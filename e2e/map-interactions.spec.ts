import { expect, test, type Page } from '@playwright/test';
import gridHeader from '../app/src/data/bangkok/grid.json';
import bangkokMeta from '../app/src/data/bangkok/meta.json';
import { useStandardBangkokMap } from './support';

test.setTimeout(90_000);

// Tokyo markers are Leaflet Canvas circles, not DOM elements. Observe the
// circles Leaflet actually paints and use their screen coordinates for real
// pointer/touch input; this does not call a marker handler or change the map.
async function observeCanvasMarkers(page: Page) {
  await page.addInitScript(() => {
    type Point = { canvas: HTMLCanvasElement; x: number; y: number; width: number; height: number };
    const state = window as typeof window & { __paintedMarkers: Point[] };
    state.__paintedMarkers = [];
    const clearRect = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function (x, y, width, height) {
      if (this.canvas.closest('.leaflet-overlay-pane')) {
        state.__paintedMarkers = state.__paintedMarkers.filter((p) => p.canvas !== this.canvas);
      }
      return clearRect.call(this, x, y, width, height);
    };
    const arc = CanvasRenderingContext2D.prototype.arc;
    CanvasRenderingContext2D.prototype.arc = function (x, y, radius, start, end, counterclockwise) {
      const canvas = this.canvas;
      if (canvas.closest('.leaflet-overlay-pane') && radius > 0 && canvas.width && canvas.height) {
        const m = this.getTransform();
        state.__paintedMarkers.push({
          canvas, x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f,
          width: canvas.width, height: canvas.height,
        });
      }
      return arc.call(this, x, y, radius, start, end, counterclockwise);
    };
  });
}

async function markerPoint(page: Page) {
  await expect(page.locator('.leaflet-overlay-pane canvas')).toBeVisible({ timeout: 15_000 });
  await expect.poll(() => page.evaluate(() => {
    const state = window as typeof window & { __paintedMarkers?: unknown[] };
    return state.__paintedMarkers?.length ?? 0;
  }), { timeout: 15_000 }).toBeGreaterThan(0);

  const handle = await page.waitForFunction(() => {
    type Point = { canvas: HTMLCanvasElement; x: number; y: number; width: number; height: number };
    const state = window as typeof window & { __paintedMarkers: Point[] };
    const map = document.querySelector('.leaflet-container')!.getBoundingClientRect();
    const points = state.__paintedMarkers.flatMap((p) => {
      if (!p.canvas.isConnected || p.width !== p.canvas.width || p.height !== p.canvas.height) return [];
      const box = p.canvas.getBoundingClientRect();
      const x = box.left + p.x * box.width / p.width;
      const y = box.top + p.y * box.height / p.height;
      if (x < map.left + map.width * .2 || x > map.right - map.width * .2 ||
          y < map.top + map.height * .2 || y > map.bottom - map.height * .3 ||
          document.elementFromPoint(x, y) !== p.canvas) return [];
      return [{ x, y, distance: Math.hypot(x - (map.left + map.width / 2), y - (map.top + map.height / 2)) }];
    });
    points.sort((a, b) => a.distance - b.distance);
    return points.length ? { x: points[0].x, y: points[0].y } : null;
  }, null, { timeout: 15_000 });
  return await handle.jsonValue() as { x: number; y: number };
}

// Leaflet's proxy scale changes with map zoom, independently of tile fetches.
// Waiting for the target scale and the end of its animation avoids tapping
// during an ignored in-flight zoom or clearing observations without a repaint.
async function zoomOutAndWait(page: Page) {
  const proxy = page.locator('.leaflet-proxy');
  const scale = () => proxy.evaluate((el) => {
    const transform = getComputedStyle(el).transform;
    return transform === 'none' ? 1 : new DOMMatrixReadOnly(transform).a;
  });
  const before = await scale();
  await page.locator('.leaflet-container').hover();
  await page.mouse.wheel(0, 480);
  await expect.poll(scale, { timeout: 15_000 }).toBeLessThan(before);
  await expect(page.locator('.leaflet-map-pane')).not.toHaveClass(/leaflet-zoom-anim/, { timeout: 15_000 });
}

