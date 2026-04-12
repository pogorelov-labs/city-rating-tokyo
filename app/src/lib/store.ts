'use client';

import { create } from 'zustand';
import { WeightConfig, DEFAULT_WEIGHTS, FilterState, DEFAULT_FILTERS, StationRatings } from './types';

interface AppState {
  weights: WeightConfig;
  setWeight: (key: keyof WeightConfig, value: number) => void;
  setAllWeights: (weights: WeightConfig) => void;
  resetWeights: () => void;
  filters: FilterState;
  setMaxRent: (v: number) => void;
  setMaxCommute: (v: number) => void;
  setCategoryMin: (key: keyof StationRatings, value: number | null) => void;
  setFilters: (filters: FilterState) => void;
  resetFilters: () => void;
  selectedStation: string | null;
  setSelectedStation: (slug: string | null) => void;
  hoveredStation: string | null;
  setHoveredStation: (slug: string | null) => void;
  heatmapMode: boolean;
  setHeatmapMode: (v: boolean) => void;
  heatmapDimension: string;
  setHeatmapDimension: (v: string) => void;
  hideFloodRisk: boolean;
  setHideFloodRisk: (v: boolean) => void;
  hideHighSeismic: boolean;
  setHideHighSeismic: (v: boolean) => void;
  compareStations: string[];
  addCompareStation: (slug: string) => void;
  removeCompareStation: (slug: string) => void;
  clearCompareStations: () => void;
  hydrateFromUrl: (partial: {
    weights?: WeightConfig;
    filters?: Partial<FilterState>;
    selectedStation?: string;
    compareStations?: string[];
    heatmapMode?: boolean;
    heatmapDimension?: string;
  }) => void;
}

export const useAppStore = create<AppState>((set) => ({
  weights: { ...DEFAULT_WEIGHTS },
  setWeight: (key, value) =>
    set((state) => ({ weights: { ...state.weights, [key]: value } })),
  setAllWeights: (weights) => set({ weights: { ...weights } }),
  resetWeights: () => set({ weights: { ...DEFAULT_WEIGHTS } }),
  filters: { ...DEFAULT_FILTERS, categoryMins: {} },
  setMaxRent: (maxRent) =>
    set((state) => ({ filters: { ...state.filters, maxRent } })),
  setMaxCommute: (maxCommute) =>
    set((state) => ({ filters: { ...state.filters, maxCommute } })),
  setCategoryMin: (key, value) =>
    set((state) => {
      const categoryMins = { ...state.filters.categoryMins };
      if (value === null) {
        delete categoryMins[key];
      } else {
        categoryMins[key] = value;
      }
      return { filters: { ...state.filters, categoryMins } };
    }),
  setFilters: (filters) => set({ filters: { ...filters, categoryMins: { ...filters.categoryMins } } }),
  resetFilters: () => set({ filters: { ...DEFAULT_FILTERS, categoryMins: {} } }),
  selectedStation: null,
  setSelectedStation: (selectedStation) => set({ selectedStation }),
  hoveredStation: null,
  setHoveredStation: (hoveredStation) => set({ hoveredStation }),
  heatmapMode: false,
  setHeatmapMode: (heatmapMode) => set({ heatmapMode }),
  heatmapDimension: 'composite',
  setHeatmapDimension: (heatmapDimension) => set({ heatmapDimension }),
  hideFloodRisk: false,
  setHideFloodRisk: (hideFloodRisk) => set({ hideFloodRisk }),
  hideHighSeismic: false,
  setHideHighSeismic: (hideHighSeismic) => set({ hideHighSeismic }),
  compareStations: [],
  addCompareStation: (slug) =>
    set((state) => {
      if (state.compareStations.length >= 3 || state.compareStations.includes(slug)) return state;
      return { compareStations: [...state.compareStations, slug] };
    }),
  removeCompareStation: (slug) =>
    set((state) => ({ compareStations: state.compareStations.filter((s) => s !== slug) })),
  clearCompareStations: () => set({ compareStations: [] }),
  hydrateFromUrl: (partial) => set((state) => {
    const updates: Partial<AppState> = {};
    if (partial.weights) updates.weights = partial.weights;
    if (partial.selectedStation) updates.selectedStation = partial.selectedStation;
    if (partial.compareStations) updates.compareStations = partial.compareStations;
    if (partial.heatmapMode !== undefined) updates.heatmapMode = partial.heatmapMode;
    if (partial.heatmapDimension) updates.heatmapDimension = partial.heatmapDimension;
    if (partial.filters) {
      updates.filters = {
        ...state.filters,
        ...partial.filters,
        categoryMins: { ...state.filters.categoryMins, ...partial.filters.categoryMins },
      };
    }
    return updates;
  }),
}));
