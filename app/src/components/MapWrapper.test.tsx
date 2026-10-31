import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import MapWrapper from './MapWrapper';

vi.mock('./Map', () => ({ default: () => <div>Tokyo map</div> }));
vi.mock('./bangkok/BangkokMapRenderer', () => ({ default: () => <div>Bangkok map</div> }));
vi.mock('./MapControls', () => ({ default: () => null }));
vi.mock('./UrlSync', () => ({ default: () => null }));
vi.mock('./MobileStationCard', () => ({ default: () => null }));

it('keeps Tokyo on its own map even when a Bangkok lab renderer is requested', async () => {
  render(<Providers city="tokyo"><MapWrapper stations={[]} bangkokRenderer="maplibre" prototypeRenderer="maplibre" /></Providers>);
  expect(await screen.findByText('Tokyo map')).toBeInTheDocument();
  expect(screen.queryByText('Bangkok map')).not.toBeInTheDocument();
});
