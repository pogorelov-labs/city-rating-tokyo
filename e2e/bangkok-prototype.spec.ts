import { test, expect } from '@playwright/test';
import { resolve } from 'node:path';
import header from '../app/src/data/bangkok/grid.json';

test('MapLibre draws buildings and grid while preserving filters and copied state', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/bangkok/prototype/maplibre?lv=grid');
  await expect(page.locator('aside').getByText('39,149 cells', { exact: true })).toBeVisible();
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), { timeout: 30_000 });
  const stats = await page.evaluate(() => window.__bangkokRenderer!.stats());
  expect(stats.buildingFeatures).toBeGreaterThan(0);
  expect(stats.gridUploads).toBeGreaterThan(0);
  await page.addScriptTag({ path: resolve('app/node_modules/axe-core/axe.min.js') });
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context: object, options: object) => Promise<{ violations: { id: string }[] }> } }).axe;
    return (await axe.run({ include: ['.bangkok-maplibre', 'nav[aria-label="Renderer comparison"]', '[aria-label="3D map controls"]'] },
      { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } })).violations.map((v) => v.id);
  });
  expect(violations).toEqual([]);
  const family = page.locator('aside').getByRole('checkbox', { name: /Family-friendly/ });
  await family.check();
  await expect(page.locator('aside').getByText(/39,112 of 39,149 cells match/)).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__bangkokRenderer!.stats().gridUploads)).toBeGreaterThan(Number(stats.gridUploads));
  await page.locator('aside').getByRole('checkbox', { name: /Hide flood-risk/ }).check();
  await page.getByRole('button', { name: 'Share', exact: true }).click();
  await expect(page.getByText('Copied!', { exact: true })).toBeVisible();
  const url = await page.evaluate(() => navigator.clipboard.readText());
  expect(new URL(url).pathname).toBe('/bangkok/prototype/maplibre');
  expect(new URL(url).searchParams.get('adult')).toBe('1');
  expect(new URL(url).searchParams.get('flood')).toBe('1');
  await page.goto(url);
  await expect(family).toBeChecked();
  await expect(page.locator('aside').getByRole('checkbox', { name: /Hide flood-risk/ })).toBeChecked();
  expect(errors).toEqual([]);
});

test('renderer switch keeps state and cell details agree', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&s=cell.41873&w=30,18,14,10,12,8,4,4,8,4');
  const mapCard = page.getByRole('region', { name: 'Selected area' });
  await expect(mapCard).toBeVisible({ timeout: 30_000 });
  const score = await mapCard.locator('.text-lg.font-bold').textContent();
  await page.getByRole('button', { name: 'Leaflet 2D', exact: true }).click();
  await expect(page).toHaveURL(/prototype\/leaflet\?.*s=cell.41873/);
  await expect(page.locator('.leaflet-popup')).toBeVisible({ timeout: 30_000 });
  expect(await page.locator('.leaflet-popup .text-lg.font-bold').textContent()).toBe(score);
});

