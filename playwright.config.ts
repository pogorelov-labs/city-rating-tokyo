import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the city-rating app.
 *
 * The app under test lives in ./app (a Next.js project). The webServer block
 * boots `next dev` from that directory so the harness is self-contained: from
 * the repo root, `npm run test:e2e` starts the dev server, runs the smoke
 * suite, and tears the server down.
 *
 * The map interaction spec also runs in CI. See e2e/README.md.
 */
const isCI = !!process.env.CI;
const releaseBaseURL = process.env.PLAYWRIGHT_BASE_URL;
const production = process.env.E2E_PRODUCTION === '1';
const port = process.env.E2E_PORT || '3000';
if (!/^\d{1,5}$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
  throw new Error('E2E_PORT must be a valid TCP port');
}
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 1 : undefined,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: releaseBaseURL ?? baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: releaseBaseURL ? undefined : {
    command: production ? 'node app/.next/standalone/server.js' : `cd app && npm run dev -- --port ${port}`,
    url: baseURL,
    env: { PORT: port, HOSTNAME: 'localhost' },
    timeout: 60_000,
    reuseExistingServer: isCI ? false : true,
  },
});
