import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Node ≥22 declares a global `localStorage` that is inert without
// --localstorage-file. On new node versions it shadows jsdom's working
// storage inside vitest, so suites that touch storage see a broken or
// missing surface. Back the jsdom window with a minimal in-memory
// implementation when the real one is absent (tests keep using
// window.localStorage; production code always does).
declare global {
  // eslint-disable-next-line no-var
  var localStorage: Storage | undefined;
}
if (typeof window !== 'undefined' && !window.localStorage?.getItem) {
  const store = new Map<string, string>();
  const shim = {
    getItem: (k: string) => (store.has(k) ? (store.get(k) as string) : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
    key: (i: number) => [...store.keys()][i] ?? null,
    get length() {
      return store.size;
    },
  };
  Object.defineProperty(window, 'localStorage', { value: shim, configurable: true });
  try {
    // Node's global localStorage is getter-only; best effort for bare references.
    Object.defineProperty(globalThis, 'localStorage', { value: shim, configurable: true });
  } catch {
    /* tests use window.localStorage */
  }
}

// Vitest globals stay disabled. Explicit cleanup also applies to suites that
// use fake timers; each suite restores its own timers and browser mocks.
afterEach(cleanup);
