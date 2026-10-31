import type { BangkokRenderer } from './bangkok-prototype';

export type MapUnavailableReason = 'webgl' | 'load' | 'context';

/** Resolve on the server during static generation, so rollback is a build setting. */
export function resolveBangkokRenderer(value: string | undefined): BangkokRenderer {
  return value === 'leaflet' ? 'leaflet' : 'maplibre';
}
