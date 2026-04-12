import { WeightConfig, DEFAULT_WEIGHTS, FilterState, DEFAULT_FILTERS, StationRatings } from './types';

const WEIGHT_KEYS = Object.keys(DEFAULT_WEIGHTS) as (keyof WeightConfig)[];

export function encodeStateToParams(state: {
  weights: WeightConfig;
  filters: FilterState;
  selectedStation: string | null;
  compareStations: string[];
  heatmapMode: boolean;
  heatmapDimension: string;
}): URLSearchParams {
  const params = new URLSearchParams();

  // Only include weights if different from defaults
  const isDefault = WEIGHT_KEYS.every((k) => state.weights[k] === DEFAULT_WEIGHTS[k]);
  if (!isDefault) {
    params.set('w', WEIGHT_KEYS.map((k) => state.weights[k]).join(','));
  }

  // Filters: only encode when non-default
  if (state.filters.minRent > DEFAULT_FILTERS.minRent) {
    params.set('nr', String(state.filters.minRent));
  }
  if (state.filters.maxRent < DEFAULT_FILTERS.maxRent) {
    params.set('mr', String(state.filters.maxRent));
  }
  if (state.filters.minCommute > DEFAULT_FILTERS.minCommute) {
    params.set('nc', String(state.filters.minCommute));
  }
  if (state.filters.maxCommute < DEFAULT_FILTERS.maxCommute) {
    params.set('mc', String(state.filters.maxCommute));
  }
  const catEntries = Object.entries(state.filters.categoryMins) as [keyof StationRatings, number][];
  if (catEntries.length > 0) {
    params.set('cm', catEntries.map(([k, v]) => `${k}:${v}`).join(','));
  }

  if (state.selectedStation) params.set('s', state.selectedStation);
  if (state.compareStations.length > 0) params.set('c', state.compareStations.join(','));
  if (state.heatmapMode) params.set('hm', '1');
  if (state.heatmapDimension !== 'composite') params.set('hd', state.heatmapDimension);

  return params;
}

export function decodeParamsToState(params: URLSearchParams): {
  weights?: WeightConfig;
  filters?: Partial<FilterState>;
  selectedStation?: string;
  compareStations?: string[];
  heatmapMode?: boolean;
  heatmapDimension?: string;
} {
  const result: ReturnType<typeof decodeParamsToState> = {};

  const w = params.get('w');
  if (w) {
    const values = w.split(',').map(Number);
    if (values.length === WEIGHT_KEYS.length && values.every((v) => !isNaN(v))) {
      const weights = {} as WeightConfig;
      WEIGHT_KEYS.forEach((k, i) => { weights[k] = values[i]; });
      result.weights = weights;
    }
  }

  // Decode filters
  const filterPatch: Partial<FilterState> = {};
  let hasFilter = false;

  const nr = params.get('nr');
  if (nr) {
    const v = Number(nr);
    if (!isNaN(v) && v >= 80000 && v <= 300000) {
      filterPatch.minRent = v;
      hasFilter = true;
    }
  }

  const mr = params.get('mr');
  if (mr) {
    const v = Number(mr);
    if (!isNaN(v) && v >= 80000 && v <= 300000) {
      filterPatch.maxRent = v;
      hasFilter = true;
    }
  }

  const nc = params.get('nc');
  if (nc) {
    const v = Number(nc);
    if (!isNaN(v) && v >= 10 && v <= 60) {
      filterPatch.minCommute = v;
      hasFilter = true;
    }
  }

  const mc = params.get('mc');
  if (mc) {
    const v = Number(mc);
    if (!isNaN(v) && v >= 10 && v <= 60) {
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

export function buildShareUrl(state: Parameters<typeof encodeStateToParams>[0]): string {
  const params = encodeStateToParams(state);
  const qs = params.toString();
  return window.location.origin + window.location.pathname + (qs ? '?' + qs : '');
}
