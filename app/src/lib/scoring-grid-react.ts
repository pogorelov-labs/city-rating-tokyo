'use client';

import { useMemo } from 'react';
import type { FilterState, MapStation, StationRatings, WeightConfig } from './types';
import {
  countPassing, gridAnchors, gridHotspots, passMask, scoreCells,
  type BangkokGrid, type GridDistrict,
} from './bangkok-grid';
import type { PercentileAnchors } from './scoring';

interface GridInputs { grid: BangkokGrid; areas: MapStation[]; districts: GridDistrict[] }
interface GridScores { inputs: GridInputs; weights: WeightConfig; scores: Float32Array; anchors: PercentileAnchors }
interface GridPassing { inputs: GridInputs; filters: FilterState; defaults: FilterState; hideFloodRisk: boolean;
  pass: Uint8Array; passing: { cells: number; km2: number } }
export interface ScoredGrid {
  districts: GridDistrict[];
  scores: Float32Array;
  anchors: PercentileAnchors;
  pass: Uint8Array;
  passing: { cells: number; km2: number };
}

// The map and the two copies of the responsive panel receive the same immutable
// grid, area, weight and filter objects. Keep a small shared cache, like the old
// panel cache, so each does not rescore the grid. Separate score and filter
// caches preserve the map's fast path when only dealbreakers change.
let lastInputs: GridInputs | null = null;
let recentScores: GridScores[] = [];
let recentPassing: GridPassing[] = [];
let recentResults: { scores: GridScores; passing: GridPassing; value: ScoredGrid }[] = [];
const hotspotsByResult = new WeakMap<ScoredGrid, Map<number, number[]>>();
const EMPTY_HOTSPOTS: number[] = [];

function inputsFor(grid: BangkokGrid, areas: MapStation[]): GridInputs {
  if (lastInputs?.grid === grid && lastInputs.areas === areas) return lastInputs;
  const bySlug = new Map(areas.map((area) => [area.slug, area]));
  lastInputs = {
    grid, areas,
    districts: grid.header.districts.map((slug) => {
      const area = bySlug.get(slug);
      return {
        ratings: (area?.ratings ?? {}) as StationRatings,
        rent_1k: area?.rent_1k ?? null,
        flood_exposed: area?.flood_exposed === true,
      };
    }),
  };
  return lastInputs;
}

function scoresFor(inputs: GridInputs, weights: WeightConfig): GridScores {
  const cached = recentScores.find((entry) => entry.inputs === inputs && entry.weights === weights);
  if (cached) return cached;
  const scores = scoreCells(inputs.grid, weights, inputs.districts);
  const value = { inputs, weights, scores, anchors: gridAnchors(inputs.grid, scores) };
  recentScores = [value, ...recentScores].slice(0, 2);
  return value;
}

function passingFor(inputs: GridInputs, filters: FilterState, defaults: FilterState, hideFloodRisk: boolean): GridPassing {
  const cached = recentPassing.find((entry) => entry.inputs === inputs && entry.filters === filters &&
    entry.defaults === defaults && entry.hideFloodRisk === hideFloodRisk);
  if (cached) return cached;
  const pass = passMask(inputs.grid, filters, defaults, inputs.districts, hideFloodRisk);
  const value = { inputs, filters, defaults, hideFloodRisk, pass, passing: countPassing(inputs.grid, pass) };
  recentPassing = [value, ...recentPassing].slice(0, 2);
  return value;
}

function scoreGrid(grid: BangkokGrid, areas: MapStation[], weights: WeightConfig, filters: FilterState,
  defaults: FilterState, hideFloodRisk: boolean): ScoredGrid {
  const inputs = inputsFor(grid, areas);
  const scores = scoresFor(inputs, weights);
  const passing = passingFor(inputs, filters, defaults, hideFloodRisk);
  const cached = recentResults.find((entry) => entry.scores === scores && entry.passing === passing);
  if (cached) return cached.value;
  const value = { districts: inputs.districts, scores: scores.scores, anchors: scores.anchors,
    pass: passing.pass, passing: passing.passing };
  recentResults = [{ scores, passing, value }, ...recentResults].slice(0, 2);
  return value;
}

/** Grid scoring uses resident-weighted anchors, not named-area percentiles. */
export function useScoredGrid(grid: BangkokGrid | null, areas: MapStation[], weights: WeightConfig,
  filters: FilterState, defaults: FilterState, hideFloodRisk = false): ScoredGrid | null {
  return useMemo(() => grid ? scoreGrid(grid, areas, weights, filters, defaults, hideFloodRisk) : null,
    [grid, areas, weights, filters, defaults, hideFloodRisk]);
}

export function useGridHotspots(grid: BangkokGrid | null, scored: ScoredGrid | null, count: number, enabled: boolean): number[] {
  return useMemo(() => {
    if (!enabled || !grid || !scored) return EMPTY_HOTSPOTS;
    let cached = hotspotsByResult.get(scored);
    if (!cached) { cached = new Map(); hotspotsByResult.set(scored, cached); }
    const existing = cached.get(count);
    if (existing) return existing;
    const hotspots = gridHotspots(grid, scored.scores, scored.pass, count);
    cached.set(count, hotspots);
    return hotspots;
  }, [grid, scored, count, enabled]);
}
