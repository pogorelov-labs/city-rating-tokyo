import { render, screen, act } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'react';
import { Providers } from '@/test/providers';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from '@/lib/types';
import { useAppStore } from '@/lib/store';
import CitySwitcher from './CitySwitcher';

vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, ...props }: ComponentProps<'a'>) => <a {...props}>{children}</a>,
}));
afterEach(() => useAppStore.getState().resetWeights());

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
});