async function districtPoint(page: Page) {
  return page.evaluate(() => {
    const paths = document.querySelectorAll<SVGGeometryElement>('.leaflet-bkk-districts-pane path.leaflet-interactive');
    for (const path of paths) {
      const box = path.getBBox();
      const matrix = path.getScreenCTM();
      if (!matrix) continue;
      for (let row = 1; row < 10; row++) for (let col = 1; col < 10; col++) {
        const local = new DOMPoint(box.x + box.width * col / 10, box.y + box.height * row / 10);
        if (!path.isPointInFill(local)) continue;
        const point = local.matrixTransform(matrix);
        if (document.elementFromPoint(point.x, point.y) === path) return { x: point.x, y: point.y };
      }
    }
    throw new Error('No unobstructed Bangkok district polygon in the map viewport');
  });
}

test('canvas marker, popup, details and Bangkok district navigation', async ({ page }, testInfo) => {
  await observeCanvasMarkers(page);
  await page.goto('/?mr=100000');
  const map = page.locator('.leaflet-container');
  await expect(map).toBeVisible({ timeout: 15_000 });
  // The rent filter leaves most central Tokyo markers outside the viewport.
  await map.hover();
  await page.evaluate(() => { (window as typeof window & { __paintedMarkers: unknown[] }).__paintedMarkers = []; });
  await page.mouse.wheel(0, 480);
  const point = await markerPoint(page);
  await page.mouse.click(point.x, point.y);

  const popup = page.locator('.leaflet-popup');
  await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 15_000 }).toBeTruthy();
  const selectedTokyo = new URL(page.url()).searchParams.get('s');
  await expect(map).not.toHaveClass(/map-flying/, { timeout: 15_000 });
  await expect(popup).toBeVisible({ timeout: 15_000 });
  const stationName = popup.getByRole('heading', { level: 2 });
  await expect(stationName).not.toBeEmpty();
  await popup.getByRole('button', { name: '+ Compare', exact: true }).click();
  await expect(popup.getByRole('button', { name: 'Remove compare', exact: true })).toBeVisible();
  await popup.getByRole('button', { name: 'Remove compare', exact: true }).click();
  await expect(popup.getByRole('button', { name: '+ Compare', exact: true })).toBeVisible();
  const stationDetails = popup.getByRole('link', { name: 'Explore this area', exact: true });
  await expect(stationDetails).toHaveAttribute('href', /\/station\//);
  // Keep interaction and navigation evidence only when this intermittent step fails.
  const navigation: string[] = [];
  page.on('request', request => { if (request.isNavigationRequest() || request.url().includes('/station/')) navigation.push(`request ${request.method()} ${request.url()}`); });
  page.on('response', response => { if (response.url().includes('/station/')) navigation.push(`response ${response.status()} ${response.url()}`); });
  await page.evaluate(() => {
    const state = window as typeof window & { __guideClickEvents: string[] };
    state.__guideClickEvents = [];
    for (const method of ['pushState', 'replaceState'] as const) {
      const original = history[method];
      history[method] = function (...args: Parameters<History[typeof method]>) {
        state.__guideClickEvents.push(`${method}: ${String(args[2])}\n${new Error().stack}`);
        return original.apply(this, args);
      };
    }
    for (const type of ['pointerdown', 'pointerup', 'click']) document.addEventListener(type, event => {
      const target = event.target as Element | null;
      const link = target?.closest('a[data-umami-event="view-details"]');
      state.__guideClickEvents.push(`${type}: ${link?.getAttribute('href') ?? target?.tagName ?? 'none'}`);
    }, true);
  });
  try {
    await stationDetails.click();
    await expect(page).toHaveURL(/\/station\/[^/?]+/, { timeout: 12_000 });
  } catch (error) {
    const clicks = await page.evaluate(() => (window as typeof window & { __guideClickEvents?: string[] }).__guideClickEvents ?? []);
    await testInfo.attach('guide-navigation-diagnostics', { body: JSON.stringify({ clicks, navigation }), contentType: 'application/json' });
    throw error;
  }
  await page.goBack();
  await expect(page.locator('.leaflet-container')).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBe(selectedTokyo);
  expect(new URL(page.url()).searchParams.get('mr')).toBe('100000');

  await page.getByRole('link', { name: 'Bangkok', exact: true }).click();
  await expect(page).toHaveURL(/\/bangkok/);
  await useStandardBangkokMap(page);
  await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
  const district = await districtPoint(page);
  await page.mouse.click(district.x, district.y);
  const districtPopup = page.locator('.leaflet-popup');
  await expect(districtPopup).toBeVisible({ timeout: 15_000 });
  await districtPopup.getByRole('button', { name: 'Close area card', exact: true }).click();
  await expect(districtPopup).not.toBeVisible();
  const nextDistrict = await districtPoint(page);
  await page.mouse.click(nextDistrict.x, nextDistrict.y);
  await expect(districtPopup).toBeVisible({ timeout: 15_000 });
  const districtDetails = districtPopup.getByRole('link', { name: 'Explore this area', exact: true });
  await expect(districtDetails).toHaveAttribute('href', /\/bangkok\/district\//);
  await districtDetails.click();
  await expect(page).toHaveURL(/\/bangkok\/district\/[^/?]+/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.goBack();
  await useStandardBangkokMap(page);
  await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
});

test.describe('Escape dismisses map selection', () => {
  for (const [city, url] of [['Tokyo', '/?s=akihabara'], ['Bangkok', '/bangkok?s=pathum-wan']] as const) {
    test(`${city} clears a selected area`, async ({ page }) => {
      await page.goto(url);
      if (city === 'Bangkok') await useStandardBangkokMap(page);
      await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });
      await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeTruthy();
      await page.keyboard.press('Escape');
      await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 10_000 }).toBeNull();
    });
  }
});

