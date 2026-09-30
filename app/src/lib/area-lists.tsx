'use client';

import { createContext, useContext, useMemo, type ReactNode } from 'react';
import type { MapStation } from './types';
import { useCityState } from './store';

/**
 * Rated areas per level of detail, for cities with more than one (Bangkok).
 *
 * Every map-page component already receives the city's primary list as its
 * `stations` prop (Tokyo stations, Bangkok districts). Bangkok's station
 * areas ride along in this context instead of a second prop on every
 * component; Tokyo renders no provider and nothing changes there.
 */
export interface AreaLists {
  district: MapStation[];
  station: MapStation[];
}

const AreaListsContext = createContext<AreaLists | null>(null);

export function AreaListsProvider({ lists, children }: { lists: AreaLists; children: ReactNode }) {
  return <AreaListsContext.Provider value={lists}>{children}</AreaListsContext.Provider>;
}

export function useAreaLists(): AreaLists | null {
  return useContext(AreaListsContext);
}

/** The areas ranked at the current level: station areas on Bangkok's station
 *  level, the `stations` prop otherwise (the grid level ranks cells itself). */
export function useLevelAreas(stations: MapStation[]): MapStation[] {
  const lists = useAreaLists();
  const level = useCityState((s) => s.level);
  return level === 'station' && lists ? lists.station : stations;
}

/** Every named area a Bangkok selection key can point at (districts + station
 *  areas); for Tokyo simply the stations. */
export function useAllAreas(stations: MapStation[]): MapStation[] {
  const lists = useAreaLists();
  return useMemo(() => (lists ? [...lists.district, ...lists.station] : stations), [lists, stations]);
}
