import { expect, test } from '@playwright/test';
import en from '../app/src/messages/en/common.json';
import ja from '../app/src/messages/ja/common.json';
import ru from '../app/src/messages/ru/common.json';

// These exercise the public production route, with no lab instrumentation.
test.setTimeout(90_000);
const locales = [ ['en', '', en], ['ja', '/ja', ja], ['ru', '/ru', ru] ] as const;

for (const [locale, prefix, messages] of locales) {
  test(`${locale}: default 3D map and localized controls`, async ({ page }) => {
    await page.goto(`${prefix}/bangkok?s=pathum-wan&profile=1`);
    const renderer = page.getByLabel(messages.map.rendererLabel);
    await expect(renderer).toHaveValue('maplibre');
    await expect(page.getByTestId('maplibre-map')).toBeVisible();
    await expect(page.getByRole('region', { name: messages.map.selectedArea })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('button', { name: messages.map.view2d })).toBeVisible();
    expect(await page.evaluate(() => ['__bangkokRenderer', '__bangkokProfile', '__bangkokGridPaint'].map((key) => key in window))).toEqual([false, false, false]);
    await renderer.selectOption('leaflet');
    await expect(page.locator('.leaflet-container')).toBeVisible();
    expect(new URL(page.url()).searchParams.get('s')).toBe('pathum-wan');
    await renderer.selectOption('maplibre');
    await expect(page.getByRole('region', { name: messages.map.selectedArea })).toBeVisible({ timeout: 30_000 });
    expect(new URL(page.url()).searchParams.get('s')).toBe('pathum-wan');
  });
}

test('map pointer selects districts, station areas and grid cells', async ({ page }) => {
  for (const [query, key] of [['', /.+/], ['?lv=station', /^st\./], ['?lv=grid', /^cell\.\d+$/]] as const) {
    await page.goto(`/bangkok${query}`);
    const map = page.getByTestId('maplibre-map');
    await expect(map).toBeVisible();
    await expect(page.getByText(en.loading.map, { exact: true })).toBeHidden({ timeout: 30_000 });
    await page.getByRole('button', { name: '2D view' }).click();
    await expect(page.getByRole('button', { name: '3D view' })).toBeVisible();
    const box = await map.boundingBox();
    expect(box).not.toBeNull();
    // The initial center is Asok station. Offset the grid click so the
    // station marker does not take precedence over the cell underneath.
    const offset = query === '?lv=grid' ? 35 : 0;
    await page.mouse.click(box!.x + box!.width / 2 + offset, box!.y + box!.height / 2 + offset);
    await expect.poll(() => new URL(page.url()).searchParams.get('s')).toMatch(key);
    await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible();
  }
});

test('selection, comparison and details work across Bangkok levels', async ({ page }) => {
  for (const [query, path] of [
    ['s=pathum-wan', /\/bangkok\/district\//],
    ['lv=station&s=st.asok', /\/bangkok\/station\//],
  ] as const) {
    await page.goto(`/bangkok?${query}`);
    const card = page.getByRole('region', { name: 'Selected area' });
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.getByRole('button', { name: '+ Compare', exact: true }).click();
    await expect(card.getByRole('button', { name: /Remove/ })).toBeVisible();
    const link = card.getByRole('link', { name: en.areaGuide.compact.explore, exact: true });
    await expect(link).toHaveAttribute('href', path);
    await link.click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  }
  await page.goto('/bangkok?lv=grid&s=cell.41873');
  await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible({ timeout: 30_000 });
  expect(new URL(page.url()).searchParams.get('s')).toBe('cell.41873');
  await page.keyboard.press('Escape');
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
});

test('grid filters and weights survive a copied share link', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/bangkok?lv=grid&w=30,18,14,10,12,8,4,4,8,4');
  await expect(page.getByTestId('maplibre-map')).toBeVisible();
  const sidebar = page.locator('aside');
  await sidebar.getByRole('checkbox', { name: /Family-friendly/ }).check();
  await sidebar.getByRole('checkbox', { name: /Hide flood-risk/ }).check();
  await expect(sidebar.getByText(/of 39,149 cells match/)).toBeVisible();
  await page.getByRole('button', { name: 'Share', exact: true }).click();
  await expect(page.getByText('Copied!', { exact: true })).toBeVisible();
  const shared = await page.evaluate(() => navigator.clipboard.readText());
  const params = new URL(shared).searchParams;
  expect(params.get('lv')).toBe('grid');
  expect(params.get('w')).toBe('30,18,14,10,12,8,4,4,8,4');
  expect(params.get('adult')).toBe('1');
  expect(params.get('flood')).toBe('1');
  await page.goto(shared);
  await expect(sidebar.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: /Hide flood-risk/ })).toBeChecked();
});

