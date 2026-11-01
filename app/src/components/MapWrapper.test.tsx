import { act, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import MapWrapper from './MapWrapper';
import { getCityActions, initialCityState, useAppStore } from '@/lib/store';

vi.mock('./Map', () => ({ default: () => <div>Tokyo map</div> }));
vi.mock('./bangkok/BangkokMapRenderer', () => ({ default: () => <div>Bangkok map</div> }));
vi.mock('./MapControls', () => ({ default: () => null }));
vi.mock('./UrlSync', () => ({ default: () => null }));
vi.mock('./MobileStationCard', () => ({ default: () => null }));
vi.mock('./bangkok/BangkokCellSelectionGuard', () => ({ default: () => <div>Cell validation</div> }));

it('keeps Tokyo on its own map even when a Bangkok lab renderer is requested', async () => {
  render(<Providers city="tokyo"><MapWrapper stations={[]} bangkokRenderer="maplibre" prototypeRenderer="maplibre" /></Providers>);
  expect(await screen.findByText('Tokyo map')).toBeInTheDocument();
  expect(screen.queryByText('Bangkok map')).not.toBeInTheDocument();
});

it('loads the cell guard only for a selected or compared cell', async () => {
  useAppStore.setState(s => ({ cities: { ...s.cities, bangkok: initialCityState('bangkok') } }));
  render(<Providers city="bangkok"><MapWrapper stations={[]} bangkokRenderer="maplibre" /></Providers>);
  expect(await screen.findByText('Bangkok map')).toBeInTheDocument();
  expect(screen.queryByText('Cell validation')).not.toBeInTheDocument();
  act(() => getCityActions('bangkok').addCompareStation('cell.39725'));
  expect(await screen.findByText('Cell validation')).toBeInTheDocument();
});
