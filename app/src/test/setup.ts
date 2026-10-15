import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Vitest globals stay disabled. Explicit cleanup also applies to suites that
// use fake timers; each suite restores its own timers and browser mocks.
afterEach(cleanup);