test.describe('touch selection', () => {
  test.use({ viewport: { width: 1024, height: 768 }, isMobile: true, hasTouch: true });

  test('tapping zoom in retains the selected station', async ({ page }) => {
    await observeCanvasMarkers(page);
    await page.goto('/?mr=100000');
    await expect(page.getByRole('button', { name: 'Zoom out' })).toBeVisible({ timeout: 15_000 });
    await zoomOutAndWait(page);
    const point = await markerPoint(page);
    await page.touchscreen.tap(point.x, point.y);
    await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 15_000 }).toBeTruthy();
    const selected = new URL(page.url()).searchParams.get('s');
    await expect(page.locator('.leaflet-container')).not.toHaveClass(/map-flying/, { timeout: 15_000 });
    await expect(page.locator('.station-halo')).toBeAttached();
    const tileZoom = () => page.locator('.leaflet-tile').evaluateAll((tiles) => Math.max(0, ...tiles.map((tile) => {
      const path = new URL((tile as HTMLImageElement).src).pathname.split('/');
      return Number(path[path.length - 3]) || 0;
    })));
    const beforeZoom = await tileZoom();
    expect(beforeZoom).toBeGreaterThan(0);
    await page.getByRole('button', { name: 'Zoom in' }).tap({ timeout: 10_000 });
    await expect.poll(tileZoom, { timeout: 10_000 }).toBeGreaterThan(beforeZoom);
    // UrlSync writes after a 300 ms debounce; wait beyond it to catch a clear.
    await page.waitForTimeout(400);
    expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
    await expect(page.locator('.station-halo')).toBeAttached();
  });

  test('Bangkok touch zoom preserves a selected district', async ({ page }) => {
    await page.goto('/bangkok');
    await useStandardBangkokMap(page);
    await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
    const point = await districtPoint(page);
    await page.touchscreen.tap(point.x, point.y);
    await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 15_000 }).toBeTruthy();
    const selected = new URL(page.url()).searchParams.get('s');
    await page.waitForTimeout(800);
    await page.getByRole('button', { name: 'Zoom in' }).tap();
    await page.waitForTimeout(500);
    expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
  });

});

