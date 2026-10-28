'use client';

import { useCallback, useEffect, useRef } from 'react';

/** Delay hover dismissal while allowing movement into the tooltip to cancel it. */
export function useDelayedHover(delay: number) {
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const cancel = useCallback(() => clearTimeout(timer.current), []);
  const schedule = useCallback((clear: () => void) => {
    timer.current = setTimeout(clear, delay);
  }, [delay]);
  useEffect(() => cancel, [cancel]);
  return { cancel, schedule };
}
