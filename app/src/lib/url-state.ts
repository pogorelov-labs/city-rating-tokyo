import { WeightConfig, DEFAULT_WEIGHTS, FilterState, StationRatings, type AreaLevel } from './types';
import { LEGACY_WEIGHT_KEYS as SCHEMA_LEGACY_WEIGHT_KEYS } from '@/lib/schema/constants';
import { CITIES, isAreaLevel, type CityId } from './cities';

const WEIGHT_KEYS = Object.keys(DEFAULT_WEIGHTS) as (keyof WeightConfig)[];

// Old key order (pre-reorder) for backward compat with shared URLs.
// Sourced from @city-rating/schema (single source of truth).
const LEGACY_WEIGHT_KEYS = [...SCHEMA_LEGACY_WEIGHT_KEYS] as (keyof WeightConfig)[];

/** Flat view of everything a share link carries (one city's slice + shared prefs). */
export interface UrlStateView {
  /** Omitted from the URL when it is the city's default level. */
  level?: AreaLevel;
  weights: WeightConfig;
  filters: FilterState;
  selectedStation: string | null;
  compareStations: string[];
  heatmapMode: boolean;
  heatmapDimension: string;
}

/**
 * Encode state into query params. Filter params (`nr`/`mr` rent, `nc`/`mc`
 * commute) are in the city's own units — yen for Tokyo, baht for Bangkok —
 * and only emitted when they differ from that city's defaults. The path
 * (`/` vs `/bangkok`) disambiguates which city a link belongs to.
 */
export function encodeStateToParams(state: UrlStateView, city: CityId = 'tokyo'): URLSearchParams {
  const params = new URLSearchParams();
  const defaults = CITIES[city].defaultFilters;

  // Level of detail first, so `?lv=grid&…` reads naturally.
  if (state.level && state.level !== CITIES[city].defaultLevel) params.set('lv', state.level);

  // Only include weights if different from defaults
  const isDefault = WEIGHT_KEYS.every((k) => state.weights[k] === DEFAULT_WEIGHTS[k]);
  if (!isDefault) {
    params.set('w', WEIGHT_KEYS.map((k) => state.weights[k]).join(','));
  }

  // Filters: only encode when non-default
  if (state.filters.minRent > defaults.minRent) {
    params.set('nr', String(state.filters.minRent));
  }
  if (state.filters.maxRent < defaults.maxRent) {
    params.set('mr', String(state.filters.maxRent));
  }
  if (state.filters.minCommute > defaults.minCommute) {
    params.set('nc', String(state.filters.minCommute));
  }
  if (state.filters.maxCommute < defaults.maxCommute) {
    params.set('mc', String(state.filters.maxCommute));
  }
  const catEntries = Object.entries(state.filters.categoryMins) as [keyof StationRatings, number][];
  if (catEntries.length > 0) {
    params.set('cm', catEntries.map(([k, v]) => `${k}:${v}`).join(','));
  }
  if (state.filters.hasLiveCamera) {
    params.set('lc', '1');
  }

  if (state.selectedStation) params.set('s', state.selectedStation);
  if (state.compareStations.length > 0) params.set('c', state.compareStations.join(','));
  if (state.heatmapMode) params.set('hm', '1');
  if (state.heatmapDimension !== 'composite') params.set('hd', state.heatmapDimension);

  return params;
}