test('phone can explore buildings, select and restore grid filters', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto('/bangkok/prototype/maplibre?lv=grid&adult=1');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page.getByTestId('maplibre-map')).toBeVisible();
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.getByRole('button', { name: 'Filters', exact: true }).tap();
  await expect(page.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await page.goto('/bangkok/prototype/maplibre?lv=station&s=st.asok');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page.getByRole('button', { name: 'Close station card' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeHidden();
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.getByRole('button', { name: 'Close station card' }).tap();
  await expect(page.getByRole('button', { name: 'Filters', exact: true })).toBeVisible();
  await context.close();
});

test('grid picking agrees with geographic cells at multiple pitches and survives context restoration', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 30_000 });
  const col = Math.floor((100.566 - header.west) / (header.east - header.west) * header.nx);
  const row = Math.floor((header.north - 13.739) / (header.north - header.south) * header.ny);
  const lng = header.west + (col + .5) / header.nx * (header.east - header.west);
  const lat = header.north - (row + .5) / header.ny * (header.north - header.south);
  for (const pitch of [0, 30, 50]) {
    await page.keyboard.press('Escape');
    await page.evaluate((c) => window.__bangkokRenderer!.setCamera(c), { lng, lat, zoom: 18, pitch, bearing: 0 });
    await page.waitForFunction(() => window.__bangkokRenderer!.ready());
    const point = await page.evaluate(([lng, lat]) => window.__bangkokRenderer!.project(lng, lat), [lng, lat]);
    const box = await page.getByTestId('maplibre-map').boundingBox();
    await page.mouse.click(box!.x + point.x, box!.y + point.y);
    await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBe(`cell.${row * header.nx + col}`);
  }
  const before = await page.evaluate(() => window.__bangkokRenderer!.stats().gridUploads);
  const supported = await page.evaluate(() => {
    const canvas = document.querySelector('.maplibregl-canvas') as HTMLCanvasElement;
    const ext = canvas.getContext('webgl2')?.getExtension('WEBGL_lose_context');
    if (!ext) return false;
    ext.loseContext(); setTimeout(() => ext.restoreContext(), 150); return true;
  });
  expect(supported).toBe(true);
  await expect.poll(() => page.evaluate(() => window.__bangkokRenderer!.stats().gridUploads), { timeout: 15_000 }).toBeGreaterThan(Number(before));
});

test('weight, camera and visibility changes avoid unrelated renderer work', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&profile=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.waitForTimeout(250);
  await page.evaluate(() => window.__bangkokProfile!.reset());
  for (const value of ['25', '12', '30']) {
    const version = await page.evaluate((value) => {
      const input = document.querySelector('aside input[aria-label="Weights: Food & Dining"]')!;
      const before = window.__bangkokGridPaint!.version;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true })); return before;
    }, value);
    await page.waitForFunction((before) => window.__bangkokGridPaint!.version > before, version);
  }
  const weights = await page.evaluate(() => window.__bangkokProfile!.snapshot().stages);
  expect(weights['source.bkk-labels.submit']).toBeUndefined();
  expect(weights['areas.sync']).toBeUndefined();
  // Deferred updates may coalesce intermediate values; require relevant work
  // without requiring a render for every input.
  expect(weights['grid.hotspots'].calls).toBeGreaterThan(0);
  expect(weights['grid.colors'].calls).toBeGreaterThan(0);
  const before = await page.evaluate(() => window.__bangkokRenderer!.stats().gridUploads);
  await page.evaluate(() => window.__bangkokProfile!.reset());
  for (const name of ['Buildings', 'Rail', 'Rail', 'Buildings']) await page.getByRole('button', { name, exact: true }).click();
  await page.evaluate(() => window.__bangkokRenderer!.setCamera({ lng: 100.571, lat: 13.735, zoom: 17, pitch: 45 }, 300));
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  const after = await page.evaluate(() => ({ stages: window.__bangkokProfile!.snapshot().stages, stats: window.__bangkokRenderer!.stats() }));
  expect(after.stats.gridUploads).toBe(before);
  expect(after.stats.errors).toBe(0);
  for (const name of ['source.bkk-labels.submit', 'areas.sync', 'grid.score', 'grid.colors']) expect(after.stages[name]).toBeUndefined();
});

test('wheel zoom and view controls preserve the grid without repainting its texture', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&adult=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  expect(await page.evaluate(() => window.__bangkokProfile)).toBeUndefined();
  const before = await page.evaluate(() => ({ camera: window.__bangkokRenderer!.getCamera(), stats: window.__bangkokRenderer!.stats() }));
  const box = await page.getByTestId('maplibre-map').boundingBox();
  await page.mouse.move(box!.x + box!.width * .6, box!.y + box!.height * .4);
  await page.mouse.wheel(0, -400);
  await page.waitForFunction((zoom) => window.__bangkokRenderer!.getCamera().zoom > zoom + .3 && window.__bangkokRenderer!.ready(), before.camera.zoom);
  await page.getByRole('button', { name: '2D view', exact: true }).click();
  await page.waitForFunction(() => window.__bangkokRenderer!.getCamera().pitch === 0 && window.__bangkokRenderer!.ready());
  await page.getByRole('button', { name: '3D view', exact: true }).click();
  await page.waitForFunction(() => window.__bangkokRenderer!.getCamera().pitch === 50 && window.__bangkokRenderer!.ready());
  expect(await page.evaluate(() => window.__bangkokRenderer!.stats().gridUploads)).toBe(before.stats.gridUploads);
  await expect(page.locator('aside').getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
});

