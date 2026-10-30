import { StrictMode } from 'react';
import { act, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CityProvider } from '@/lib/city-context';
import { getCityActions, useAppStore } from '@/lib/store';
import UrlSync from './UrlSync';

beforeEach(() => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  window.history.replaceState(null, '', '/');
  vi.useFakeTimers();
});
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });
const mount = (city: 'tokyo' | 'bangkok' = 'tokyo') => render(
  <StrictMode><CityProvider city={city}><UrlSync /></CityProvider></StrictMode>,
);

describe('UrlSync browser/store contract', () => {
  it('hydrates once under StrictMode and rerenders, into only the current city', () => {
    window.history.replaceState(null, '', '/bangkok?s=pathum-wan&utm_source=campaign');
    const hydrate = vi.spyOn(useAppStore.getState(), 'hydrateFromUrl');
    const { rerender } = mount('bangkok');
    rerender(<StrictMode><CityProvider city="bangkok"><UrlSync /></CityProvider></StrictMode>);
    expect(hydrate).toHaveBeenCalledTimes(1);
    expect(useAppStore.getState().cities.bangkok.selectedStation).toBe('pathum-wan');
    expect(useAppStore.getState().cities.tokyo.selectedStation).toBeNull();
  });

  it('hydrates Bangkok safety flags from a link and keeps changes shareable', () => {
    window.history.replaceState(null, '', '/bangkok?lv=grid&flood=1&adult=1');
    mount('bangkok');
    expect(useAppStore.getState().cities.bangkok).toMatchObject({
      level: 'grid', hideFloodRisk: true, hideAdultZones: true, hideHighSeismic: false,
    });
    expect(useAppStore.getState().cities.tokyo.hideFloodRisk).toBe(false);

    act(() => getCityActions('bangkok').setHideAdultZones(false));
    act(() => vi.advanceTimersByTime(300));
    const params = new URLSearchParams(window.location.search);
    expect(params.get('flood')).toBe('1');
    expect(params.has('adult')).toBe(false);
  });

  it('clears previously enabled flags omitted from a link and restores Tokyo seismic filtering', () => {
    getCityActions('tokyo').setHideFloodRisk(true);
    getCityActions('tokyo').setHideAdultZones(true);
    window.history.replaceState(null, '', '/?s=shibuya&seismic=1');
    mount();
    expect(useAppStore.getState().cities.tokyo).toMatchObject({
      selectedStation: 'shibuya', hideFloodRisk: false, hideAdultZones: false, hideHighSeismic: true,
    });
  });

  it('does not erase tracking parameters just by landing or rerendering', () => {
    window.history.replaceState(null, '', '/?utm_source=campaign&utm_medium=email&s=alpha');
    const replace = vi.spyOn(window.history, 'replaceState');
    mount(); act(() => vi.advanceTimersByTime(1000));
    expect(replace).not.toHaveBeenCalled();
    expect(new URLSearchParams(window.location.search).get('utm_source')).toBe('campaign');
  });

  it('writes carried state immediately on no-query arrival and preserves the locale/city path', () => {
    getCityActions('bangkok').setSelectedStation('pathum-wan');
    window.history.replaceState(null, '', '/ru/bangkok');
    const replace = vi.spyOn(window.history, 'replaceState');
    mount('bangkok');
    expect(replace).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe('/ru/bangkok');
    expect(new URLSearchParams(window.location.search).get('s')).toBe('pathum-wan');
  });

  it('does not write an empty default state', () => {
    const replace = vi.spyOn(window.history, 'replaceState');
    mount(); act(() => vi.advanceTimersByTime(1000));
    expect(replace).not.toHaveBeenCalled();
  });

  it('coalesces changes into one replaceState 300ms after the last change', () => {
    const replace = vi.spyOn(window.history, 'replaceState');
    mount();
    act(() => getCityActions('tokyo').setSelectedStation('alpha'));
    act(() => vi.advanceTimersByTime(200));
    act(() => getCityActions('tokyo').setSelectedStation('beta'));
    act(() => vi.advanceTimersByTime(299));
    expect(replace).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(replace).toHaveBeenCalledTimes(1);
    expect(new URLSearchParams(window.location.search).get('s')).toBe('beta');
  });

  it('ignores hover changes without delaying a pending shareable selection', () => {
    const replace = vi.spyOn(window.history, 'replaceState');
    mount();
    act(() => getCityActions('tokyo').setHoveredStation('alpha'));
    act(() => vi.advanceTimersByTime(500));
    expect(replace).not.toHaveBeenCalled();
    act(() => getCityActions('tokyo').setSelectedStation('alpha'));
    act(() => vi.advanceTimersByTime(200));
    act(() => getCityActions('tokyo').setHoveredStation(null));
    act(() => vi.advanceTimersByTime(100));
    expect(replace).toHaveBeenCalledTimes(1);
    expect(new URLSearchParams(window.location.search).get('s')).toBe('alpha');
  });

  it('unmount cancels pending writeback and unsubscribes', () => {
    const replace = vi.spyOn(window.history, 'replaceState');
    const { unmount } = mount();
    act(() => getCityActions('tokyo').setSelectedStation('alpha'));
    unmount();
    act(() => getCityActions('tokyo').setSelectedStation('beta'));
    act(() => vi.advanceTimersByTime(1000));
    expect(replace).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });
});
