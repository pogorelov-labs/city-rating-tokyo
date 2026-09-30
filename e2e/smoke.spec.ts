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

  test('Bangkok district map loads with the city switcher', async ({ page }) => {
    const response = await page.goto('/bangkok');
    expect(response?.status()).toBe(200);

    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });
    // 50 district polygons live in their own Leaflet pane.
    await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
    await expect(page.getByRole('link', { name: 'Tokyo', exact: true })).toHaveAttribute('href', '/');
    await expect(page.getByRole('link', { name: 'Bangkok', exact: true })).toHaveAttribute('aria-current', 'page');
  });

  test('district detail page loads', async ({ page }) => {
    const response = await page.goto('/bangkok/district/watthana');
    expect(response?.status()).toBe(200);

    await expect(page.getByRole('heading', { name: 'Watthana', level: 1 })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Rail stations')).toBeVisible();
    await expect(page.getByText('Asok', { exact: true })).toBeVisible();
  });

  test('district map tooltips sit above the polygons', async ({ page }) => {
    await page.goto('/bangkok');
    const polygons = page.locator('.leaflet-bkk-districts-pane path.leaflet-interactive');
    await expect(polygons).toHaveCount(50, { timeout: 15_000 });
    await polygons.nth(20).hover({ force: true });
    // In the tooltip pane — inside the polygons' own pane it rendered under them.
    await expect(page.locator('.leaflet-tooltip-pane .district-tooltip')).toBeVisible({ timeout: 5_000 });
  });

  test('Bangkok levels of detail: districts → stations → 200 m grid', async ({ page }) => {
    await page.goto('/bangkok');
    await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });

    await page.getByRole('radio', { name: 'Stations' }).click();
    await expect(page).toHaveURL(/lv=station/);
    await expect(page.locator('.leaflet-bkk-areas-pane path')).toHaveCount(133, { timeout: 10_000 });
    await expect(page.getByRole('complementary').getByText('133 station areas', { exact: true })).toBeVisible();

    await page.getByRole('radio', { name: '200 m grid' }).click();
    await expect(page).toHaveURL(/lv=grid/);
    await expect(page.locator('canvas.bkk-grid-canvas')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Best spots' })).toBeVisible();
    await expect(page.locator('.grid-hotspot')).toHaveCount(5, { timeout: 10_000 });
  });

  test('a grid cell opens its popup', async ({ page }) => {
    // Fly to the Siam station area on the grid, then click the map centre.
    await page.goto('/bangkok?lv=grid&s=st.siam');
    await expect(page.locator('canvas.bkk-grid-canvas')).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1_500); // fly-to animation
    const map = page.locator('.leaflet-container');
    const box = (await map.boundingBox())!;
    // A little south-east of the station dot (a dot click selects the area).
    await page.mouse.click(box.x + box.width / 2 + 40, box.y + box.height / 2 + 60);
    await expect(page).toHaveURL(/s=cell\.\d+/, { timeout: 5_000 });
    await expect(page.locator('.leaflet-popup').getByText('Pathum Wan district →')).toBeVisible({ timeout: 5_000 });
  });

  test('station area page loads', async ({ page }) => {
    const response = await page.goto('/bangkok/station/asok');
    expect(response?.status()).toBe(200);
    await expect(page.getByRole('heading', { name: 'Asok / Sukhumvit', level: 1 })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Next stops')).toBeVisible();
    // Client-rendered radar: its legend must be real copy, not a message key.
    await expect(page.getByText('Typical Bangkok station area (median)')).toBeVisible({ timeout: 10_000 });
  });

  test('district page radar legend is translated', async ({ page }) => {
    await page.goto('/bangkok/district/watthana');
    await expect(page.getByText('Typical Bangkok district (median)')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('bangkok.district.radarMedianLabel')).toHaveCount(0);
  });

  test('switching city keeps weights but not currency-bound filters', async ({ page }) => {
    // Tokyo link with a custom weight vector and a yen rent limit.
    await page.goto('/?w=28,18,12,0,12,0,0,12,18,0&mr=150000');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('link', { name: 'Bangkok', exact: true }).click();
    await expect(page).toHaveURL(/\/bangkok\?w=28%2C18%2C12/, { timeout: 15_000 });
    expect(page.url()).not.toContain('mr=');
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
