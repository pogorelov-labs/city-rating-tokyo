import { render, screen, act, fireEvent } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'react';
import { Providers } from '@/test/providers';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from '@/lib/types';
import { getCityActions, useAppStore } from '@/lib/store';
import { decodeParamsToState } from '@/lib/url-state';
import CitySwitcher from './CitySwitcher';

const push = vi.hoisted(() => vi.fn());
vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({ push }),
  Link: ({ children, onNavigate, ...props }: ComponentProps<'a'> & { onNavigate?: (event: { preventDefault: () => void }) => void }) =>
    <a {...props} onClick={event => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); onNavigate?.({ preventDefault: () => {} });
    }}>{children}</a>,
}));
afterEach(() => { useAppStore.setState(useAppStore.getInitialState(), true); push.mockClear(); });

describe('city switcher links', () => {
  it('encodes live shared weights and no city-specific filters, then removes defaults', () => {
    window.history.replaceState(null, '', '/?mr=150000&s=shibuya&c=shibuya');
    const weights = PRESET_PROFILES.find(profile => profile.id === 'family')!.weights;
    act(() => useAppStore.getState().setAllWeights(weights));
    render(<Providers><CitySwitcher /></Providers>);
    const bangkok = screen.getByRole('link', { name: 'Bangkok' });
    const url = new URL(bangkok.getAttribute('href')!, 'https://example.test');
    expect(url.pathname).toBe('/bangkok');
    expect(url.searchParams.get('w')).toBe(Object.values(weights).join(','));
    expect([...url.searchParams.keys()]).toEqual(['w']);
    expect(screen.getByRole('link', { name: 'Tokyo' })).toHaveAttribute('aria-current', 'page');
    act(() => useAppStore.getState().setAllWeights(DEFAULT_WEIGHTS));
    expect(bangkok).toHaveAttribute('href', '/bangkok');
  });

  it('uses the destination city slice and shared weights for a normal same-tab switch', () => {
    const target = getCityActions('bangkok');
    act(() => {
      target.setHideFloodRisk(true); target.setHideAdultZones(true); target.setMaxRent(25000);
      target.setLevel('station'); target.setSelectedStation('st.asok'); target.addCompareStation('st.nana');
      getCityActions('tokyo').setHideHighSeismic(true); useAppStore.getState().setWeight('food', 3);
    });
    render(<Providers><CitySwitcher /></Providers>);
    const link = screen.getByRole('link', { name: 'Bangkok' });
    expect([...new URL(link.getAttribute('href')!, 'https://example.test').searchParams.keys()]).toEqual(['w']);
    fireEvent.click(link);
    expect(push).toHaveBeenCalledTimes(1);
    const route = new URL(push.mock.calls[0][0], 'https://example.test');
    expect(route.pathname).toBe('/bangkok');
    expect(decodeParamsToState(route.searchParams, 'bangkok')).toMatchObject({
      level: 'station', hideFloodRisk: true, hideAdultZones: true, hideHighSeismic: false,
      selectedStation: 'st.asok', compareStations: ['st.nana'], filters: { maxRent: 25000 },
      weights: useAppStore.getState().weights,
    });
  });

  it('does not leak the source city filters into a clean destination', () => {
    act(() => { getCityActions('tokyo').setHideFloodRisk(true); getCityActions('tokyo').setHideAdultZones(true);
      getCityActions('tokyo').setHideHighSeismic(true); getCityActions('tokyo').setSelectedStation('shibuya');
      useAppStore.getState().setWeight('food', 3); });
    render(<Providers><CitySwitcher /></Providers>);
    const link = screen.getByRole('link', { name: 'Bangkok' });
    fireEvent.click(link);
    expect(push).not.toHaveBeenCalled();
    expect([...new URL(link.getAttribute('href')!, 'https://example.test').searchParams.keys()]).toEqual(['w']);
  });

  it('restores Tokyo seismic and its own selection from Bangkok', () => {
    act(() => { getCityActions('tokyo').setHideHighSeismic(true); getCityActions('tokyo').setHideFloodRisk(true);
      getCityActions('tokyo').setSelectedStation('shibuya'); useAppStore.getState().setWeight('food', 3); });
    render(<Providers city="bangkok"><CitySwitcher /></Providers>);
    fireEvent.click(screen.getByRole('link', { name: 'Tokyo' }));
    const route = new URL(push.mock.calls[0][0], 'https://example.test');
    expect(route.pathname).toBe('/');
    expect(decodeParamsToState(route.searchParams, 'tokyo')).toMatchObject({
      hideHighSeismic: true, hideFloodRisk: true, selectedStation: 'shibuya', weights: useAppStore.getState().weights,
    });
  });

  it.each([{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }])
  ('leaves modified navigation to the weights-only href: %o', (options) => {
    render(<Providers><CitySwitcher /></Providers>);
    const link = screen.getByRole('link', { name: 'Bangkok' });
    const prevent = (event: Event) => event.preventDefault();
    document.addEventListener('click', prevent);
    try { fireEvent.click(link, options); expect(push).not.toHaveBeenCalled(); }
    finally { document.removeEventListener('click', prevent); }
  });

  it('does not navigate after an earlier handler canceled the click or on the active city', () => {
    render(<Providers><CitySwitcher /></Providers>);
    const prevent = (event: Event) => event.preventDefault();
    document.addEventListener('click', prevent, true);
    try { fireEvent.click(screen.getByRole('link', { name: 'Bangkok' })); }
    finally { document.removeEventListener('click', prevent, true); }
    fireEvent.click(screen.getByRole('link', { name: 'Tokyo' }));
    expect(push).not.toHaveBeenCalled();
  });

});
