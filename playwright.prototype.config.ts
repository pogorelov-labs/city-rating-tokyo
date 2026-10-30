import { defineConfig, devices } from '@playwright/test';
const port = process.env.E2E_PORT || '3170';
const baseURL = process.env.E2E_BASE_URL || `http://localhost:${port}`;
export default defineConfig({
  testDir: './e2e', testMatch: 'bangkok-prototype.spec.ts', workers: 1, retries: 0,
  timeout: 60_000, reporter: 'list',
  use: {
    baseURL, ...devices['Desktop Chrome'], screenshot: 'only-on-failure',
    launchOptions: process.env.CI && process.platform === 'linux'
      ? { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } : undefined,
  },
  webServer: process.env.E2E_BASE_URL ? undefined : { command: `cd app && BANGKOK_RENDERER_LAB=1 npm run dev -- --port ${port}`,
    url: `${baseURL}/bangkok/prototype/leaflet`, reuseExistingServer: !process.env.CI, timeout: 60_000 },
});
