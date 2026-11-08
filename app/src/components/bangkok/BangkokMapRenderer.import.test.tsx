import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import BangkokMapRenderer from './BangkokMapRenderer';

vi.mock('@/components/bangkok/maplibre/MapLibreMap', () => { throw new Error('chunk unavailable'); });

it('ends loading and shows the lab error when the renderer import fails', async () => {
  render(<Providers city="bangkok"><BangkokMapRenderer stations={[]} defaultRenderer="maplibre" prototypeRenderer="maplibre" /></Providers>);
  expect(await screen.findByRole('alert')).toHaveTextContent('3D map could not load');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
