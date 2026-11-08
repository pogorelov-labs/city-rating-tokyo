import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import * as gridMath from './bangkok-grid';
import { station } from '@/test/stations';
import { CITIES } from './cities';
import { DEFAULT_WEIGHTS } from './types';
import type { BangkokGrid, GridHeader } from './bangkok-grid';
import { useGridHotspots, useScoredGrid } from './scoring-grid-react';

const header = {
  nx: 2, ny: 1, cell_m: 200, west: 100.561, east: 100.566, north: 13.7385, south: 13.7367,
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
  it('shares a top-ten hotspot pass with the five map markers, even when the map mounts first', () => {
    const input = { ...grid, header: { ...header, nx: 50, cell_m: 2000, west: 100, east: 102 }, cells: Uint32Array.from({ length: 50 }, (_, i) => i),
      planes: { district: new Uint8Array(50).fill(1), weight: new Uint8Array(50).fill(100), food: Uint8Array.from({ length: 50 }, (_, i) => i % 10 + 1) } };
    const spy = vi.spyOn(gridMath, 'gridHotspots');
    try {
      const { result } = renderHook(() => {
        const scored = useScoredGrid(input, areas, weights, defaults, defaults)!;
        return { map: useGridHotspots(input, scored, 5, true), list: useGridHotspots(input, scored, 10, true) };
      });
      expect(result.current.map).toHaveLength(5);
      expect(result.current.list).toHaveLength(10);
      expect(result.current.map).toEqual(result.current.list.slice(0, 5));
      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy.mock.calls[0][3]).toBe(10);
    } finally { spy.mockRestore(); }
  });
  it('shares the same flood mask for map and panel, and separates the unfiltered result', () => {
    const { result } = renderHook(() => {
      const map = useScoredGrid(grid, areas, weights, defaults, defaults, true);
      const panel = useScoredGrid(grid, areas, weights, defaults, defaults, true);
      const unfiltered = useScoredGrid(grid, areas, weights, defaults, defaults);
      const spots = useGridHotspots(grid, panel, 10, true);
      const spotsAgain = useGridHotspots(grid, map, 10, true);
      return { map, panel, unfiltered, spots, spotsAgain };
    });
    expect(result.current.map).toBe(result.current.panel);
    expect(result.current.map!.scores).toBe(result.current.panel!.scores);
    expect(result.current.map!.anchors).toBe(result.current.panel!.anchors);
    expect([...result.current.map!.pass]).toEqual([0, 1]);
    expect([...result.current.panel!.pass]).toEqual([0, 1]);
    expect([...result.current.unfiltered!.pass]).toEqual([1, 1]);
    expect(result.current.map!.passing.cells).toBe(1);
    expect(result.current.panel!.passing.cells).toBe(1);
    expect(result.current.unfiltered!.passing.cells).toBe(2);
    expect(result.current.spots).toBe(result.current.spotsAgain);
    expect(result.current.spots).toEqual([1]);
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

  it('shares family-filter results between consumers without reusing an unfiltered mask', () => {
    const { result, rerender } = renderHook(
      ({ family }) => ({
        map: useScoredGrid(grid, areas, weights, defaults, defaults, false, family),
        panel: useScoredGrid(grid, areas, weights, defaults, defaults, false, family),
      }),
      { initialProps: { family: false } },
    );
    const before = result.current.map!;
    expect([...before.pass]).toEqual([1, 1]);
    rerender({ family: true });
    expect(result.current.map).toBe(result.current.panel);
    expect(result.current.map!.scores).toBe(before.scores);
    expect([...result.current.map!.pass]).toEqual([0, 1]);
    rerender({ family: false });
    expect([...result.current.map!.pass]).toEqual([1, 1]);
  });
});
