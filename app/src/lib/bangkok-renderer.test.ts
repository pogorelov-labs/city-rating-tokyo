import { describe, expect, it } from 'vitest';
import { resolveBangkokRenderer } from './bangkok-renderer';

describe('Bangkok renderer build setting', () => {
  it('defaults to 3D and supports an explicit standard-map rollback', () => {
    expect(resolveBangkokRenderer(undefined)).toBe('maplibre');
    expect(resolveBangkokRenderer('maplibre')).toBe('maplibre');
    expect(resolveBangkokRenderer('leaflet')).toBe('leaflet');
    expect(resolveBangkokRenderer('invalid')).toBe('maplibre');
  });
});