test.describe('phone-width map controls', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  for (const [city, url, closeName] of [
    ['Tokyo station', '/?s=akihabara', 'Close station card'],
    ['Bangkok district', '/bangkok?s=pathum-wan', 'Close district card'],
    ['Bangkok station area', '/bangkok?lv=station&s=st.asok', 'Close station card'],
    ['Bangkok grid cell', '/bangkok?lv=grid&s=cell.41873', 'Close cell card'],
  ] as const) {
    test(`${city}: zoom and card close remain usable`, async ({ page }) => {
      await page.goto(url);
      if (city.startsWith('Bangkok')) await useStandardBangkokMap(page);
      const zoom = page.getByRole('button', { name: 'Zoom in' });
      const zoomOut = page.getByRole('button', { name: 'Zoom out' });
      const close = page.getByRole('button', { name: closeName });
      await expect(zoom).toBeVisible({ timeout: 20_000 });
      await expect(close).toBeVisible({ timeout: 20_000 });
      // Let the flight and 200 ms card transition finish before hit testing.
      await expect(page.locator('.leaflet-container')).not.toHaveClass(/map-flying/, { timeout: 15_000 });
      await page.waitForTimeout(750);
      const zoomBox = await zoom.boundingBox();
      const closeBox = await close.boundingBox();
      const cardBox = await page.getByRole('dialog').boundingBox();
      expect(cardBox).not.toBeNull();
      expect(zoomBox).not.toBeNull();
      expect(closeBox).not.toBeNull();
      // Keep the full card clear, not merely the Close target.
      expect(cardBox!.x + cardBox!.width).toBeLessThanOrEqual(zoomBox!.x);
      // The targets must not overlap: raising the zoom z-index alone can hide Close.
      expect(zoomBox!.x + zoomBox!.width <= closeBox!.x || closeBox!.x + closeBox!.width <= zoomBox!.x ||
        zoomBox!.y + zoomBox!.height <= closeBox!.y || closeBox!.y + closeBox!.height <= zoomBox!.y).toBe(true);
      await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 10_000 }).toBeTruthy();
      const selected = new URL(page.url()).searchParams.get('s');
      const before = await page.locator('.leaflet-tile').evaluateAll((tiles) => Math.max(0, ...tiles.map((tile) => {
        const parts = new URL((tile as HTMLImageElement).src).pathname.split('/');
        return Number(parts[parts.length - 3]) || 0;
      })));
      expect(before).toBeGreaterThan(0);
      await zoom.tap({ timeout: 8_000 });
      await expect.poll(() => page.locator('.leaflet-tile').evaluateAll((tiles) => Math.max(0, ...tiles.map((tile) => {
        const parts = new URL((tile as HTMLImageElement).src).pathname.split('/');
        return Number(parts[parts.length - 3]) || 0;
      }))), { timeout: 10_000 }).toBeGreaterThan(before);
      expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
      await page.waitForTimeout(350); // Leaflet ignores another zoom during its animation.
      await zoomOut.tap({ timeout: 8_000 });
      await expect.poll(() => page.locator('.leaflet-tile').evaluateAll((tiles) => Math.max(0, ...tiles.map((tile) => {
        const parts = new URL((tile as HTMLImageElement).src).pathname.split('/');
        return Number(parts[parts.length - 3]) || 0;
      }))), { timeout: 10_000 }).toBe(before);
      expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
      await close.tap({ timeout: 8_000 });
      await expect.poll(() => new URL(page.url()).searchParams.get('s'), { timeout: 10_000 }).toBeNull();
    });
  }
});


