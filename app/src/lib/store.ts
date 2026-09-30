'use client';

import { create } from 'zustand';
import { WeightConfig, DEFAULT_WEIGHTS, FilterState, StationRatings, type AreaLevel } from './types';
import { CITIES, CITY_IDS, type CityId } from './cities';
import { useCityId } from './city-context';

/**
 * State that only makes sense inside one city. Filters carry currency
 * (¥ vs ฿) and city-specific commute hubs; selection / compare lists hold
 * that city's slugs. Keeping one slice per city means switching cities never
 * applies Tokyo yen limits to Bangkok baht data (not even for one render or
 * during SSR), and switching back restores exactly what the user left.
 */
export interface CityScopedState {
  filters: FilterState;
  /** Level of detail painted on the map (Bangkok: district / station / grid). */
  level: AreaLevel;
  /** One selection per city. Bangkok keys are typed (see `lib/area-key.ts`),
   *  so a district, a station area or a grid cell can be selected — and stays
   *  highlighted — whatever level is painted. */
  selectedStation: string | null;
  hoveredStation: string | null;
  compareStations: string[];
  hideFloodRisk: boolean;
  hideHighSeismic: boolean;
}

export type CityPatch =
  | Partial<CityScopedState>
  | ((prev: CityScopedState) => Partial<CityScopedState>);

/** Shape accepted by `hydrateFromUrl` — what `decodeParamsToState` returns. */
export interface UrlHydration {
  level?: AreaLevel;
  weights?: WeightConfig;
  filters?: Partial<FilterState>;
  selectedStation?: string;
  compareStations?: string[];
  heatmapMode?: boolean;
  heatmapDimension?: string;
}

interface AppState {
  // ── Shared across cities: personal preferences ──
  weights: WeightConfig;
  setWeight: (key: keyof WeightConfig, value: number) => void;
  setAllWeights: (weights: WeightConfig) => void;
  resetWeights: () => void;
  heatmapMode: boolean;
  setHeatmapMode: (v: boolean) => void;
  heatmapDimension: string;
  setHeatmapDimension: (v: string) => void;
  /** Bangkok rail overlay (lines + stations) on/off. */
  showRailOverlay: boolean;
  setShowRailOverlay: (v: boolean) => void;
  isFlying: boolean;
  setIsFlying: (v: boolean) => void;

  // ── Per city ──
  cities: Record<CityId, CityScopedState>;
  updateCity: (city: CityId, patch: CityPatch) => void;
  hydrateFromUrl: (city: CityId, partial: UrlHydration) => void;
}

export function initialCityState(city: CityId): CityScopedState {
  return {
    filters: { ...CITIES[city].defaultFilters, categoryMins: {} },
    level: CITIES[city].defaultLevel,
    selectedStation: null,
    hoveredStation: null,
    compareStations: [],
    hideFloodRisk: false,
    hideHighSeismic: false,
  };
}

export const useAppStore = create<AppState>((set) => ({
  weights: { ...DEFAULT_WEIGHTS },
  setWeight: (key, value) =>
    set((state) => ({ weights: { ...state.weights, [key]: value } })),
  setAllWeights: (weights) => set({ weights: { ...weights } }),
  resetWeights: () => set({ weights: { ...DEFAULT_WEIGHTS } }),
  heatmapMode: false,
  setHeatmapMode: (heatmapMode) => set({ heatmapMode }),
  heatmapDimension: 'composite',
  setHeatmapDimension: (heatmapDimension) => set({ heatmapDimension }),
  showRailOverlay: true,
  setShowRailOverlay: (showRailOverlay) => set({ showRailOverlay }),
  isFlying: false,
  setIsFlying: (isFlying) => set({ isFlying }),

  cities: Object.fromEntries(CITY_IDS.map((id) => [id, initialCityState(id)])) as Record<
    CityId,
    CityScopedState
  >,
  updateCity: (city, patch) =>
    set((state) => {
      const prev = state.cities[city];
      const next = typeof patch === 'function' ? patch(prev) : patch;
      if (Object.keys(next).length === 0) return state;
      return { cities: { ...state.cities, [city]: { ...prev, ...next } } };
    }),
  hydrateFromUrl: (city, partial) =>
    set((state) => {
      const updates: Partial<AppState> = {};
      if (partial.weights) updates.weights = partial.weights;
      if (partial.heatmapMode !== undefined) updates.heatmapMode = partial.heatmapMode;
      if (partial.heatmapDimension) updates.heatmapDimension = partial.heatmapDimension;

      const prev = state.cities[city];
      const next: CityScopedState = { ...prev };
      if (partial.level) next.level = partial.level;
      if (partial.selectedStation) next.selectedStation = partial.selectedStation;
      if (partial.compareStations) next.compareStations = partial.compareStations;
      if (partial.filters) {
        next.filters = {
          ...prev.filters,
          ...partial.filters,
          categoryMins: { ...prev.filters.categoryMins, ...partial.filters.categoryMins },
        };
      }
      updates.cities = { ...state.cities, [city]: next };
      return updates;
    }),
}));

