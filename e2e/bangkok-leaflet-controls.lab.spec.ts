import { expect, test, type Page } from '@playwright/test';

test.use({ viewport: { width: 740, height: 650 }, deviceScaleFactor: 1, hasTouch: true });

const camera = { lat: 13.7374, lng: 100.5606, zoom: 16, pitch: 0, bearing: 0 };

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/bangkok/prototype/leaflet?lv=grid&adult=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.getByRole('combobox', { name: 'Map motion' }).selectOption('smooth');
  await page.evaluate(c => window.__bangkokRenderer!.setCamera(c), camera);
  await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
});

// Observe release and the beginning of inertia in the page, avoiding a
// protocol round trip that can miss the short coast on a busy test runner.
type CoastObservation = { release: number; max: number; moves: number[] };
type CatchObservation = { lastMotionAge: number; lastStep: number; frameGap: number };
async function watchCoast(page: Page, eventName: 'touchend' | 'mouseup') {
  await page.evaluate(({ eventName, camera }) => {
    const state = window as unknown as { coast: Promise<CoastObservation>; caught: Promise<CatchObservation> };
    const times: number[] = [];
    const moveName = eventName === 'touchend' ? 'touchmove' : 'mousemove';
    const downName = eventName === 'touchend' ? 'touchstart' : 'mousedown';
    const record = () => times.push(performance.now());
    window.addEventListener(moveName, record, true);
    let finishCatch: (value: CatchObservation) => void;
    state.caught = new Promise(resolve => { finishCatch = resolve; });
    state.coast = new Promise(resolve => {
      window.addEventListener(eventName, () => {
        window.removeEventListener(moveName, record, true);
        const project = () => window.__bangkokRenderer!.project(camera.lng, camera.lat).x;
        const release = project(), start = performance.now();
        let previous = release, max = release, lastMotion = -Infinity, lastStep = 0, previousFrame = start, frameGap = 0;
        let caught = false, reported = false;
        window.addEventListener(downName, () => {
          caught = true;
          finishCatch({ lastMotionAge: performance.now() - lastMotion, lastStep, frameGap });
        }, { capture: true, once: true });
        const sample = (now: number) => {
          const current = project(), step = Math.abs(current - previous);
          frameGap = now - previousFrame; previousFrame = now; previous = current;
          if (step > .05) { lastMotion = performance.now(); lastStep = step; }
          max = Math.max(max, current);
          if (!reported && (max > release + 3 || performance.now() - start > 2000)) {
            reported = true;
            resolve({ release, max, moves: times.map(t => Math.round(start - t)) });
          }
          if (!caught && performance.now() - start < 2500) requestAnimationFrame(sample);
        };
        requestAnimationFrame(sample);
      }, { capture: true, once: true });
    });
  }, { eventName, camera });
}
async function requireCoast(page: Page) {
  const observation = await page.evaluate(() => (window as unknown as { coast: Promise<CoastObservation> }).coast);
  expect(observation.max - observation.release, `No coast detected; release observation: ${JSON.stringify(observation)}`).toBeGreaterThan(3);
}
async function requireActiveCatch(page: Page) {
  const observation = await page.evaluate(() => (window as unknown as { caught: Promise<CatchObservation> }).caught);
  expect(observation.lastStep, `No moving frame before contact: ${JSON.stringify(observation)}`).toBeGreaterThan(.05);
  expect(observation.lastMotionAge, `Coast stopped before contact: ${JSON.stringify(observation)}`).toBeLessThan(Math.max(100, observation.frameGap * 2));
}

for (const mode of ['smooth', 'device'] as const) test(`rapid ${mode} zoom accumulates and external camera changes cancel intent`, async ({ page }) => {
  if (mode === 'device') {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.getByRole('combobox', { name: 'Map motion' }).selectOption('system');
    await page.reload();
    await page.waitForFunction(() => window.__bangkokRenderer?.ready());
  }
  await page.evaluate(c => window.__bangkokRenderer!.setCamera({ ...c, zoom: 14 }), camera);
  const plus = page.getByRole('button', { name: 'Zoom in', exact: true });
  const minus = page.getByRole('button', { name: 'Zoom out', exact: true });
  const a = (await plus.boundingBox())!, b = (await minus.boundingBox())!;
  for (const box of [a, a, a, b]) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect.poll(() => page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom)).toBeCloseTo(16, 2);
  await page.mouse.click(a.x + a.width / 2, a.y + a.height / 2);
  await page.evaluate(c => window.__bangkokRenderer!.setCamera({ ...c, zoom: 12 }), camera);
  await page.mouse.click(a.x + a.width / 2, a.y + a.height / 2);
  await expect.poll(() => page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom)).toBeCloseTo(13, 2);
});

