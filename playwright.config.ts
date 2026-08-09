import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the city-rating app.
 *
 * The app under test lives in ./app (a Next.js project). The webServer block
 * boots `next dev` from that directory so the harness is self-contained: from
 * the repo root, `npm run test:e2e` starts the dev server, runs the smoke
 * suite, and tears the server down.
 *
 * These tests are intended to run LOCALLY before deploying — they are not
 * wired into the CI workflow because spinning up the dev server on every PR
 * is heavier than the value the smoke check provides. See e2e/README.md.
 */
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 1 : undefined,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'cd app && npm run dev',
    url: 'http://localhost:3000',
    timeout: 60_000,
    reuseExistingServer: isCI ? false : true,
  },
});