test('short phone: grid card leaves zoom and Close usable', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 568 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto('/bangkok?lv=grid&s=cell.41873');
  await useStandardBangkokMap(page);
  const close = page.getByRole('button', { name: 'Close cell card' });
  const zoomOut = page.getByRole('button', { name: 'Zoom out' });
  await expect(close).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(750);
  const zoomBox = await zoomOut.boundingBox();
  const cardBox = await page.getByRole('dialog').boundingBox();
  expect(cardBox!.x + cardBox!.width).toBeLessThanOrEqual(zoomBox!.x);
  const selected = new URL(page.url()).searchParams.get('s');
  await zoomOut.tap();
  await page.waitForTimeout(400);
  expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
  await close.tap();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
  await context.close();
});


test('phone: expanded air panel does not obstruct zoom or card Close', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto('/bangkok?s=pathum-wan');
  await useStandardBangkokMap(page);
  const close = page.getByRole('button', { name: 'Close district card' });
  await expect(close).toBeVisible({ timeout: 20_000 });
  await page.locator('summary').filter({ hasText: 'Bangkok: air and seasons' }).click();
  await page.waitForTimeout(750);
  const selected = new URL(page.url()).searchParams.get('s');
  await page.getByRole('button', { name: 'Zoom in' }).tap();
  await page.waitForTimeout(400);
  expect(new URL(page.url()).searchParams.get('s')).toBe(selected);
  await close.tap();
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toBeNull();
  await context.close();
});