test('follow device with reduced motion zooms immediately', async ({ page }) => {
  await page.getByRole('combobox', { name: 'Map motion' }).selectOption('system');
  await page.evaluate(c => window.__bangkokRenderer!.setCamera({ ...c, zoom: 14 }), camera);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  expect(await page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom)).toBe(15);
});

test('touch catches coast immediately and subsequent taps still select', async ({ page, context }) => {
  const cd = await context.newCDPSession(page);
  const box = (await page.locator('.leaflet-container').boundingBox())!;
  const x = Math.round(box.x + box.width * .24), y = Math.round(box.y + box.height * .55);
  const touch = (type: 'touchStart' | 'touchMove' | 'touchEnd', dx = 0, dy = 0) => cd.send('Input.dispatchTouchEvent', {
    type, touchPoints: type === 'touchEnd' ? [] : [{ x: x + dx, y: y + dy, id: 1 }],
  });
  const anchor = () => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, camera);
  await watchCoast(page, 'touchend');
  await touch('touchStart');
  // Queue native moves in order before awaiting acknowledgments: CDP may wait
  // for a frame per acknowledgment, exceeding Leaflet's 50 ms sample window.
  await Promise.all(Array.from({ length: 10 }, (_, i) => touch('touchMove', (i + 1) * 15)));
  await touch('touchEnd');
  await requireCoast(page);
  await page.evaluate(() => {
    (window as unknown as { labClicks: number }).labClicks = 0;
    document.querySelector('.leaflet-container')!.addEventListener('click', () => (window as unknown as { labClicks: number }).labClicks++);
  });
  await touch('touchStart', 150);
  await requireActiveCatch(page);
  const down = await anchor();
  await page.waitForTimeout(220);
  const held = await anchor();
  await touch('touchEnd');
  await page.waitForTimeout(75);
  expect(new URL(page.url()).searchParams.get('s')).toBeNull();
  expect(Math.abs(held - down)).toBeLessThan(2);
  expect(await page.evaluate(() => (window as unknown as { labClicks: number }).labClicks)).toBe(0);
  await touch('touchStart', 150);
  await page.waitForTimeout(40);
  await touch('touchEnd');
  await expect.poll(() => page.evaluate(() => (window as unknown as { labClicks: number }).labClicks)).toBe(1);
  const dragBefore = await anchor();
  await touch('touchStart', 100);
  for (const dx of [110, 120, 130, 140]) await touch('touchMove', dx);
  await touch('touchEnd');
  expect(Math.abs(await anchor() - dragBefore)).toBeGreaterThan(10);
  await page.waitForTimeout(1200);
  await page.evaluate(c => window.__bangkokRenderer!.setCamera(c), camera);
  const point = await page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat), camera);
  const pickDx = Math.round(box.x + point.x - x);
  const pickDy = Math.round(box.y + point.y - y);
  await touch('touchStart', pickDx, pickDy);
  await page.waitForTimeout(40);
  await touch('touchEnd', pickDx);
  await expect.poll(() => new URL(page.url()).searchParams.get('s')).not.toBeNull();
  await cd.detach();
});


test('mouse contact catches a coast and the following drag works', async ({ page }) => {
  const box = (await page.locator('.leaflet-container').boundingBox())!;
  const x = Math.round(box.x + box.width * .24), y = Math.round(box.y + box.height * .55);
  const anchor = () => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, camera);
  await watchCoast(page, 'mouseup');
  await page.mouse.move(x, y); await page.mouse.down();
  for (let dx = 15; dx <= 150; dx += 15) await page.mouse.move(x + dx, y);
  await page.mouse.up();
  await requireCoast(page);
  await page.mouse.down();
  await requireActiveCatch(page);
  const down = await anchor();
  await page.waitForTimeout(220);
  expect(Math.abs(await anchor() - down)).toBeLessThan(2);
  await page.mouse.up();
  await page.waitForTimeout(75);
  expect(new URL(page.url()).searchParams.get('s')).toBeNull();
  const before = await anchor();
  await page.mouse.down(); await page.mouse.move(x + 190, y, { steps: 5 }); await page.mouse.up();
  expect(Math.abs(await anchor() - before)).toBeGreaterThan(10);
});
