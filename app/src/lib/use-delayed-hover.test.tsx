// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { HOVER_CLEAR_DELAY_MS, useDelayedHover } from './use-delayed-hover';

afterEach(() => vi.useRealTimers());
describe('useDelayedHover', () => {
  it('uses the same 150 ms default for both maps', () => {
    vi.useFakeTimers();
    const clear = vi.fn();
    const { result } = renderHook(() => useDelayedHover());
    act(() => result.current.schedule(clear));
    act(() => vi.advanceTimersByTime(HOVER_CLEAR_DELAY_MS - 1));
    expect(clear).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(clear).toHaveBeenCalledOnce();
    expect(HOVER_CLEAR_DELAY_MS).toBe(150);
  });
  it.each([120, 150])('delays dismissal by %ims and cancels it on re-entry', (delay) => {
    vi.useFakeTimers();
    const clear = vi.fn();
    const { result, unmount } = renderHook(() => useDelayedHover(delay));
    act(() => result.current.schedule(clear));
    act(() => vi.advanceTimersByTime(delay - 1));
    expect(clear).not.toHaveBeenCalled();
    act(() => result.current.cancel());
    act(() => vi.advanceTimersByTime(1));
    expect(clear).not.toHaveBeenCalled();
    act(() => result.current.schedule(clear));
    act(() => vi.advanceTimersByTime(delay));
    expect(clear).toHaveBeenCalledOnce();
    act(() => result.current.schedule(clear));
    unmount();
    act(() => vi.advanceTimersByTime(delay));
    expect(clear).toHaveBeenCalledOnce();
  });
});
