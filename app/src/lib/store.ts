'use client';

import { create } from 'zustand';
import { WeightConfig, DEFAULT_WEIGHTS } from './types';

interface AppState {
  weights: WeightConfig;
  setWeight: (key: keyof WeightConfig, value: number) => void;
  setAllWeights: (weights: WeightConfig) => void;
  resetWeights: () => void;
  maxRent: number;
  setMaxRent: (v: number) => void;
  maxCommute: number;
  setMaxCommute: (v: number) => void;
  minScore: number;
  setMinScore: (v: number) => void;
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
  maxRent: 300000,
  setMaxRent: (maxRent) => set({ maxRent }),
  maxCommute: 60,
  setMaxCommute: (maxCommute) => set({ maxCommute }),
  minScore: 0,
  setMinScore: (minScore) => set({ minScore }),
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
  hydrateFromUrl: (partial) => set((state) => ({
    ...(partial.weights ? { weights: partial.weights } : {}),
    ...(partial.selectedStation ? { selectedStation: partial.selectedStation } : {}),
    ...(partial.compareStations ? { compareStations: partial.compareStations } : {}),
    ...(partial.heatmapMode !== undefined ? { heatmapMode: partial.heatmapMode } : {}),
    ...(partial.heatmapDimension ? { heatmapDimension: partial.heatmapDimension } : {}),
  })),
}));