test('named selection, comparison and station focus use static geometry and restore after context loss', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=station&s=st.asok&profile=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  const inspect = () => page.evaluate(() => window.__bangkokRenderer!.inspectArea!('st.asok'));
  expect((await inspect()).area.selected).toBe(true);
  expect((await inspect()).stations.every((s) => s.selected === true)).toBe(true);
  const drawn = await inspect();
  expect(typeof drawn.area.color).toBe('string');
  expect(drawn.rendered.length).toBeGreaterThan(0);
  expect(drawn.rendered.every((f) => f.id === 'st.asok' && f.state.selected === true && f.state.color === drawn.area.color)).toBe(true);
  expect(drawn.renderedStations.length).toBeGreaterThan(0);
  expect(drawn.renderedStations.every((f) => ['asok', 'sukhumvit'].includes(String(f.id)) && f.state.selected === true)).toBe(true);
  expect(drawn.renderedFocus.length).toBeGreaterThan(0);
  expect(drawn.renderedFocus.every((f) => f.id === 'st.asok' && f.state.selected === true)).toBe(true);
  await page.evaluate(() => window.__bangkokProfile!.reset());
  await page.getByRole('region', { name: 'Selected area' }).getByRole('button', { name: '+ Compare', exact: true }).click();
  await page.getByRole('button', { name: 'Close area card' }).click();
  await expect.poll(async () => (await inspect()).area.selected).toBe(false);
  expect((await inspect()).area.compared).toBe(true);
  expect((await inspect()).stations.every((s) => s.compared === true)).toBe(true);
  expect(await page.evaluate(() => window.__bangkokRenderer!.inspectCartography!().focusVisible)).toBe(true);
  const stages = await page.evaluate(() => window.__bangkokProfile!.snapshot().stages);
  expect(stages['source.bkk-selected.submit']).toBeUndefined();
  expect(stages['source.bkk-labels.submit']).toBeUndefined();
  await page.evaluate(() => {
    const gl = document.querySelector<HTMLCanvasElement>('.maplibregl-canvas')!.getContext('webgl2')!;
    const ext = gl.getExtension('WEBGL_lose_context')!;
    ext.loseContext(); setTimeout(() => ext.restoreContext(), 150);
  });
  await page.waitForFunction(() => window.__bangkokProfile!.gpuStatus === 'context lost');
  await page.waitForFunction(() => window.__bangkokRenderer!.ready() && window.__bangkokProfile!.gpuStatus !== 'context lost');
  expect((await inspect()).area.compared).toBe(true);
  expect((await inspect()).stations.every((s) => s.compared === true)).toBe(true);
  await page.getByRole('radio', { name: 'Districts', exact: true }).click();
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  const district = await page.evaluate(() => window.__bangkokRenderer!.inspectArea!('khlong-toei'));
  expect(district.rendered.length).toBeGreaterThan(0);
  expect(district.rendered.every((f) => f.id === 'khlong-toei' && typeof f.state.color === 'string')).toBe(true);
  await page.getByRole('radio', { name: 'Stations', exact: true }).click();
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  expect((await inspect()).area.compared).toBe(true);
  expect((await inspect()).rendered.every((f) => f.id === 'st.asok' && f.state.compared === true)).toBe(true);
});