/** Actions bound to one city. Created once per city, so they are referentially
 *  stable and safe in effect / callback dependency lists. */
export interface CityActions {
  setLevel: (level: AreaLevel) => void;
  setMinRent: (v: number) => void;
  setMaxRent: (v: number) => void;
  setMinCommute: (v: number) => void;
  setMaxCommute: (v: number) => void;
  setCategoryMin: (key: keyof StationRatings, value: number | null) => void;
  setHasLiveCamera: (v: boolean) => void;
  setFilters: (filters: FilterState) => void;
  resetFilters: () => void;
  setSelectedStation: (slug: string | null) => void;
  setHoveredStation: (slug: string | null) => void;
  setHideFloodRisk: (v: boolean) => void;
  setHideHighSeismic: (v: boolean) => void;
  addCompareStation: (slug: string) => void;
  removeCompareStation: (slug: string) => void;
  clearCompareStations: () => void;
}

const actionsCache = new Map<CityId, CityActions>();
export const MAX_COMPARE = 3;

export function getCityActions(city: CityId): CityActions {
  const cached = actionsCache.get(city);
  if (cached) return cached;
  const up = (patch: CityPatch) => useAppStore.getState().updateCity(city, patch);
  const setFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) =>
    up((s) => ({ filters: { ...s.filters, [key]: value } }));
  const actions: CityActions = {
    // A hover belongs to the layer being painted; the selection survives.
    setLevel: (level) => up((s) => (s.level === level ? {} : { level, hoveredStation: null })),
    setMinRent: (v) => setFilter('minRent', v),
    setMaxRent: (v) => setFilter('maxRent', v),
    setMinCommute: (v) => setFilter('minCommute', v),
    setMaxCommute: (v) => setFilter('maxCommute', v),
    setCategoryMin: (key, value) =>
      up((s) => {
        const categoryMins = { ...s.filters.categoryMins };
        if (value === null) delete categoryMins[key];
        else categoryMins[key] = value;
        return { filters: { ...s.filters, categoryMins } };
      }),
    setHasLiveCamera: (v) => setFilter('hasLiveCamera', v),
    setFilters: (filters) => up({ filters: { ...filters, categoryMins: { ...filters.categoryMins } } }),
    resetFilters: () => up({ filters: { ...CITIES[city].defaultFilters, categoryMins: {} } }),
    setSelectedStation: (selectedStation) => up({ selectedStation }),
    setHoveredStation: (hoveredStation) =>
      up((s) => (s.hoveredStation === hoveredStation ? {} : { hoveredStation })),
    setHideFloodRisk: (hideFloodRisk) => up({ hideFloodRisk }),
    setHideHighSeismic: (hideHighSeismic) => up({ hideHighSeismic }),
    addCompareStation: (slug) =>
      up((s) =>
        s.compareStations.length >= MAX_COMPARE || s.compareStations.includes(slug)
          ? {}
          : { compareStations: [...s.compareStations, slug] },
      ),
    removeCompareStation: (slug) =>
      up((s) => ({ compareStations: s.compareStations.filter((x) => x !== slug) })),
    clearCompareStations: () => up({ compareStations: [] }),
  };
  actionsCache.set(city, actions);
  return actions;
}

/** Select from the current page's city slice (city comes from `CityProvider`). */
export function useCityState<T>(selector: (s: CityScopedState) => T): T {
  const city = useCityId();
  return useAppStore((s) => selector(s.cities[city]));
}

/** Stable, city-bound actions for the current page's city. */
export function useCityActions(): CityActions {
  return getCityActions(useCityId());
}
