'use client';

import { createContext, useContext, useDeferredValue, useMemo, type ReactNode } from 'react';
import { useCity } from './city-context';
import { hasActiveFilters, type CityId } from './cities';
import { useAppStore, useCityState } from './store';
import type { FilterState, MapStation, WeightConfig } from './types';
import {
  applyDealbreakers,
  calculateWeightedScore,
  computeScoreAnchors,
  type FilteredMapStation,
  type PercentileAnchors,
} from './scoring';

type ScoredArea = MapStation & { score: number | null };

export interface ScoredAreas {
  /** The provider's original list, also shared with the grid adapter. */
  areas: MapStation[];
  /** All areas, including those without ratings, in their original order. */
  scored: ScoredArea[];
  /** Anchors always use the full unfiltered population. */
  anchors: PercentileAnchors;
  passing: FilteredMapStation[];
  /** Rated, passing areas in descending score order, limited to the panel's 15. */
  ranked: FilteredMapStation[];
  ratedCount: number;
  deferredWeights: WeightConfig;
}

interface Inputs {
  cityId: CityId;
  weights: WeightConfig;
  filters: FilterState;
  defaults: FilterState;
  hideFloodRisk: boolean;
  hideHighSeismic: boolean;
  hideAdultZones: boolean;
}

function useInputs(): Inputs {
  const city = useCity();
  const weights = useDeferredValue(useAppStore((s) => s.weights));
  const filters = useCityState((s) => s.filters);
  const hideFloodRisk = useCityState((s) => s.hideFloodRisk);
  const hideHighSeismic = useCityState((s) => s.hideHighSeismic);
  const hideAdultZones = useCityState((s) => s.hideAdultZones);
  return { cityId: city.id, weights, filters, defaults: city.defaultFilters, hideFloodRisk, hideHighSeismic, hideAdultZones };
}

/** One implementation for named-area scoring, filtering and ranking. */
function useAreaCalculation(areas: MapStation[], input: Inputs, enabled: boolean): ScoredAreas | null {
  const { cityId, weights, filters, defaults, hideFloodRisk, hideHighSeismic, hideAdultZones } = input;
  const scored = useMemo(() => enabled ? areas.map((area) => ({
    ...area,
    score: area.ratings ? calculateWeightedScore(area.ratings, weights) : null,
  })) : null, [areas, weights, enabled]);
  const anchors = useMemo(() => scored ? computeScoreAnchors(
    scored.flatMap((area) => area.score === null ? [] : [area.score]),
  ) : null, [scored]);
  const passing = useMemo(() => {
    if (!scored) return null;
    if (!hasActiveFilters(cityId, filters, { hideFloodRisk, hideHighSeismic, hideAdultZones })) {
      return scored.map((area) => ({ ...area, rentUnknown: false }));
    }
    return applyDealbreakers(scored, filters, hideFloodRisk, hideHighSeismic, hideAdultZones, defaults);
  }, [scored, cityId, filters, hideFloodRisk, hideHighSeismic, hideAdultZones, defaults]);
  const ranked = useMemo(() => passing ? passing.filter((area) => area.ratings !== null)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 15) : null, [passing]);
  const ratedCount = useMemo(() => enabled ? areas.filter((area) => area.ratings).length : 0, [areas, enabled]);
  return useMemo(() => scored && anchors && passing && ranked ? {
    areas, scored, anchors, passing, ranked, ratedCount, deferredWeights: weights,
  } : null, [areas, scored, anchors, passing, ranked, ratedCount, weights]);
}

interface SharedScoring {
  primaryAreas: MapStation[];
  primary: ScoredAreas;
  stationAreas?: MapStation[];
  station: ScoredAreas | null;
}
const ScoredAreasContext = createContext<SharedScoring | null>(null);
const EMPTY_AREAS: MapStation[] = [];

/** Reuse the provider's original list without calculating named-area scores. */
export function useSharedAreaList(areas: MapStation[], level: 'primary' | 'station'): MapStation[] {
  const shared = useContext(ScoredAreasContext);
  return (level === 'primary' ? shared?.primaryAreas : shared?.stationAreas) ?? areas;
}

/** The map and both responsive panels share each city's named-area results. */
export function ScoredAreasProvider({ primaryAreas, stationAreas, children }: {
  primaryAreas: MapStation[];
  stationAreas?: MapStation[];
  children: ReactNode;
}) {
  const input = useInputs();
  const primary = useAreaCalculation(primaryAreas, input, true)!;
  const station = useAreaCalculation(stationAreas ?? EMPTY_AREAS, input, stationAreas !== undefined);
  const value = useMemo(() => ({ primaryAreas, primary, stationAreas, station }),
    [primaryAreas, primary, stationAreas, station]);
  return <ScoredAreasContext.Provider value={value}>{children}</ScoredAreasContext.Provider>;
}

/** Score a named-area list; homepage callers identify the shared city level. */
export function useScoredAreas(areas: MapStation[], level?: 'primary' | 'station'): ScoredAreas {
  const shared = useContext(ScoredAreasContext);
  const result = level === 'primary' ? shared?.primary ?? null
    : level === 'station' ? shared?.station ?? null
      : areas === shared?.primaryAreas ? shared.primary
        : areas === shared?.stationAreas ? shared.station : null;
  // Keep the hook usable for standalone components and tests without a provider.
  // The fallback is disabled when the homepage has already computed this list.
  const input = useInputs();
  const fallback = useAreaCalculation(areas, input, result === null);
  return result ?? fallback!;
}