test('park landcover and names survive score layers, while selection preserves score and grid data', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&profile=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.evaluate(() => window.__bangkokRenderer!.setCamera({ lng: 100.5505, lat: 13.727, zoom: 15.8, pitch: 50, bearing: -20 }));
  for (const level of ['Districts', 'Stations', '200 m grid']) {
    await page.getByRole('radio', { name: level, exact: true }).click();
    await page.waitForFunction(() => window.__bangkokRenderer!.ready());
    const style = await page.evaluate(() => window.__bangkokRenderer!.inspectCartography!());
    expect(style.nature.some((f) => f.layer === 'bkk-landcover' && f.kind === 'grass')).toBe(true);
    expect(style.nature.some((f) => f.layer === 'water')).toBe(true);
    expect(style.nature.some((f) => f.layer === 'bkk-park-labels' && /Lumphini|Benjakitti|Benchakitti/.test(f.name))).toBe(true);
    expect(style.nature.filter((f) => f.layer === 'bkk-park-labels').every((f) => f.kind === 'park')).toBe(true);
    expect(style.layers.indexOf('bkk-area-fill')).toBeLessThan(style.layers.indexOf('bkk-landcover'));
    expect(style.layers.indexOf('bkk-landcover')).toBeLessThan(style.layers.indexOf('water'));
    expect(style.layers.indexOf('water')).toBeLessThan(style.layers.indexOf('bkk-area-focus-fill'));
    expect(style.layers.indexOf('bkk-area-focus-fill')).toBeLessThan(style.layers.indexOf('bkk-buildings'));
    expect(style.focusVisible).toBe(false);
    if (level === '200 m grid') expect(style.layers.indexOf('bkk-grid-texture')).toBeLessThan(style.layers.indexOf('bkk-landcover'));
  }
  await page.evaluate(() => window.__bangkokRenderer!.setCamera({ lng: 100.5606, lat: 13.7374, zoom: 16, pitch: 50, bearing: -20 }));
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  const before = await page.evaluate(() => { window.__bangkokProfile!.reset(); return window.__bangkokRenderer!.stats().gridUploads; });
  const point = await page.evaluate(() => window.__bangkokRenderer!.project(100.56036, 13.73704));
  const box = await page.getByTestId('maplibre-map').boundingBox();
  await page.mouse.click(box!.x + point.x, box!.y + point.y);
  await expect(page.getByRole('region', { name: 'Selected area' })).toBeVisible();
  await expect(page.locator('.maplibregl-popup')).toHaveCount(0);
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  const selected = await page.evaluate(() => ({ style: window.__bangkokRenderer!.inspectCartography!(), area: window.__bangkokRenderer!.inspectArea!('st.asok'),
    uploads: window.__bangkokRenderer!.stats().gridUploads, stages: window.__bangkokProfile!.snapshot().stages }));
  expect(selected.style.focusVisible).toBe(true);
  expect(selected.area.renderedFocus.some((f) => f.state.selected === true)).toBe(true);
  expect(selected.uploads).toBe(before);
  expect(selected.stages['grid.score']).toBeUndefined();
  expect(selected.stages['source.bkk-selected.submit']).toBeUndefined();
  expect(selected.stages['source.bkk-labels.submit']).toBeUndefined();
  const line = selected.style.paint['bkk-area-focus'] as Record<string, unknown>;
  const compare = selected.style.paint['bkk-area-compare'] as Record<string, unknown>;
  expect(line['line-color']).not.toBe(compare['line-color']);
  expect(compare['line-dasharray']).toBeDefined();
  await page.mouse.move(10, 10);
  await page.getByRole('button', { name: 'Close area card' }).click();
  await expect.poll(() => page.evaluate(() => window.__bangkokRenderer!.inspectCartography!().focusVisible)).toBe(false);
});

test('lab pages are noindex', async ({ page }) => {
  for (const renderer of ['maplibre', 'leaflet']) {
    const response = await page.goto(`/bangkok/prototype/${renderer}`);
    expect(response?.ok()).toBe(true);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
  }
});

test('leaving the profiled lab removes diagnostics from production', async ({ page }) => {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&profile=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready() && window.__bangkokProfile);
  await page.getByRole('link', { name: 'Bangkok', exact: true }).click();
  await expect(page).toHaveURL(/\/bangkok(?:\?|$)/);
  await expect(page.getByTestId('maplibre-map')).toBeVisible();
  await expect.poll(() => page.evaluate(() => ['__bangkokRenderer', '__bangkokProfile', '__bangkokGridPaint'].map((key) => key in window))).toEqual([false, false, false]);
});
