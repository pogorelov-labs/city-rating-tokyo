import { expect, test, type Page } from '@playwright/test';

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

test('canvas marker, popup, details and Bangkok district navigation', async ({ page }) => {
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
  await expect(map).not.toHaveClass(/map-flying/, { timeout: 15_000 });
  await expect(popup).toBeVisible({ timeout: 15_000 });
  const stationName = popup.locator('.font-bold.text-base span').first();
  await expect(stationName).not.toBeEmpty();
  const stationDetails = popup.getByRole('link', { name: 'View details →' });
  await expect(stationDetails).toHaveAttribute('href', /\/station\//);
  await stationDetails.click();
  await expect(page).toHaveURL(/\/station\/[^/?]+/, { timeout: 12_000 });
  await page.goBack();
  await expect(page.locator('.leaflet-container')).toBeVisible();

  await page.getByRole('link', { name: 'Bangkok', exact: true }).click();
  await expect(page).toHaveURL(/\/bangkok/);
  await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
  const district = await districtPoint(page);
  await page.mouse.click(district.x, district.y);
  const districtPopup = page.locator('.leaflet-popup');
  await expect(districtPopup).toBeVisible({ timeout: 15_000 });
  const districtDetails = districtPopup.getByRole('link', { name: 'View details →' });
  await expect(districtDetails).toHaveAttribute('href', /\/bangkok\/district\//);
  await districtDetails.click();
  await expect(page).toHaveURL(/\/bangkok\/district\/[^/?]+/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.goBack();
  await expect(page.locator('.leaflet-bkk-districts-pane path')).toHaveCount(50, { timeout: 15_000 });
});

test.describe('Escape dismisses map selection', () => {
  for (const [city, url] of [['Tokyo', '/?s=akihabara'], ['Bangkok', '/bangkok?s=pathum-wan']] as const) {
    test(`${city} clears a selected area`, async ({ page }) => {
      await page.goto(url);
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
    await page.evaluate(() => { (window as typeof window & { __paintedMarkers: unknown[] }).__paintedMarkers = []; });
    await page.getByRole('button', { name: 'Zoom out' }).tap();
    await page.waitForTimeout(350); // Leaflet ignores another zoom during its animation.
    await page.getByRole('button', { name: 'Zoom out' }).tap();
    await page.waitForTimeout(350);
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
