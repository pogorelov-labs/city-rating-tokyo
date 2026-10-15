import { act } from '@testing-library/react';
import { vi } from 'vitest';

/** Frames deliberately independent of timers: a throttled tab can delay rAF
 * beyond the close fallback. Flushing a frame never also flushes its child. */
export function controlFrames() {
  let id = 0;
  const pending = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    pending.set(++id, callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (handle: number) => pending.delete(handle));
  return {
    pending,
    next() {
      act(() => {
        const frame = [...pending.values()];
        pending.clear();
        frame.forEach((callback) => callback(performance.now()));
      });
    },
  };
}
