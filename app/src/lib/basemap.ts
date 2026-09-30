/**
 * Base map tiles.
 *
 * CARTO basemaps require an API key since late September 2026: a keyless
 * request gets a tile stamped "API key required" instead of the map. The key is
 * public by design (it rides on every tile URL), so it is inlined at build time
 * from NEXT_PUBLIC_CARTO_BASEMAPS_KEY — set in Coolify as a build variable, the
 * same way as NEXT_PUBLIC_UMAMI_*. Free for non-commercial use up to 5M tile
 * requests a month: https://carto.com/basemaps/apikey
 *
 * Without a key the map uses OpenStreetMap's own tiles instead of showing the
 * watermark. OSM's tile policy does not allow prefetching tiles that are not on
 * screen, so hover prefetch is off in that mode.
 *
 * Both providers require their attribution to stay visible on the map.
 */

export interface Basemap {
  provider: 'carto' | 'osm';
  /** Leaflet URL template with {z}/{x}/{y}. */
  url: string;
  attribution: string;
  /** Whether warming the cache with off-screen tiles is allowed. */
  prefetch: boolean;
}

const OSM_COPYRIGHT = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export function basemapFor(cartoKey: string | undefined): Basemap {
  const key = cartoKey?.trim();
  if (key) {
    return {
      provider: 'carto',
      // CARTO's documented template has no @2x retina variant; tiles are served
      // at standard resolution.
      url: `https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${encodeURIComponent(key)}`,
      attribution: `${OSM_COPYRIGHT}, &copy; <a href="https://carto.com/attributions">CARTO</a>`,
      prefetch: true,
    };
  }
  return {
    provider: 'osm',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: OSM_COPYRIGHT,
    prefetch: false,
  };
}

// Must be the literal `process.env.NEXT_PUBLIC_…` so Next inlines it at build time.
export const BASEMAP = basemapFor(process.env.NEXT_PUBLIC_CARTO_BASEMAPS_KEY);

export function tileUrl(basemap: Basemap, z: number, x: number, y: number): string {
  return basemap.url.replace('{z}', String(z)).replace('{x}', String(x)).replace('{y}', String(y));
}
