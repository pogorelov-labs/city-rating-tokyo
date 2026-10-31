import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from '@testing-library/react';
import { getCityActions, useAppStore } from '@/lib/store';
import UrlSync from './UrlSync';
import { Providers } from '@/test/providers';
import LocaleSwitcher from './LocaleSwitcher';

const replace = vi.hoisted(() => vi.fn());
vi.mock('@/i18n/navigation', () => ({ useRouter: () => ({ replace }), usePathname: () => '/station/kichijoji' }));

beforeEach(() => { replace.mockClear(); useAppStore.setState(useAppStore.getInitialState(), true); });
afterEach(() => { vi.useRealTimers(); });
describe('locale navigation retains the selected guide/map context', () => {
  it('keeps weights, destination and comparison when switching to Japanese', () => {
    window.history.replaceState(null, '', '/station/kichijoji?w=12,8,20,25,0,20,0,0,0,15&hub=tokyo&reference=mitaka');
    render(<Providers><LocaleSwitcher /></Providers>);
    fireEvent.click(screen.getByRole('button', { name: 'JA' }));
    expect(replace).toHaveBeenCalledWith({ pathname: '/station/kichijoji', query: {
      w: '12,8,20,25,0,20,0,0,0,15', hub: 'tokyo', reference: 'mitaka',
    } }, { locale: 'ja' });
  });
  it('flushes pending map weights and flags before constructing the locale route', () => {
    vi.useFakeTimers();
    window.history.replaceState(null, '', '/bangkok');
    render(<Providers city="bangkok"><UrlSync /><LocaleSwitcher /></Providers>);
    act(() => { getCityActions('bangkok').setHideFloodRisk(true); useAppStore.getState().setWeight('food', 3); });
    fireEvent.click(screen.getByRole('button', { name: 'JA' }));
    const query = replace.mock.calls[0][0].query;
    expect(query.flood).toBe('1');
    expect(query.w).toBeTruthy();
    const replaceState = vi.spyOn(window.history, 'replaceState');
    act(() => vi.advanceTimersByTime(300));
    expect(replaceState).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });

});
