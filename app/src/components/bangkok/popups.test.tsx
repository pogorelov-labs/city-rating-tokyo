import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import type { ComponentProps, ReactNode } from 'react';
import { Providers, messages } from '@/test/providers';
import { station } from '@/test/stations';
import { useAppStore } from '@/lib/store';
import { DistrictPopupBody, StationAreaPopupBody } from './popups';

const closePopup = vi.hoisted(() => vi.fn());
vi.mock('react-leaflet', () => ({ useMap: () => ({ closePopup }) }));
vi.mock('@/i18n/navigation', () => ({ Link: ({ children, ...props }: ComponentProps<'a'> & { children: ReactNode }) => <a {...props}>{children}</a> }));

beforeEach(() => { useAppStore.setState(useAppStore.getInitialState(), true); closePopup.mockClear(); });

it.each(['district', 'station'] as const)('keeps %s guide links, missing-rent disclosure and popup dismissal', (kind) => {
  act(() => useAppStore.getState().setWeight('food', 3));
  const area = { ...station(kind === 'station' ? 'st.asok' : 'khlong-toei', { rent_1k: null }), score: 7.2 };
  const common = { color: '#fff', isCompared: false, compareFull: false, onCompare: vi.fn(), onUncompare: vi.fn() };
  const bubble = vi.fn();
  render(<Providers city="bangkok"><div onClick={bubble}>{kind === 'station'
    ? <StationAreaPopupBody {...common} area={area} lineChip={() => null} districtName={(slug) => slug} />
    : <DistrictPopupBody {...common} district={area} />}</div></Providers>);
  expect(screen.getByText(messages.en.areaGuide.rent.provenance.unavailable)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /explore/i }).getAttribute('href'))
    .toMatch(kind === 'station' ? /^\/bangkok\/station\/asok\?w=/ : /^\/bangkok\/district\/khlong-toei\?w=/);
  fireEvent.click(screen.getByRole('button', { name: messages.en.areaGuide.compact.close }));
  expect(closePopup).toHaveBeenCalledOnce();
  expect(bubble).not.toHaveBeenCalled();
});
