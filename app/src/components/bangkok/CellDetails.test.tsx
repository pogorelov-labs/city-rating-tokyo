import { act, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { ComponentProps, ReactNode } from 'react';
import { Providers } from '@/test/providers';
import { station } from '@/test/stations';
import { useAppStore } from '@/lib/store';
import { CellDetails } from './CellDetails';

vi.mock('@/i18n/navigation', () => ({ Link: ({ children, ...props }: ComponentProps<'a'> & { children: ReactNode }) => <a {...props}>{children}</a> }));

it('carries current guide weights through both cell area links', () => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  act(() => useAppStore.getState().setWeight('food', 3));
  const ratings = station('test').ratings!;
  render(<Providers city="bangkok"><CellDetails info={{ index: 1, ratings, districtSlug: 'khlong-toei', districtIndex: 0,
    weight: 1, hubMinutes: {}, minCommute: 10, stationId: 'asok', stationDistanceM: 200, areaId: 'asok' }}
    score={7} medians={ratings} stationName={() => 'Asok'} areaName={() => 'Asok'} districtName={() => 'Khlong Toei'} /></Providers>);
  const links = screen.getAllByRole('link');
  expect(links.map(link => link.getAttribute('href'))).toEqual([
    expect.stringMatching(/^\/bangkok\/district\/khlong-toei\?w=/),
    expect.stringMatching(/^\/bangkok\/station\/asok\?w=/),
  ]);
  expect(links.map(link => link.getAttribute('data-umami-event'))).toEqual(['cell-district', 'cell-station-area']);
});
