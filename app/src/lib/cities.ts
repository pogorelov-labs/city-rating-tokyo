import type { FilterState, StationRatings } from './types';
import { DEFAULT_FILTERS, PRESET_PROFILES } from './types';
import { CITY_MEDIANS, DEFAULT_COMPOSITE_ANCHORS, type PercentileAnchors } from './scoring';
import bangkokMeta from '@/data/bangkok/meta.json';

/**
 * City registry — the single place where Tokyo and Bangkok differ.
 *
 * Everything city-specific that UI code needs (map framing, currency, filter
 * ranges, commute hubs, preset dealbreakers, medians for the deviation
 * palette, which Tokyo-only features exist) lives here, so components ask
 * `useCity()` instead of hard-coding Tokyo assumptions.
 *
 * The rating *categories* and weight vector are deliberately shared: weights
 * express what the user cares about, which does not change when they switch
 * city, so the store keeps one weight vector across both.
 *
 * Scores are relative within each city (percentile-normalised over that
 * city's own areas), so a Tokyo 8 and a Bangkok 8 are not comparable.
 */

export const CITY_IDS = ['tokyo', 'bangkok'] as const;
export type CityId = (typeof CITY_IDS)[number];

/** What one rated area is: a train-station catchment or an administrative district. */
export type CityUnit = 'station' | 'district';

export interface RangeConfig {
  min: number;
  max: number;
  step: number;
}

export type LatLngTuple = [number, number];

export interface CityConfig {
  id: CityId;
  unit: CityUnit;
  /** Locale-agnostic path of the city map (use with the i18n `Link`). */
  homePath: string;
  /** Locale-agnostic prefix of an area detail page; append `/${slug}`. */
  detailBasePath: string;
  map: {
    /** Initial framing: Tokyo opens on a fixed centre/zoom, Bangkok fits the province. */
    center: LatLngTuple;
    zoom: number;
    fitBounds?: [LatLngTuple, LatLngTuple];
    /** Tighter box for narrow (phone) screens, where the whole province would be tiny. */
    fitBoundsNarrow?: [LatLngTuple, LatLngTuple];
    minZoom: number;
    maxBounds: [LatLngTuple, LatLngTuple];
  };
  currency: { code: 'JPY' | 'THB'; symbol: string };
  /** Dealbreaker rent slider, monthly, local currency. `max` means "no limit". */
  rent: RangeConfig;
  /** Dealbreaker commute slider in minutes. `max` means "no limit". */
  commute: RangeConfig;
  /** Commute hubs, keys into the `hubs.*` messages. */
  hubs: readonly string[];
  defaultFilters: FilterState;
  /** Dealbreakers applied by each quick profile (weights are shared). */
  presetFilters: Record<string, Partial<FilterState>>;
  features: {
    /** Flood (elevation) + seismic dealbreakers — Tokyo data only. */
    environmentFilters: boolean;
    liveCameras: boolean;
    /** Rail network overlay (lines + stations) on top of district polygons. */
    railOverlay: boolean;
  };
  /** Per-category city median, painted as the "norm" tick on rating bars. */
  medians: Record<keyof StationRatings, number>;
  /** Composite anchors for statically rendered pages (default weights). */
  defaultAnchors: PercentileAnchors;
}

const tokyoPresetFilters = Object.fromEntries(
  PRESET_PROFILES.map((p) => [p.id, p.filters ?? {}]),
) as Record<string, Partial<FilterState>>;

const BANGKOK_DEFAULT_FILTERS: FilterState = {
  minRent: 6_000,
  maxRent: 40_000,
  minCommute: 10,
  maxCommute: 90,
  categoryMins: {},
  hasLiveCamera: false,
};

