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
const externalBaseURL = process.env.E2E_BASE_URL || process.env.PLAYWRIGHT_BASE_URL;
const production = process.env.E2E_PRODUCTION === '1';
const port = process.env.E2E_PORT || '3000';
if (!/^\d{1,5}$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
  throw new Error('E2E_PORT must be a valid TCP port');
}
const baseURL = externalBaseURL || `http://localhost:${port}`;

export default defineConfig({
  testDir: './e2e',
  testIgnore: '**/bangkok-prototype.spec.ts',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: 0,
  workers: isCI ? 1 : undefined,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // CI's headless Linux browser may not have a hardware GPU. These
        // flags exercise rendering functionality, not performance.
        launchOptions: isCI && process.platform === 'linux' ? { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } : undefined,
      },
    },
  ],
  webServer: externalBaseURL ? undefined : {
    command: production ? 'node app/.next/standalone/server.js' : `cd app && npm run dev -- --port ${port}`,
    url: baseURL,
    env: { PORT: port, HOSTNAME: 'localhost' },
    timeout: 60_000,
    reuseExistingServer: isCI ? false : true,
  },
});
