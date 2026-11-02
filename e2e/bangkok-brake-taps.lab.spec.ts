import { expect, test, type CDPSession, type Page } from '@playwright/test';
import { flickAndCatch } from './helpers/bangkok-touch-flick';
import { installGestureClock } from './helpers/bangkok-gesture-clock';

test.use({ viewport: { width: 740, height: 650 }, hasTouch: true, deviceScaleFactor: 1 });
// Lab-only: the prototype exposes camera coordinates to verify gesture effects.
test.setTimeout(90_000);
const camera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: 50, bearing: -20 };
const frame = (page: Page) => page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())));
async function open(page: Page, motion: 'system' | 'smooth') {
  await page.goto('/bangkok/prototype/maplibre?lv=grid&adult=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 30_000 });
  await page.evaluate(c => window.__bangkokRenderer!.setCamera(c), camera);
  await page.getByRole('combobox', { name: 'Map motion' }).selectOption(motion);
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 30_000 });
}
async function touch(cd: CDPSession, type: 'touchStart' | 'touchMove' | 'touchEnd', x: number, y: number) {
  await cd.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
}
async function tap(cd: CDPSession, page: Page, x: number, y: number) {
  await touch(cd, 'touchStart', x, y); await page.waitForTimeout(35); await touch(cd, 'touchEnd', x, y);
}
async function point(page: Page) {
  const box = (await page.getByTestId('maplibre-map').boundingBox())!;
  return { x: Math.round(box.x + box.width * .24), y: Math.round(box.y + box.height * .55) };
}
const zoom = (page: Page) => page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom);
const selected = (page: Page) => new URL(page.url()).searchParams.get('s');
async function watchTapTimes(page: Page) {
  await page.evaluate(() => {
    const times: { type: string; time: number }[] = [];
    (window as unknown as { __tapTimes: typeof times }).__tapTimes = times;
    for (const type of ['touchstart', 'touchend']) window.addEventListener(type, event => times.push({ type: event.type, time: event.timeStamp }), true);
  });
}
async function tapInterval(page: Page) {
  const times = await page.evaluate(() => (window as unknown as { __tapTimes: { type: string; time: number }[] }).__tapTimes);
  const ends = times.map((event, i) => ({ event, i })).filter(({ event }) => event.type === 'touchend');
  const first = ends.at(-2)!;
  const secondStart = times.slice(first.i + 1).find(event => event.type === 'touchstart')!;
  return secondStart.time - first.event.time;
}

for (const [preference, motion] of [['no-preference', 'system'], ['reduce', 'smooth']] as const) {
  test(`${preference}/${motion}: catch and quick tap select without zoom; later pan works`, async ({ page, context }) => {
    await installGestureClock(page);
    await page.emulateMedia({ reducedMotion: preference });
    await open(page, motion);
    const cd = await context.newCDPSession(page), { x, y } = await point(page);
    const anchor = () => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, camera);
    await watchTapTimes(page);
    await flickAndCatch(page, cd, { x, y, threshold: 4, keepPaused: true });
    await page.clock.runFor(35); await touch(cd, 'touchEnd', x + 150, y);
    expect(selected(page)).toBeNull();
    const before = await zoom(page);
    await page.clock.runFor(75);
    await touch(cd, 'touchStart', x + 150, y); await page.clock.runFor(35); await touch(cd, 'touchEnd', x + 150, y);
    const interval = await tapInterval(page);
    expect(interval).toBeGreaterThanOrEqual(75); expect(interval).toBeLessThan(300);
    await page.clock.resume();
    await expect.poll(() => selected(page)).toMatch(/^cell\.\d+$/);
    await page.waitForTimeout(450);
    expect(await zoom(page)).toBeCloseTo(before, 3);
    await page.keyboard.press('Escape');
    await expect.poll(() => selected(page)).toBeNull();
    const beforePan = await anchor();
    await touch(cd, 'touchStart', x, y);
    for (const dx of [20, 40, 60, 80]) { await touch(cd, 'touchMove', x + dx, y); await frame(page); }
    await touch(cd, 'touchEnd', x + 80, y);
    expect(Math.abs((await anchor()) - beforePan)).toBeGreaterThan(20);
    await cd.detach();
  });
}