test('wheel and keyboard controls retain selected area', async ({ page }) => {
  await page.goto('/bangkok?s=pathum-wan');
  const map = page.getByTestId('maplibre-map');
  await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(en.loading.map, { exact: true })).toBeHidden({ timeout: 30_000 });
  await expect(page.getByRole('button', { name: '2D view' })).toBeEnabled({ timeout: 30_000 });
  await page.getByRole('button', { name: '2D view' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: '3D view' })).toBeVisible();
  await map.hover();
  await page.mouse.wheel(0, -400);
  await page.keyboard.press('Escape');
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
});

test('touch controls retain a selected area', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    await page.goto('/bangkok?lv=station&s=st.asok');
    await expect(page.getByRole('button', { name: 'Close station card' })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeHidden();
    await page.getByRole('button', { name: 'Zoom in' }).tap();
    expect(new URL(page.url()).searchParams.get('s')).toBe('st.asok');
    await page.getByRole('button', { name: 'Close station card' }).tap();
    await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
    await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeVisible();
  } finally { await context.close(); }
});

for (const failure of ['webgl', 'style'] as const) {
  test(`${failure} failure falls back and keeps state`, async ({ page }) => {
    if (failure === 'webgl') await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type: string, ...args: unknown[]) {
        if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') return null;
        return original.apply(this, [type, ...args] as Parameters<typeof original>);
      } as typeof original;
    });
    else await page.route('https://tiles.openfreemap.org/styles/positron', (route) => route.abort());
    await page.goto('/bangkok?lv=station&s=st.asok&adult=1&w=30,18,14,10,12,8,4,4,8,4');
    const renderer = page.getByLabel('Map renderer');
    await expect(renderer).toHaveValue('leaflet', { timeout: 30_000 });
    await expect(page.locator('.leaflet-container')).toBeVisible();
    const message = failure === 'webgl' ? en.map.rendererUnavailableWebgl : en.map.rendererUnavailableLoad;
    await expect(page.locator('summary[aria-label]').filter({ hasText: '!' })).toHaveAttribute('aria-label', message);
    const params = new URL(page.url()).searchParams;
    expect(params.get('lv')).toBe('station');
    expect(params.get('s')).toBe('st.asok');
    expect(params.get('adult')).toBe('1');
    expect(params.get('w')).toBe('30,18,14,10,12,8,4,4,8,4');
    if (failure === 'style') {
      await page.unroute('https://tiles.openfreemap.org/styles/positron');
      await renderer.selectOption('maplibre');
      await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible({ timeout: 30_000 });
    }
  });
}

test('lab routes are excluded from a normal build and sitemap', async ({ page, request }) => {
  const response = await page.goto('/bangkok/prototype/maplibre');
  expect(response?.status()).toBe(404);
  const sitemap = await request.get('/sitemap.xml');
  expect(sitemap.ok()).toBe(true);
  const index = await sitemap.text();
  expect(index).not.toContain('/bangkok/prototype');
  for (const loc of index.matchAll(/<loc>([^<]+)<\/loc>/g)) {
    const child = await request.get(new URL(loc[1]).pathname);
    expect(child.ok()).toBe(true);
    expect(await child.text()).not.toContain('/bangkok/prototype');
  }
});


test('production worker and document security policies support Bangkok rendering', async ({ request }) => {
  test.skip(!process.env.CI && process.env.E2E_PRODUCTION !== '1', 'Run against a production build');
  const worker = await request.get('/map-assets/maplibre-gl-worker-6.16.0.mjs');
  expect(worker.status()).toBe(200);
  expect(worker.headers()['content-type']).toMatch(/(?:javascript|ecmascript)/i);
  expect(worker.headers()['cache-control']).toMatch(/immutable/i);
  const bangkok = await request.get('/bangkok');
  const tokyo = await request.get('/');
  expect(bangkok.ok()).toBe(true);
  expect(tokyo.ok()).toBe(true);
  for (const response of [worker, bangkok]) {
    const csp = response.headers()['content-security-policy'];
    expect(csp).toBeTruthy();
    expect(csp).not.toContain("'unsafe-eval'");
    expect(csp.match(/(?:^|;)\s*connect-src\s+[^;]*/)?.[0]).toContain('https://tiles.openfreemap.org');
  }
  const tokyoPolicy = tokyo.headers()['content-security-policy'];
  expect(tokyoPolicy).toBeTruthy();
  expect(tokyoPolicy).not.toContain("'unsafe-eval'");
  expect(tokyoPolicy.match(/(?:^|;)\s*connect-src\s+[^;]*/)?.[0]).toContain('https://tiles.openfreemap.org');
});

