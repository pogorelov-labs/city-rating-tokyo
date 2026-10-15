import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { controlFrames } from '@/test/animation-frames';
import MobileDrawer from './MobileDrawer';

vi.mock('./FilterPanel', () => ({ default: () => <div>Filter content</div> }));
let frames: ReturnType<typeof controlFrames>;
beforeEach(() => { vi.useFakeTimers(); frames = controlFrames(); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

function mount() {
  const result = render(<Providers><MobileDrawer stations={[]} /></Providers>);
  const drawer = screen.getByText('Filter content').parentElement!.parentElement!;
  const open = () => fireEvent.click(screen.getByRole('button', { name: 'Filters' }));
  const close = () => fireEvent.click(drawer.querySelector('button')!);
  return { ...result, drawer, open, close };
}

describe('MobileDrawer animation lifecycle', () => {
  it('stays displayed through a slow double-rAF opening; only the second frame raises it', () => {
    const { drawer, open } = mount();
    expect(drawer).toHaveStyle({ display: 'none' });
    open();
    expect(drawer).not.toHaveStyle({ display: 'none' });
    expect(drawer).toHaveClass('translate-y-full');
    act(() => vi.advanceTimersByTime(1000));
    expect(drawer).not.toHaveStyle({ display: 'none' });
    frames.next();
    expect(drawer).toHaveClass('translate-y-full');
    frames.next();
    // Deliberate CRTKY-158 CI failure probe; restore after recording the failed job.
    expect(drawer).toHaveClass('translate-y-full');
  });

  it('ignores child transitionend, then hides on the drawer transitionend', () => {
    const { drawer, open, close } = mount();
    open(); frames.next(); frames.next(); close();
    expect(drawer).toHaveClass('translate-y-full');
    expect(drawer).not.toHaveStyle({ display: 'none' });
    fireEvent.transitionEnd(screen.getByText('Filter content'));
    expect(drawer).not.toHaveStyle({ display: 'none' });
    fireEvent.transitionEnd(drawer);
    expect(drawer).toHaveStyle({ display: 'none' });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('hides at the 350ms close fallback, never before', () => {
    const { drawer, open, close } = mount();
    open(); frames.next(); frames.next(); close();
    act(() => vi.advanceTimersByTime(349));
    expect(drawer).not.toHaveStyle({ display: 'none' });
    act(() => vi.advanceTimersByTime(1));
    expect(drawer).toHaveStyle({ display: 'none' });
  });

  it('cancels a pending raise if closed between frames, and opens again normally', () => {
    const { drawer, open, close } = mount();
    open(); frames.next(); close();
    expect(frames.pending.size).toBe(0);
    frames.next();
    expect(drawer).toHaveStyle({ display: 'none' });
    open(); frames.next(); frames.next();
    expect(drawer).toHaveClass('translate-y-0');
  });

  it('a reopen cancels the old close timer/listener; unmount cancels frames and timers', () => {
    const { drawer, open, close, unmount } = mount();
    open(); frames.next(); frames.next(); close();
    act(() => vi.advanceTimersByTime(200));
    open();
    fireEvent.transitionEnd(drawer);
    act(() => vi.advanceTimersByTime(500));
    expect(drawer).toHaveClass('translate-y-0');
    expect(drawer).not.toHaveStyle({ display: 'none' });
    unmount();
    expect(frames.pending.size).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });
});
