import { act, render, screen } from '@testing-library/react';
import { useDeferredValue } from 'react';
import { beforeEach, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { station } from '@/test/stations';
import { CITIES } from '@/lib/cities';
import { getCityActions, useAppStore, useCityState } from '@/lib/store';
import { ScoredAreasProvider } from '@/lib/scoring-react';
import { useScoredGrid } from '@/lib/scoring-grid-react';
import { GRID_LOCAL_KEYS, type BangkokGrid, type GridHeader } from '@/lib/bangkok-grid';
import { GridHotspotList, GridMatchCount } from './GridRanking';

const gridHandle = vi.hoisted(() => ({ current: null as unknown }));
vi.mock('@/lib/bangkok-grid', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/bangkok-grid')>();
  return { ...original, useBangkokGrid: () => ({ grid: gridHandle.current, error: false }) };
});

const header = {
  nx: 2, ny: 1, cell_m: 200, west: 100, east: 100.1, north: 14, south: 13.9,
  districts: ['flooded', 'safe'], stations: [], areas: [], fields: ['hub_siam'],
  scales: { weight: 100, station_dist_m: 10 },
} as unknown as GridHeader;
const planes: Record<string, Uint8Array> = {
  district: Uint8Array.from([1, 2]), weight: Uint8Array.from([100, 100]),
  station: Uint8Array.from([0, 0]), station_dist: Uint8Array.from([255, 255]),
  area: Uint8Array.from([0, 0]), hub_siam: Uint8Array.from([20, 20]),
};
for (const key of GRID_LOCAL_KEYS) planes[key] = Uint8Array.from(key === 'food' ? [10, 1] : [7, 7]);
const grid: BangkokGrid = { header, planes, cells: Uint32Array.from([0, 1]) };
const districts = [station('flooded', { flood_exposed: true, rent_1k: 10000 }), station('safe', { rent_1k: 12000 })];

function MapPassingCount() {
  const weights = useDeferredValue(useAppStore((s) => s.weights));
  const filters = useCityState((s) => s.filters);
  const hideFloodRisk = useCityState((s) => s.hideFloodRisk);
  const result = useScoredGrid(grid, districts, weights, filters, CITIES.bangkok.defaultFilters, hideFloodRisk);
  return <output data-testid="map-count">{result?.passing.cells}</output>;
}

beforeEach(() => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  gridHandle.current = grid;
});

it('keeps the grid map, match count and hotspots aligned when flood filtering changes', () => {
  render(<Providers city="bangkok"><ScoredAreasProvider primaryAreas={districts}>
    <MapPassingCount />
    <div data-testid="panel-count"><GridMatchCount districts={districts} /></div>
    <GridHotspotList districts={districts} />
  </ScoredAreasProvider></Providers>);

  expect(screen.getByTestId('map-count')).toHaveTextContent('2');
  expect(screen.getByTestId('panel-count')).toHaveTextContent('2 cells');
  expect(screen.getByRole('button', { name: /flooded/i })).toBeInTheDocument();

  act(() => getCityActions('bangkok').setHideFloodRisk(true));
  expect(screen.getByTestId('map-count')).toHaveTextContent('1');
  expect(screen.getByTestId('panel-count')).toHaveTextContent('1 of 2 cells match');
  expect(screen.queryByRole('button', { name: /flooded/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /safe/i })).toBeInTheDocument();

  act(() => getCityActions('bangkok').setHideFloodRisk(false));
  expect(screen.getByTestId('map-count')).toHaveTextContent('2');
  expect(screen.getByTestId('panel-count')).toHaveTextContent('2 cells');
  expect(screen.getByRole('button', { name: /flooded/i })).toBeInTheDocument();
});
