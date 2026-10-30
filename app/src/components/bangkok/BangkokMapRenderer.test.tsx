import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { getCityActions, useAppStore } from '@/lib/store';
import BangkokMapRenderer from './BangkokMapRenderer';

const engine = vi.hoisted(() => ({ throws: false }));

vi.mock('@/components/DistrictMap', () => ({ default: ({ prototype }: { prototype?: boolean }) => <div>Standard engine {prototype ? 'lab' : 'normal'}</div> }));
vi.mock('@/components/bangkok/maplibre/MapLibreMap', () => ({ default: ({ prototype, onUnavailable, onImportFailure }: { prototype?: boolean; onUnavailable: (reason: 'webgl' | 'load' | 'context') => void; onImportFailure: () => void }) => { if (engine.throws) throw new Error('renderer crashed'); return <div>3D engine {prototype ? 'lab' : 'normal'}<button onClick={() => onUnavailable('webgl')}>Simulate failure</button><button onClick={onImportFailure}>Simulate import failure</button></div>; } }));

beforeEach(() => { engine.throws = false; useAppStore.setState(useAppStore.getInitialState(), true); });

it('falls back while retaining city state and permits a manual renderer change', async () => {
  const actions = getCityActions('bangkok');
  act(() => { actions.setSelectedStation('district.test'); actions.setHideFloodRisk(true); actions.addCompareStation('district.test'); });
  act(() => useAppStore.getState().setWeight('food', 3));
  window.history.replaceState(null, '', '?w=shared&level=grid');
  const before = useAppStore.getState().cities.bangkok;
  const weights = useAppStore.getState().weights;
  const url = window.location.href;
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="maplibre" /></Providers>);
  fireEvent.click(await screen.findByRole('button', { name: 'Simulate failure' }));
  expect(await screen.findByText('Standard engine normal')).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('WebGL is not supported');
  expect(screen.getByLabelText('3D map unavailable: WebGL is not supported.')).toBeInTheDocument();
  expect(useAppStore.getState().cities.bangkok).toEqual(before);
  expect(useAppStore.getState().weights).toEqual(weights);
  expect(window.location.href).toBe(url);
  fireEvent.change(screen.getByRole('combobox', { name: /map/i }), { target: { value: 'maplibre' } });
  expect(await screen.findByText('3D engine normal')).toBeInTheDocument();
  expect(useAppStore.getState().cities.bangkok).toEqual(before);
  expect(useAppStore.getState().weights).toEqual(weights);
  expect(window.location.href).toBe(url);
});

it('honors explicit lab renderer over the rollback default', async () => {
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="leaflet" prototypeRenderer="maplibre" /></Providers>);
  expect(await screen.findByText('3D engine lab')).toBeInTheDocument();
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});

it('starts with the configured standard renderer', async () => {
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="leaflet" /></Providers>);
  expect(await screen.findByText('Standard engine normal')).toBeInTheDocument();
});

it('catches a renderer crash and preserves the shared state', async () => {
  const actions = getCityActions('bangkok');
  act(() => { actions.setSelectedStation('district.test'); actions.setMaxRent(12000); actions.addCompareStation('district.test'); });
  const before = useAppStore.getState().cities.bangkok;
  const url = window.location.href;
  engine.throws = true;
  const error = vi.spyOn(console, 'error').mockImplementation(() => {});
  try {
    render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="maplibre" /></Providers>);
    expect(await screen.findByText('Standard engine normal')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('3D map could not load');
    expect(useAppStore.getState().cities.bangkok).toEqual(before);
    expect(window.location.href).toBe(url);
  } finally { error.mockRestore(); }
});

it('does not offer a retry after a code download failure', async () => {
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="maplibre" /></Providers>);
  fireEvent.click(await screen.findByRole('button', { name: 'Simulate import failure' }));
  expect(await screen.findByText('Standard engine normal')).toBeInTheDocument();
  expect(screen.getByRole('option', { name: '3D map' })).toBeDisabled();
});

it('shows the actual lab failure without switching renderers', async () => {
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="leaflet" prototypeRenderer="maplibre" /></Providers>);
  fireEvent.click(await screen.findByRole('button', { name: 'Simulate failure' }));
  expect(screen.getByRole('alert')).toHaveTextContent('WebGL is not supported');
  expect(screen.getByText('3D engine lab')).toBeInTheDocument();
  expect(screen.queryByText('Standard engine lab')).not.toBeInTheDocument();
});