export function decodeParamsToState(params: URLSearchParams, city: CityId = 'tokyo'): {
  level?: AreaLevel;
  weights?: WeightConfig;
  filters?: Partial<FilterState>;
  selectedStation?: string;
  compareStations?: string[];
  heatmapMode?: boolean;
  heatmapDimension?: string;
} {
  const result: ReturnType<typeof decodeParamsToState> = {};
  const { rent, commute, features } = CITIES[city];

  const lv = params.get('lv');
  if (isAreaLevel(city, lv)) result.level = lv;

  const w = params.get('w');
  if (w) {
    const values = w.split(',').map(Number);
    if (values.length >= 9 && values.every((v) => !isNaN(v))) {
      const weights = { ...DEFAULT_WEIGHTS } as WeightConfig;
      // Detect old vs new format: old URLs have 9 or 10 values in legacy order
      // (food,nightlife,transport,...). New URLs have 10 in current order
      // (transport,rent,daily_essentials,...). Use legacy keys for 9-value URLs
      // and for 10-value URLs where position 0 matches old "food" weight pattern.
      const keys = values.length < WEIGHT_KEYS.length ? LEGACY_WEIGHT_KEYS : WEIGHT_KEYS;
      keys.forEach((k, i) => {
        if (i < values.length) weights[k] = values[i];
      });
      result.weights = weights;
    }
  }

  // Decode filters — out-of-range values (e.g. a yen amount on a baht page)
  // are silently dropped rather than clamped.
  const filterPatch: Partial<FilterState> = {};
  let hasFilter = false;
  const inRange = (v: number, r: { min: number; max: number }) => !isNaN(v) && v >= r.min && v <= r.max;

  const nr = params.get('nr');
  if (nr) {
    const v = Number(nr);
    if (inRange(v, rent)) {
      filterPatch.minRent = v;
      hasFilter = true;
    }
  }

  const mr = params.get('mr');
  if (mr) {
    const v = Number(mr);
    if (inRange(v, rent)) {
      filterPatch.maxRent = v;
      hasFilter = true;
    }
  }

  const nc = params.get('nc');
  if (nc) {
    const v = Number(nc);
    if (inRange(v, commute)) {
      filterPatch.minCommute = v;
      hasFilter = true;
    }
  }

  const mc = params.get('mc');
  if (mc) {
    const v = Number(mc);
    if (inRange(v, commute)) {
      filterPatch.maxCommute = v;
      hasFilter = true;
    }
  }

  const cm = params.get('cm');
  if (cm) {
    const categoryMins: Partial<Record<keyof StationRatings, number>> = {};
    const validKeys = new Set(WEIGHT_KEYS);
    for (const pair of cm.split(',')) {
      const [key, val] = pair.split(':');
      if (validKeys.has(key as keyof StationRatings)) {
        const v = Number(val);
        if (!isNaN(v) && v >= 1 && v <= 10) {
          categoryMins[key as keyof StationRatings] = v;
        }
      }
    }
    if (Object.keys(categoryMins).length > 0) {
      filterPatch.categoryMins = categoryMins;
      hasFilter = true;
    }
  }

  if (params.get('lc') === '1' && features.liveCameras) {
    filterPatch.hasLiveCamera = true;
    hasFilter = true;
  }

  if (hasFilter) result.filters = filterPatch;

  const s = params.get('s');
  if (s) result.selectedStation = s;

  const c = params.get('c');
  if (c) result.compareStations = c.split(',').filter(Boolean);

  if (params.get('hm') === '1') result.heatmapMode = true;

  const hd = params.get('hd');
  if (hd) result.heatmapDimension = hd;

  return result;
}

export function buildShareUrl(state: UrlStateView, city: CityId = 'tokyo'): string {
  const params = encodeStateToParams(state, city);
  const qs = params.toString();
  return window.location.origin + window.location.pathname + (qs ? '?' + qs : '');
}

/** Flatten the store into the share-link view for one city. */
export function selectUrlView(
  state: {
    weights: WeightConfig;
    heatmapMode: boolean;
    heatmapDimension: string;
    cities: Record<
      CityId,
      { level: AreaLevel; filters: FilterState; selectedStation: string | null; compareStations: string[] }
    >;
  },
  city: CityId,
): UrlStateView {
  const slice = state.cities[city];
  return {
    level: slice.level,
    weights: state.weights,
    filters: slice.filters,
    selectedStation: slice.selectedStation,
    compareStations: slice.compareStations,
    heatmapMode: state.heatmapMode,
    heatmapDimension: state.heatmapDimension,
  };
}
