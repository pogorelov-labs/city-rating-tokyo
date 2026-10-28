// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useDelayedHover } from './use-delayed-hover';

afterEach(() => vi.useRealTimers());
describe('useDelayedHover', () => {
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