export const CITIES: Record<CityId, CityConfig> = {
  tokyo: {
    id: 'tokyo',
    unit: 'station',
    homePath: '/',
    detailBasePath: '/station',
    map: {
      center: [35.6762, 139.7503],
      zoom: 12,
      minZoom: 8,
      maxBounds: [[34.8, 138.6], [36.6, 140.9]],
    },
    currency: { code: 'JPY', symbol: '¥' },
    rent: { min: DEFAULT_FILTERS.minRent, max: DEFAULT_FILTERS.maxRent, step: 10_000 },
    commute: { min: DEFAULT_FILTERS.minCommute, max: DEFAULT_FILTERS.maxCommute, step: 5 },
    hubs: ['shibuya', 'shinjuku', 'tokyo', 'ikebukuro', 'shinagawa'],
    defaultFilters: DEFAULT_FILTERS,
    presetFilters: tokyoPresetFilters,
    features: { environmentFilters: true, liveCameras: true, railOverlay: false },
    medians: CITY_MEDIANS,
    defaultAnchors: DEFAULT_COMPOSITE_ANCHORS,
  },
  bangkok: {
    id: 'bangkok',
    unit: 'district',
    homePath: '/bangkok',
    detailBasePath: '/bangkok/district',
    map: {
      center: [13.745, 100.56],
      zoom: 11,
      // Province bbox (khet boundaries): the whole city is visible on arrival.
      fitBounds: [[13.49, 100.33], [13.96, 100.94]],
      // Inner city: Chatuchak ↔ Bang Na, Thon Buri ↔ Bang Kapi.
      fitBoundsNarrow: [[13.66, 100.46], [13.84, 100.66]],
      minZoom: 9,
      maxBounds: [[13.2, 100.0], [14.25, 101.25]],
    },
    currency: { code: 'THB', symbol: '฿' },
    rent: { min: BANGKOK_DEFAULT_FILTERS.minRent, max: BANGKOK_DEFAULT_FILTERS.maxRent, step: 1_000 },
    commute: { min: BANGKOK_DEFAULT_FILTERS.minCommute, max: BANGKOK_DEFAULT_FILTERS.maxCommute, step: 5 },
    hubs: ['siam', 'asok', 'silom', 'rama9', 'mochit'],
    defaultFilters: BANGKOK_DEFAULT_FILTERS,
    presetFilters: {
      'young-pro': { maxRent: 25_000, maxCommute: 30 },
      family: { maxCommute: 45, categoryMins: { safety: 7 } },
      'foodie-budget': { maxRent: 15_000 },
      'digital-nomad': { maxRent: 18_000 },
    },
    features: { environmentFilters: false, liveCameras: false, railOverlay: true },
    medians: bangkokMeta.medians as Record<keyof StationRatings, number>,
    defaultAnchors: bangkokMeta.default_anchors as PercentileAnchors,
  },
};

export function isCityId(value: unknown): value is CityId {
  return typeof value === 'string' && (CITY_IDS as readonly string[]).includes(value);
}

/** Locale-agnostic detail path for an area, e.g. `/station/shibuya` or `/bangkok/district/watthana`. */
export function areaPath(city: CityId, slug: string): string {
  return `${CITIES[city].detailBasePath}/${slug}`;
}

/**
 * Compact monthly-rent label: `¥120k`, `฿25k`, `฿8.5k`.
 * Baht values under 10k keep one decimal because the whole Bangkok range is
 * ~฿7k–฿40k and "฿8k" vs "฿9k" is a meaningful difference there.
 */
export function formatRentShort(city: CityId, value: number): string {
  const { symbol } = CITIES[city].currency;
  const k = value / 1000;
  if (city === 'bangkok' && k < 10) {
    const rounded = Math.round(k * 2) / 2; // nearest ฿0.5k
    return `${symbol}${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}k`;
  }
  return `${symbol}${Math.round(k)}k`;
}

/** True when any dealbreaker differs from the city's wide-open defaults. */
export function hasActiveFilters(
  city: CityId,
  filters: FilterState,
  env: { hideFloodRisk: boolean; hideHighSeismic: boolean },
): boolean {
  const d = CITIES[city].defaultFilters;
  return (
    filters.minRent > d.minRent ||
    filters.maxRent < d.maxRent ||
    filters.minCommute > d.minCommute ||
    filters.maxCommute < d.maxCommute ||
    Object.keys(filters.categoryMins).length > 0 ||
    filters.hasLiveCamera ||
    env.hideFloodRisk ||
    env.hideHighSeismic
  );
}
