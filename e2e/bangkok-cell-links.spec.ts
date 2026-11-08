import { expect, test } from '@playwright/test';

test.setTimeout(90_000);

for (const bad of ['cell.999999999999999999999999', 'cell.999999999999999', 'cell.1e3', 'cell.', 'cell.0']) {
  test(`invalid selection ${bad} is removed without damaging other map state`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`/bangkok?lv=station&s=${bad}&c=cell.0,st.asok,cell.39725&adult=1&flood=1&w=30,18,14,10,12,8,4,4,8,4`);
    await expect(page.getByLabel('Map renderer')).toHaveValue('maplibre', { timeout: 30_000 });
    await expect(page.getByTestId('maplibre-map')).toBeVisible();
    await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 30_000 }).toBeNull();
    await expect.poll(() => new URL(page.url()).searchParams.get('c'), { timeout: 30_000 }).toBe('st.asok,cell.39725');
    const params = new URL(page.url()).searchParams;
    expect(params.get('adult')).toBe('1');
    expect(params.get('flood')).toBe('1');
    expect(params.get('w')).toBe('30,18,14,10,12,8,4,4,8,4');
    expect(params.get('lv')).toBe('station');
    await expect(page.getByRole('status').filter({ hasText: /3D map.*unavailable|3D map could not load/i })).toHaveCount(0);
    expect(errors).toEqual([]);
    // The same retained state remains usable on the standard renderer.
    await page.getByLabel('Map renderer').selectOption('leaflet');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 30_000 });
    expect(new URL(page.url()).searchParams.get('c')).toBe('st.asok,cell.39725');
  });
}

test('a valid cell remains selected while its grid mask is loading', async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let requested!: () => void;
  const requestedGrid = new Promise<void>(resolve => { requested = resolve; });
  await page.route('**/data/bangkok/grid-*.bin', async route => {
    requested();
    await gate;
    await route.continue();
  });
  try {
    await page.goto('/bangkok?lv=grid&s=cell.39725&adult=1');
    await requestedGrid;
    await expect(page.getByLabel('Map renderer')).toBeVisible({ timeout: 30_000 });
    expect(new URL(page.url()).searchParams.get('s')).toBe('cell.39725');
    release();
    await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible({ timeout: 30_000 });
    expect(new URL(page.url()).searchParams.get('s')).toBe('cell.39725');
    expect(new URL(page.url()).searchParams.get('adult')).toBe('1');
  } finally {
    release();
    await page.unrouteAll({ behavior: 'wait' });
  }
});

test('an invalid masked cell leaves phone controls reachable', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    await page.goto('/bangkok?lv=grid&s=cell.0&adult=1');
    await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
    await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 30_000 }).toBeNull();
    await expect(page.getByRole('button', { name: 'Close cell card' })).toHaveCount(0);
    await expect(page.getByLabel('Map renderer')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Filters', exact: true }).tap();
    await expect(page.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  } finally { await context.close(); }
});

test('a compare-only cell loads on the district level and remains visible in the standard map', async ({ page }) => {
  const gridResponse = page.waitForResponse(response => /\/data\/bangkok\/grid-[^/]+\.bin/.test(response.url()) && response.ok(), { timeout: 30_000 });
  await page.goto('/bangkok?c=cell.39725');
  await gridResponse;
  await expect(page.getByTestId('maplibre-map')).toBeVisible({ timeout: 30_000 });
  expect(new URL(page.url()).searchParams.get('c')).toBe('cell.39725');
  await page.getByLabel('Map renderer').selectOption('leaflet');
  await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('path.bangkok-cell-compared')).toHaveCount(1, { timeout: 30_000 });
  expect(new URL(page.url()).searchParams.get('c')).toBe('cell.39725');
});

test('an invalid-only selection is removed from both address and share link', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/bangkok?s=cell.0&adult=1');
  await expect.poll(() => new URL(page.url()).searchParams.has('s'), { timeout: 30_000 }).toBe(false);
  await page.getByRole('button', { name: 'Share', exact: true }).click();
  await expect(page.getByText('Copied!', { exact: true })).toBeVisible();
  const shared = new URL(await page.evaluate(() => navigator.clipboard.readText()));
  expect(shared.searchParams.has('s')).toBe(false);
  expect(shared.searchParams.get('adult')).toBe('1');
});

test('a valid selected cell and valid comparisons survive a masked comparison', async ({ page }) => {
  await page.goto('/bangkok?lv=grid&s=cell.39725&c=cell.0,watthana,cell.41873&flood=1');
  await expect.poll(() => new URL(page.url()).searchParams.get('c'), { timeout: 30_000 }).toBe('watthana,cell.41873');
  await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible({ timeout: 30_000 });
  const params = new URL(page.url()).searchParams;
  expect(params.get('s')).toBe('cell.39725');
  expect(params.get('flood')).toBe('1');
});

test('a failed grid download leaves a plausible selected cell and phone controls available', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    await page.route('**/data/bangkok/grid-*.bin', route => route.fulfill({ status: 503, body: 'unavailable' }));
    const failed = page.waitForResponse(response => /\/data\/bangkok\/grid-.*\.bin/.test(response.url()) && response.status() === 503);
    await page.goto('/bangkok?lv=grid&s=cell.39725&adult=1');
    await failed;
    await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
    await expect(page.getByLabel('Map renderer')).toHaveValue('maplibre', { timeout: 30_000 });
    await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Close cell card' })).toHaveCount(0);
    expect(new URL(page.url()).searchParams.get('s')).toBe('cell.39725');
    expect(new URL(page.url()).searchParams.get('adult')).toBe('1');
  } finally { await context.close(); }
});
