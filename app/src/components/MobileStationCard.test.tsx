import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { station } from '@/test/stations';
import { controlFrames } from '@/test/animation-frames';
import { getCityActions, useAppStore } from '@/lib/store';
import MobileStationCard from './MobileStationCard';

vi.mock('@/lib/use-is-touch', () => ({ useIsTouch: () => true }));
vi.mock('@/i18n/navigation', () => ({ Link: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
const stations = [station('alpha'), station('beta')];
let frames: ReturnType<typeof controlFrames>;
const select = (slug: string | null) => act(() => getCityActions('tokyo').setSelectedStation(slug));
const fly = (value: boolean) => act(() => useAppStore.getState().setIsFlying(value));
beforeEach(() => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  vi.useFakeTimers(); frames = controlFrames();
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
const mount = () => render(<Providers><MobileStationCard stations={stations} /></Providers>);

describe('MobileStationCard animation lifecycle', () => {
  it('has no card until selected, stays visible during a slow double-rAF, and swaps content while open', () => {
    mount();
    expect(screen.queryByRole('dialog')).toBeNull();
    select('alpha');
    const card = screen.getByRole('dialog', { name: 'alpha' });
    act(() => vi.advanceTimersByTime(1000));
    expect(card).not.toHaveStyle({ display: 'none' });
    expect(card).toHaveClass('translate-y-full');
    frames.next(); expect(card).toHaveClass('translate-y-full');
    frames.next(); expect(card).toHaveClass('translate-y-0');
    select('beta');
    expect(screen.getByRole('dialog', { name: 'beta' })).toBe(card);
    expect(card).toHaveClass('translate-y-0');
  });

  it('lowers for flight, ignores child transitions and hides only after its own transition', () => {
    mount(); select('alpha'); frames.next(); frames.next();
    const card = screen.getByRole('dialog');
    fly(true);
    expect(card).toHaveClass('translate-y-full');
    fireEvent.transitionEnd(card.querySelector('button')!);
    expect(card).not.toHaveStyle({ display: 'none' });
    fireEvent.transitionEnd(card);
    expect(card).toHaveStyle({ display: 'none' });
    expect(vi.getTimerCount()).toBe(0);
    fly(false); frames.next(); frames.next();
    expect(card).toHaveClass('translate-y-0');
  });

  it('uses its existing 300ms close fallback when transitionend is absent', () => {
    mount(); select('alpha'); frames.next(); frames.next();
    const card = screen.getByRole('dialog');
    fly(true);
    act(() => vi.advanceTimersByTime(299));
    expect(card).not.toHaveStyle({ display: 'none' });
    act(() => vi.advanceTimersByTime(1));
    expect(card).toHaveStyle({ display: 'none' });
  });

  it('landing before the close timeout cancels the old close, including a late transitionend', () => {
    mount(); select('alpha'); frames.next(); frames.next();
    const card = screen.getByRole('dialog');
    fly(true); act(() => vi.advanceTimersByTime(150)); fly(false);
    fireEvent.transitionEnd(card);
    act(() => vi.advanceTimersByTime(500));
    expect(card).not.toHaveStyle({ display: 'none' });
    expect(card).toHaveClass('translate-y-0');
  });

  it('deselecting between frames cancels the raise; a later selection starts lowered', () => {
    const { unmount } = mount();
    select('alpha'); frames.next(); select(null);
    expect(frames.pending.size).toBe(0);
    expect(screen.queryByRole('dialog')).toBeNull();
    select('beta');
    expect(screen.getByRole('dialog')).toHaveClass('translate-y-full');
    frames.next(); frames.next();
    fireEvent.click(screen.getByRole('button', { name: 'Close station card' }));
    expect(useAppStore.getState().cities.tokyo.selectedStation).toBeNull();
    expect(screen.queryByRole('dialog')).toBeNull();
    select('alpha'); unmount();
    expect(frames.pending.size).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });
});
