import { render, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { initialCityState, useAppStore } from '@/lib/store';
import { GRID_HEADER, type BangkokGrid } from '@/lib/bangkok-grid';
import BangkokCellSelectionGuard from './BangkokCellSelectionGuard';

const state = vi.hoisted(() => ({ grid: null as BangkokGrid | null, enabled: false }));
vi.mock('@/lib/bangkok-grid', async importOriginal => ({
  ...await importOriginal<typeof import('@/lib/bangkok-grid')>(),
  useBangkokGrid: (enabled: boolean) => { state.enabled = enabled; return { grid: state.grid, error: false }; },
}));

beforeEach(() => {
  state.grid = null;
  state.enabled = false;
  useAppStore.setState(s => ({ cities: { ...s.cities, bangkok: initialCityState('bangkok') } }));
});

it('removes only invalid cell state and keeps pending selections until mask membership is known', async () => {
  useAppStore.getState().updateCity('bangkok', {
    selectedStation: 'cell.39725', compareStations: ['st.asok', 'cell.0', 'cell.999999999999999'],
    hideAdultZones: true, hideFloodRisk: true,
  });
  const view = render(<Providers city="bangkok"><BangkokCellSelectionGuard /></Providers>);
  await waitFor(() => expect(useAppStore.getState().cities.bangkok.compareStations).toEqual(['st.asok', 'cell.0']));
  expect(useAppStore.getState().cities.bangkok.selectedStation).toBe('cell.39725');
  expect(state.enabled).toBe(true);
  const district = new Uint8Array(GRID_HEADER.nx * GRID_HEADER.ny);
  district[39725] = 1;
  state.grid = { header: GRID_HEADER, planes: { district }, cells: new Uint32Array([39725]) };
  view.rerender(<Providers city="bangkok"><BangkokCellSelectionGuard /></Providers>);
  await waitFor(() => expect(useAppStore.getState().cities.bangkok.compareStations).toEqual(['st.asok']));
  const city = useAppStore.getState().cities.bangkok;
  expect(city.selectedStation).toBe('cell.39725');
  expect(city.hideAdultZones).toBe(true);
  expect(city.hideFloodRisk).toBe(true);
});