test('Tokyo to Bangkok client navigation loads the 3D map without CSP violations', async ({ page }) => {
  const providerRequests: string[] = [];
  page.on('request', (request) => { if (new URL(request.url()).hostname === 'tiles.openfreemap.org') providerRequests.push(request.url()); });
  await page.addInitScript(() => {
    const state = window as typeof window & { __cspViolations: string[] };
    state.__cspViolations = [];
    document.addEventListener('securitypolicyviolation', (event) => state.__cspViolations.push(event.violatedDirective));
  });
  await page.goto('/?w=30,18,14,10,12,8,4,4,8,4');
  await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 30_000 });
  expect(providerRequests).toEqual([]);
  await page.getByRole('link', { name: 'Bangkok', exact: true }).click();
  await expect(page).toHaveURL(/\/bangkok/);
  await expect(page.getByLabel('Map renderer')).toHaveValue('maplibre');
  await expect(page.getByTestId('maplibre-map')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(en.loading.map, { exact: true })).toBeHidden({ timeout: 30_000 });
  await expect(page.getByRole('button', { name: '2D view' })).toBeEnabled({ timeout: 30_000 });
  expect(providerRequests.length).toBeGreaterThan(0);
  expect(await page.evaluate(() => (window as typeof window & { __cspViolations: string[] }).__cspViolations)).toEqual([]);
  expect(new URL(page.url()).searchParams.get('w')).toBe('30,18,14,10,12,8,4,4,8,4');
});

test('touch tablet shows selected station and grid cards', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 820, height: 900 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    for (const [query, selected] of [['lv=station&s=st.asok', 'st.asok'], ['lv=grid&s=cell.41873', 'cell.41873']] as const) {
      await page.goto(`/bangkok?${query}`);
      await expect(page.getByTestId('maplibre-map')).toBeVisible();
      await expect(page.getByText(en.loading.map, { exact: true })).toBeHidden({ timeout: 30_000 });
      await expect.poll(async () =>
        (await page.getByRole('dialog').isVisible()) || (await page.getByRole('region', { name: 'Selected area' }).isVisible()),
        { timeout: 15_000 }).toBe(true);
      expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
    }
  } finally { await context.close(); }
});

test('phone fallback notice leaves the heatmap selector usable', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type: string, ...args: unknown[]) {
        if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') return null;
        return original.apply(this, [type, ...args] as Parameters<typeof original>);
      } as typeof original;
    });
    await page.goto('/bangkok?s=pathum-wan');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Map layers', exact: true }).tap();
    await page.getByRole('button', { name: 'Heatmap', exact: true }).tap();
    const notice = page.locator('summary[aria-label]').filter({ hasText: '!' });
    const selector = page.getByRole('combobox', { name: 'Heatmap' });
    await expect(notice).toBeVisible();
    await expect(selector).toBeVisible();
    const a = await notice.boundingBox(), b = await selector.boundingBox();
    expect(a).not.toBeNull(); expect(b).not.toBeNull();
    expect(a!.x + a!.width <= b!.x || b!.x + b!.width <= a!.x ||
      a!.y + a!.height <= b!.y || b!.y + b!.height <= a!.y).toBe(true);
    const zoom = page.getByRole('button', { name: 'Zoom in' });
    const z = await zoom.boundingBox();
    expect(z).not.toBeNull();
    expect(z!.x + z!.width <= b!.x || b!.x + b!.width <= z!.x ||
      z!.y + z!.height <= b!.y || b!.y + b!.height <= z!.y).toBe(true);
    await selector.selectOption({ index: 1 });
    await zoom.tap({ timeout: 8_000 });
    await notice.tap();
    await expect(page.locator('details[open]').getByText(en.map.rendererUnavailableWebgl)).toBeVisible();
  } finally { await context.close(); }
});

