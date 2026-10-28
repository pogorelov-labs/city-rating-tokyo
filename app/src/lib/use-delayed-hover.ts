'use client';

import { useCallback, useEffect, useRef } from 'react';

// 150 ms gives pointers time to reach a tooltip without a perceptible delay.
export const HOVER_CLEAR_DELAY_MS = 150;

/** Delay hover dismissal while allowing movement into the tooltip to cancel it. */
export function useDelayedHover(delay = HOVER_CLEAR_DELAY_MS) {
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const cancel = useCallback(() => clearTimeout(timer.current), []);
  const schedule = useCallback((clear: () => void) => {
    timer.current = setTimeout(clear, delay);
  }, [delay]);
  useEffect(() => cancel, [cancel]);
  return { cancel, schedule };
}