test('ordinary double tap still zooms; single tap selects in reduced motion', async ({ page, context }) => {
  await installGestureClock(page);
  await page.emulateMedia({ reducedMotion: 'reduce' }); await open(page, 'system');
  const cd = await context.newCDPSession(page), { x, y } = await point(page);
  const before = await zoom(page);
  await watchTapTimes(page);
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 2000));
  await touch(cd, 'touchStart', x, y); await page.clock.runFor(35); await touch(cd, 'touchEnd', x, y);
  await page.clock.runFor(75);
  await touch(cd, 'touchStart', x, y); await page.clock.runFor(35); await touch(cd, 'touchEnd', x, y);
  const interval = await tapInterval(page);
  expect(interval).toBeGreaterThanOrEqual(75); expect(interval).toBeLessThan(300);
  await page.clock.resume();
  await expect.poll(() => zoom(page)).toBeGreaterThan(before + .8);
  await page.goto('/bangkok/prototype/maplibre?lv=grid&adult=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 30_000 });
  const fresh = await point(page); await tap(cd, page, fresh.x, fresh.y);
  await expect.poll(() => selected(page)).toMatch(/^cell\.\d+$/);
  await cd.detach();
});

test('catch then add a finger to pinch; cancellation restores taps', async ({ page, context }) => {
  await installGestureClock(page);
  await page.emulateMedia({ reducedMotion: 'reduce' }); await open(page, 'smooth');
  const cd = await context.newCDPSession(page), { x, y } = await point(page);
  await flickAndCatch(page, cd, { x, y, threshold: 4 });
  const px = x + 150;
  const before = await zoom(page);
  const pair = (span: number) => [{ x: px, y, id: 1 }, { x: px + span, y, id: 2 }];
  await cd.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pair(60) });
  for (const span of [80, 100, 130, 160]) {
    await cd.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: pair(span) }); await frame(page);
  }
  await expect.poll(() => zoom(page)).toBeGreaterThan(before + .3);
  await cd.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
  await page.waitForTimeout(100);
  await tap(cd, page, x, y);
  await expect.poll(() => selected(page)).toMatch(/^cell\.\d+$/);
  await cd.detach();
});

test('ordinary double tap and drag still zooms', async ({ page, context }) => {
  await installGestureClock(page);
  await page.emulateMedia({ reducedMotion: 'no-preference' }); await open(page, 'system');
  const cd = await context.newCDPSession(page), { x, y } = await point(page);
  const before = await zoom(page);
  await watchTapTimes(page);
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 2000));
  await touch(cd, 'touchStart', x, y); await page.clock.runFor(35); await touch(cd, 'touchEnd', x, y);
  await page.clock.runFor(75);
  await touch(cd, 'touchStart', x, y);
  for (const dy of [20, 40, 60, 80]) { await touch(cd, 'touchMove', x, y + dy); await page.clock.runFor(16); }
  await touch(cd, 'touchEnd', x, y + 80);
  const interval = await tapInterval(page);
  expect(interval).toBeGreaterThanOrEqual(75); expect(interval).toBeLessThan(300);
  await page.clock.resume();
  await expect.poll(async () => Math.abs(await zoom(page) - before)).toBeGreaterThan(.2);
  await cd.detach();
});

test('cancel a caught contact and select with the next tap', async ({ page, context }) => {
  await installGestureClock(page);
  await page.emulateMedia({ reducedMotion: 'reduce' }); await open(page, 'smooth');
  const cd = await context.newCDPSession(page), { x, y } = await point(page);
  await flickAndCatch(page, cd, { x, y, threshold: 4 });
  await cd.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
  await page.waitForTimeout(75);
  await tap(cd, page, x + 150, y);
  await expect.poll(() => selected(page)).toMatch(/^cell\.\d+$/);
  await cd.detach();
});