test('short phone keeps 3D controls and selected card usable with air panel expanded', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  try {
    await page.goto('/bangkok?lv=station&s=st.asok');
    const close = page.getByRole('button', { name: 'Close station card' });
    await expect(close).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(en.loading.map, { exact: true })).toBeHidden({ timeout: 30_000 });
    await page.locator('summary').filter({ hasText: 'Bangkok: air and seasons' }).tap();
    const menu = page.getByRole('button', { name: '3D map controls' });
    await expect(menu).toBeEnabled({ timeout: 30_000 });
    await menu.tap({ timeout: 8_000 });
    await expect(menu).toHaveAttribute('aria-expanded', 'true');
    const layers = page.getByRole('button', { name: 'Map layers' });
    await layers.tap({ timeout: 8_000 });
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await expect(layers).toHaveAttribute('aria-expanded', 'true');
    await menu.focus();
    await expect(layers).toHaveAttribute('aria-expanded', 'false');
    await page.keyboard.press('Enter');
    await expect(menu).toHaveAttribute('aria-expanded', 'true');
    await page.keyboard.press('Escape');
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await menu.tap();
    await page.getByRole('button', { name: '2D view' }).tap({ timeout: 8_000 });
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await page.getByRole('button', { name: 'Zoom in' }).tap({ timeout: 8_000 });
    const attribution = page.locator('.maplibregl-ctrl-attrib-button');
    await expect(attribution).toHaveAttribute('aria-label', 'Map attribution');
    const attributionLink = page.getByRole('link', { name: 'OpenFreeMap' });
    if (!(await attributionLink.isVisible())) await attribution.tap({ timeout: 8_000 });
    await expect(attributionLink).toBeVisible();
    await attribution.tap({ timeout: 8_000 });
    await expect(attributionLink).toBeHidden();
    expect(new URL(page.url()).searchParams.get('s')).toBe('st.asok');
    const card = page.getByRole('dialog');
    await card.getByRole('button', { name: '+ Compare', exact: true }).tap({ timeout: 8_000 });
    await expect(card.getByRole('button', { name: /Remove compare/ })).toBeVisible();
    await close.tap({ timeout: 8_000 });
    await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
  } finally { await context.close(); }
});

test('station guide returns to its map target with current weights and map settings', async ({ page }) => {
  const weights = '30,18,14,10,12,8,4,4,8,4';
  await page.goto(`/bangkok?lv=station&s=st.asok&c=st.nana&adult=1&flood=1&mr=25000&hm=1&hd=food&w=${weights}`);
  const card = page.getByRole('region', { name: en.map.selectedArea });
  await expect(card).toBeVisible({ timeout: 30_000 });
  const sidebar = page.locator('aside');
  await expect(sidebar.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: /Hide flood-risk/ })).toBeChecked();
  await expect(page.getByRole('combobox', { name: en.map.heatmap })).toHaveValue('food');
  await card.getByRole('link', { name: en.areaGuide.compact.explore, exact: true }).click();
  await expect(page).toHaveURL(/\/bangkok\/station\/asok/);
  await expect.poll(() => new URL(page.url()).searchParams.get('w')).toBe(weights);
  await page.getByRole('combobox', { name: en.areaGuide.score.priorities }).selectOption('family');
  await expect.poll(() => new URL(page.url()).searchParams.get('w')).not.toBe(weights);
  const changedWeights = new URL(page.url()).searchParams.get('w');
  expect(changedWeights).toBeTruthy();
  await page.locator('[data-umami-event="back-to-map"]').click();
  await expect(page).toHaveURL(/\/bangkok\?/);
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBe('st.asok');
  const params = new URL(page.url()).searchParams;
  expect(Object.fromEntries(['lv', 's', 'c', 'adult', 'flood', 'mr', 'hm', 'hd', 'w'].map(key => [key, params.get(key)]))).toEqual({
    lv: 'station', s: 'st.asok', c: 'st.nana', adult: '1', flood: '1', mr: '25000', hm: '1', hd: 'food', w: changedWeights,
  });
  await expect(sidebar.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: /Hide flood-risk/ })).toBeChecked();
  await expect(page.getByRole('combobox', { name: en.map.heatmap })).toHaveValue('food');
  await expect(page.getByRole('region', { name: en.map.selectedArea })).toBeVisible();
});

test('grid-cell district and station guide links carry weights and return to the guide target', async ({ page }) => {
  const weights = '30,18,14,10,12,8,4,4,8,4';
  // This cell is in Watthana and the Asok station area.
  for (const [event, detail, target, level] of [
    ['cell-district', '/bangkok/district/watthana', 'watthana', null],
    ['cell-station-area', '/bangkok/station/asok', 'st.asok', 'station'],
  ] as const) {
    await page.goto(`/bangkok?lv=grid&s=cell.39725&adult=1&w=${weights}`);
    const card = page.getByRole('region', { name: en.map.selectedArea });
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.locator(`[data-umami-event="${event}"]`).click();
    await expect.poll(() => new URL(page.url()).pathname).toBe(detail);
    await expect.poll(() => new URL(page.url()).searchParams.get('w')).toBe(weights);
    await page.locator('[data-umami-event="back-to-map"]').click();
    await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBe(target);
    const params = new URL(page.url()).searchParams;
    expect(params.get('lv')).toBe(level);
    expect(params.get('adult')).toBe('1');
    expect(params.get('w')).toBe(weights);
  }
});
