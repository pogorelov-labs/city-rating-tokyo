'use client';

import { useSyncExternalStore } from 'react';

/**
 * Detects whether the device has a coarse pointer (touch).
 * Uses `useSyncExternalStore` so the value is stable across
 * SSR (false) and hydration (actual value).
 */
const query = '(hover: none)';

function subscribe(cb: () => void) {
  const mql = window.matchMedia(query);
  mql.addEventListener('change', cb);
  return () => mql.removeEventListener('change', cb);
}

function getSnapshot() {
  return window.matchMedia(query).matches;
}

function getServerSnapshot() {
  return false;
}

export function useIsTouch() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