test('Bangkok map layers and grid filters survive a copied share link', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/bangkok');
  await useStandardBangkokMap(page);
  await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 20_000 });
  await page.getByRole('radio', { name: 'Stations', exact: true }).click();
  await expect(page.locator('.leaflet-bkk-areas-pane path')).toHaveCount(bangkokMeta.station_area_count);
  await page.getByRole('radio', { name: '200 m grid', exact: true }).click();

  const canvas = page.locator('canvas.bkk-grid-canvas');
  const sidebar = page.locator('aside');
  const totalCells = gridHeader.cells.toLocaleString('en-US');
  await expect(canvas).toBeVisible({ timeout: 20_000 });
  await expect(sidebar.getByText(`${totalCells} cells`, { exact: true })).toBeVisible();
  await expect(page.locator('.leaflet-bkk-areas-pane path')).toHaveCount(0);

  // Read the real rendered pixel at the cell containing Soi Cowboy, not a
  // mocked layer or a direct call to the filtering function.
  const x = Math.floor((100.5621 - gridHeader.west) / (gridHeader.east - gridHeader.west) * gridHeader.nx);
  const y = Math.floor((gridHeader.north - 13.7376) / (gridHeader.north - gridHeader.south) * gridHeader.ny);
  const readPixel = () => canvas.evaluate((el, point) =>
    Array.from((el as HTMLCanvasElement).getContext('2d')!.getImageData(point.x, point.y, 1, 1).data), { x, y });
  await expect.poll(async () => (await readPixel())[3]).toBeGreaterThan(0);
  const unfilteredPixel = await readPixel();
  const family = sidebar.getByRole('checkbox', { name: /Family-friendly/ });
  const flood = sidebar.getByRole('checkbox', { name: /Hide flood-risk areas/ });
  await family.check();
  await expect.poll(async () => {
    const p = await readPixel();
    return Math.abs(p[0] - 229) <= 2 && Math.abs(p[1] - 231) <= 2 && Math.abs(p[2] - 235) <= 2 && p[3] === 140;
  }).toBe(true);
  expect(await readPixel()).not.toEqual(unfilteredPixel);
  await expect(sidebar.getByText(new RegExp(`of ${totalCells} cells match`))).toBeVisible();

  await flood.check();
  await page.getByRole('button', { name: 'Share', exact: true }).click();
  await expect(page.getByText('Copied!', { exact: true })).toBeVisible();
  const shared = await page.evaluate(() => navigator.clipboard.readText());
  const params = new URL(shared).searchParams;
  expect(params.get('lv')).toBe('grid');
  expect(params.get('flood')).toBe('1');
  expect(params.get('adult')).toBe('1');

  await page.goto(shared);
  await useStandardBangkokMap(page);
  await expect(sidebar.getByRole('checkbox', { name: /Family-friendly/ })).toBeChecked();
  await expect(sidebar.getByRole('checkbox', { name: /Hide flood-risk areas/ })).toBeChecked();
  await expect(canvas).toBeVisible({ timeout: 20_000 });
  await sidebar.getByRole('checkbox', { name: /Family-friendly/ }).uncheck();
  await sidebar.getByRole('checkbox', { name: /Hide flood-risk areas/ }).uncheck();
  await expect(sidebar.getByText(`${totalCells} cells`, { exact: true })).toBeVisible();
  await expect.poll(readPixel).toEqual(unfilteredPixel);

  // Hit-test a painted cell through the browser's real pointer path.
  const point = await canvas.evaluate((el) => {
    const canvas = el as HTMLCanvasElement;
    const bounds = canvas.getBoundingClientRect();
    const map = canvas.closest('.leaflet-container')!.getBoundingClientRect();
    const pixels = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height).data;
    for (let row = 20; row < canvas.height - 20; row++) {
      for (let col = 20; col < canvas.width - 20; col++) {
        if (!pixels[(row * canvas.width + col) * 4 + 3]) continue;
        // At low zoom, a pointer can round into an adjacent cell. Pick a
        // built-up interior rather than a one-pixel city boundary.
        if (![-1, 0, 1].every((dy) => [-1, 0, 1].every((dx) =>
          pixels[((row + dy) * canvas.width + col + dx) * 4 + 3] > 0))) continue;
        // MouseEvent client coordinates are integer CSS pixels. Round the
        // centre before hit testing, especially when a grid cell is ~1 px.
        const x = Math.round(bounds.left + (col + 0.5) * bounds.width / canvas.width);
        const y = Math.round(bounds.top + (row + 0.5) * bounds.height / canvas.height);
        if (x < map.left + 30 || x > map.right - 30 || y < map.top + 30 || y > map.bottom - 30) continue;
        const target = document.elementFromPoint(x, y);
        if (!target?.closest('.leaflet-container') ||
            target.closest('.leaflet-interactive, .leaflet-marker-icon, .leaflet-popup, .leaflet-control')) continue;
        return { x, y, index: row * canvas.width + col };
      }
    }
    throw new Error('No unobstructed painted grid cell in the viewport');
  });
  await page.mouse.move(point.x, point.y);
  await expect(page.locator('.grid-tooltip')).toBeVisible();
  await page.mouse.click(point.x, point.y);
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).toMatch(/^cell\.\d+$/);
  const selectedIndex = Number(new URL(page.url()).searchParams.get('s')!.slice(5));
  expect(Math.abs(Math.floor(selectedIndex / gridHeader.nx) - Math.floor(point.index / gridHeader.nx))).toBeLessThanOrEqual(1);
  expect(Math.abs(selectedIndex % gridHeader.nx - point.index % gridHeader.nx)).toBeLessThanOrEqual(1);
  await expect(page.locator('.leaflet-popup')).toBeVisible();
});

test('phone restores and updates Bangkok grid filters from a link', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto('/bangkok?lv=grid&flood=1&adult=1');
  await useStandardBangkokMap(page);
  // Next dev's indicator covers the mobile filter button; it is not present
  // in production and should not intercept the user action under test.
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page.locator('canvas.bkk-grid-canvas')).toBeVisible({ timeout: 20_000 });
  await page.getByRole('button', { name: 'Filters', exact: true }).tap();
  const family = page.getByRole('checkbox', { name: /Family-friendly/ });
  const flood = page.getByRole('checkbox', { name: /Hide flood-risk areas/ });
  await expect(family).toBeChecked();
  await expect(flood).toBeChecked();
  await family.uncheck();
  await expect.poll(() => new URL(page.url()).searchParams.has('adult')).toBe(false);
  expect(new URL(page.url()).searchParams.get('flood')).toBe('1');
  await page.reload();
  await useStandardBangkokMap(page);
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await page.getByRole('button', { name: 'Filters', exact: true }).tap();
  await expect(family).not.toBeChecked();
  await expect(flood).toBeChecked();
  await context.close();
});
