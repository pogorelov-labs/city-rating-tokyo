'use client';

import { createContext, useContext, type ReactNode } from 'react';
import { CITIES, type CityConfig, type CityId } from './cities';

/**
 * Which city the current page renders. Set once per page by `CityProvider`
 * (server pages pass a plain string, so it serialises across the RSC
 * boundary); client components read it with `useCityId()` / `useCity()`.
 *
 * Defaults to Tokyo so any component rendered outside a provider — e.g. on a
 * Tokyo station page — keeps its original behaviour.
 */
const CityContext = createContext<CityId>('tokyo');

export function CityProvider({ city, children }: { city: CityId; children: ReactNode }) {
  return <CityContext.Provider value={city}>{children}</CityContext.Provider>;
}

export function useCityId(): CityId {
  return useContext(CityContext);
}

export function useCity(): CityConfig {
  return CITIES[useContext(CityContext)];
}
