import { test, expect } from '@playwright/test';

/**
 * Smoke tests for the city-rating app.
 *
 * Goal: catch gross regressions in the core flows (homepage map, station
 * detail, methodology, locale switching) before they ship. We assert HTTP 200
 * plus one piece of expected content per page — no visual regression and no
 * perf capture here (those live in the flyto-visual-test and perf-capture
 * skills, which are heavier).
 *
 * The dev server is brought up automatically by the webServer config in
 * playwright.config.ts; from the repo root just run `npm run test:e2e`.
 */

test.describe('smoke', () => {
  test('homepage loads and the map renders', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);

    // The Leaflet map mounts a .leaflet-container; the underlying <canvas> may
    // be deferred, so wait for the container as the stable signal.
    await expect(page.locator('.leaflet-container')).toBeVisible({
      timeout: 15_000,
    });
  });

  test('station detail page loads', async ({ page }) => {
    const response = await page.goto('/station/shibuya');
    expect(response?.status()).toBe(200);

    // The station display name renders in a bold header span. Shibuya is one
    // of the canonical stations and always has full data.
    await expect(page.getByText('Shibuya', { exact: true })).toBeVisible({
      timeout: 10_000,
    });
  });

  test('methodology page loads', async ({ page }) => {
    const response = await page.goto('/methodology');
    expect(response?.status()).toBe(200);

    await expect(
      page.getByRole('heading', { name: 'Methodology', exact: true })
    ).toBeVisible({ timeout: 10_000 });
  });

  test('Japanese locale page loads', async ({ page }) => {
    const response = await page.goto('/ja');
    expect(response?.status()).toBe(200);

    // The JA homepage header renders the long-form title 東京エリアガイド
    // (Tokyo Area Guide). This confirms locale routing + message loading.
    await expect(page.getByText('東京エリアガイド')).toBeVisible({
      timeout: 10_000,
    });
  });
});
