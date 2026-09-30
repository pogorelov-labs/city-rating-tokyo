/**
 * Base map selection (lib/basemap.ts).
 *
 * CARTO started watermarking keyless tile requests ("API key required") in
 * September 2026, which blanked every map on the site. These pin the rules:
 * with a key → CARTO with the key on every URL; without → OpenStreetMap, never
 * a keyless CARTO URL.
 */
import { describe, expect, it } from 'vitest';

import { basemapFor, tileUrl } from '../basemap';

describe('basemapFor', () => {
  it('uses CARTO light_all with the key on the tile URL when a key is set', () => {
    const b = basemapFor('abc123');
    expect(b.provider).toBe('carto');
    expect(b.url).toBe('https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=abc123');
    expect(b.prefetch).toBe(true);
  });

  it('never produces a keyless CARTO URL', () => {
    for (const key of [undefined, '', '   ']) {
      const b = basemapFor(key);
      expect(b.provider).toBe('osm');
      expect(b.url).not.toContain('cartocdn');
    }
  });

  it('does not prefetch off-screen tiles from OpenStreetMap (tile usage policy)', () => {
    expect(basemapFor(undefined).prefetch).toBe(false);
  });

  it('carries the attribution each provider requires', () => {
    expect(basemapFor('k').attribution).toMatch(/OpenStreetMap.*CARTO/);
    expect(basemapFor(undefined).attribution).toMatch(/OpenStreetMap/);
  });

  it('encodes the key', () => {
    expect(basemapFor('a b&c').url).toContain('?key=a%20b%26c');
  });
});

describe('tileUrl', () => {
  it('fills z/x/y and keeps the key', () => {
    expect(tileUrl(basemapFor('k'), 14, 14552, 6451)).toBe(
      'https://basemaps.cartocdn.com/rastertiles/light_all/14/14552/6451.png?key=k',
    );
  });
});
