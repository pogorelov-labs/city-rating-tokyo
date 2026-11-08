import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { controlFrames } from '@/test/animation-frames';
import MobileDrawer from './MobileDrawer';

vi.mock('./FilterPanel', () => ({ default: () => <div>Filter content</div> }));
let frames: ReturnType<typeof controlFrames>;
// jsdom has no top layer. These tests exercise transition races; focus
// containment, Escape and real drag/cancel events are covered in the browser.
const missingDialog = !HTMLDialogElement.prototype.showModal;
beforeAll(() => {
  if (!missingDialog) return;
  HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  HTMLDialogElement.prototype.close = function () { this.open = false; };
});
afterAll(() => {
  if (missingDialog) for (const key of ['showModal', 'close']) Reflect.deleteProperty(HTMLDialogElement.prototype, key);
});
beforeEach(() => {
  vi.useFakeTimers(); frames = controlFrames();
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

function mount() {
  const result = render(<Providers><MobileDrawer stations={[]} /></Providers>);
  const drawer = screen.getByText('Filter content').parentElement!.parentElement!;
  const open = () => fireEvent.click(screen.getByRole('button', { name: 'Filters' }));
  const close = () => fireEvent.click(screen.getByRole('button', { name: 'Close filters' }));
  return { ...result, drawer, open, close };
}

describe('MobileDrawer animation lifecycle', () => {
  it('keeps a short pull after a pause but dismisses the same distance as a flick', () => {
    const { drawer, open } = mount();
    open(); frames.next(); frames.next();
    const grip = drawer.querySelector<HTMLElement>('.map-filter-grip')!;
    grip.setPointerCapture = vi.fn();
    Object.defineProperty(drawer, 'offsetHeight', { value: 600 });
    const emit = (type: string, y: number, time: number) => {
      const event = Object.assign(new Event(type, { bubbles: true }), { pointerId: 1, isPrimary: true, button: 0, clientY: y });
      Object.defineProperty(event, 'timeStamp', { value: time });
      fireEvent(grip, event);
    };
    emit('pointerdown', 100, 10); emit('pointermove', 145, 55); emit('pointerup', 145, 300);
    expect(drawer).toHaveAttribute('data-open', 'true');
    emit('pointerdown', 100, 500); emit('pointermove', 145, 535); emit('pointerup', 145, 545);
    expect(drawer).toHaveAttribute('data-open', 'false');
  });

  it('closes immediately with reduced motion, without waiting for frames or a transition', () => {
    vi.stubGlobal('matchMedia', vi.fn((q: string) => ({ matches: q.includes('reduced-motion'), addEventListener: vi.fn(), removeEventListener: vi.fn() })));
    const { drawer, open, close } = mount();
    open(); expect(drawer).toHaveClass('translate-y-0');
    close(); expect(drawer).toHaveStyle({ display: 'none' });
    expect(frames.pending.size).toBe(0);
  });
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
    expect(drawer).toHaveClass('translate-y-0');
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
