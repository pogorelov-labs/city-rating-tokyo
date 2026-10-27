import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { station } from '@/test/stations';
import { CITIES } from './cities';
import { DEFAULT_WEIGHTS } from './types';
import type { BangkokGrid, GridHeader } from './bangkok-grid';
import { useGridHotspots, useScoredGrid } from './scoring-grid-react';

const header = {
  nx: 2, ny: 1, cell_m: 200, west: 100, east: 100.1, north: 14, south: 13.9,
  districts: ['flooded', 'safe'], fields: [], scales: { weight: 100, station_dist_m: 10 },
} as unknown as GridHeader;
const grid: BangkokGrid = {
  header, cells: Uint32Array.from([0, 1]),
  planes: { district: Uint8Array.from([1, 2]), weight: Uint8Array.from([100, 100]), food: Uint8Array.from([8, 4]) },
};
const areas = [station('flooded', { flood_exposed: true, rent_1k: 10000 }), station('safe', { rent_1k: 12000 })];
const weights = { ...DEFAULT_WEIGHTS };
for (const key of Object.keys(weights) as (keyof typeof weights)[]) weights[key] = key === 'food' ? 100 : 0;
const defaults = CITIES.bangkok.defaultFilters;

describe('useScoredGrid', () => {
  it('shares scoring while preserving the existing map and panel flood behavior', () => {
    const { result } = renderHook(() => {
      const map = useScoredGrid(grid, areas, weights, defaults, defaults, true);
      const panel = useScoredGrid(grid, areas, weights, defaults, defaults);
      const panelAgain = useScoredGrid(grid, areas, weights, defaults, defaults);
      const spots = useGridHotspots(grid, panel, 10, true);
      const spotsAgain = useGridHotspots(grid, panelAgain, 10, true);
      return { map, panel, panelAgain, spots, spotsAgain };
    });
    expect(result.current.panel).toBe(result.current.panelAgain);
    expect(result.current.map!.scores).toBe(result.current.panel!.scores);
    expect(result.current.map!.anchors).toBe(result.current.panel!.anchors);
    expect([...result.current.map!.pass]).toEqual([0, 1]);
    expect([...result.current.panel!.pass]).toEqual([1, 1]);
    expect(result.current.map!.passing.cells).toBe(1);
    expect(result.current.panel!.passing.cells).toBe(2);
    expect(result.current.spots).toBe(result.current.spotsAgain);
    // Adjacent 200 m cells collapse to one 1.5 km-separated hotspot.
    expect(result.current.spots).toEqual([0]);
  });

  it('reuses scores across filter changes and recomputes the passing mask', () => {
    const { result, rerender } = renderHook(
      ({ maxRent }) => useScoredGrid(grid, areas, weights, { ...defaults, maxRent }, defaults),
      { initialProps: { maxRent: defaults.maxRent } },
    );
    const before = result.current!;
    rerender({ maxRent: 11000 });
    expect(result.current!.scores).toBe(before.scores);
    expect([...result.current!.pass]).toEqual([1, 0]);
    expect(result.current!.passing.cells).toBe(1);
  });
});
