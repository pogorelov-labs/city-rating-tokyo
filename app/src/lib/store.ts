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
  heatmapMode: boolean;
  setHeatmapMode: (v: boolean) => void;
  heatmapDimension: string;
  setHeatmapDimension: (v: string) => void;
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
  heatmapMode: false,
  setHeatmapMode: (heatmapMode) => set({ heatmapMode }),
  heatmapDimension: 'composite',
  setHeatmapDimension: (heatmapDimension) => set({ heatmapDimension }),
}));
