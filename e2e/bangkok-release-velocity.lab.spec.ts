import { expect, test, type CDPSession, type Page } from '@playwright/test';
import { observePanRelease } from './helpers/bangkok-release-trace';

test.use({ viewport: { width: 740, height: 650 }, hasTouch: true, deviceScaleFactor: 1 });
const camera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: 50, bearing: -20 };
const frame = (page: Page) => page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())));
const anchor = (page: Page) => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, camera);

async function open(page: Page, motion: 'reduce' | 'no-preference') {
  await page.emulateMedia({ reducedMotion: motion });
  await page.goto('/bangkok/prototype/maplibre?lv=grid&adult=1');
  await page.waitForFunction(() => window.__bangkokRenderer?.ready(), null, { timeout: 30_000 });
  await page.evaluate(c => window.__bangkokRenderer!.setCamera(c), camera);
  await page.waitForFunction(() => window.__bangkokRenderer!.ready());
  await page.getByRole('combobox', { name: 'Map motion' }).selectOption('smooth');
  const box = (await page.getByTestId('maplibre-map').boundingBox())!;
  return { x: Math.round(box.x + box.width * .24), y: Math.round(box.y + box.height * .55) };
}

function touch(cd: CDPSession, x: number, y: number, fingers: number) {
  return (type: 'touchStart' | 'touchMove' | 'touchEnd', dx = 0) => cd.send('Input.dispatchTouchEvent', {
    type, touchPoints: type === 'touchEnd' ? [] : Array.from({ length: fingers }, (_, i) => ({
      x: x + dx + (i - (fingers - 1) / 2) * 60, y, id: i + 1,
    })),
  });
}

for (const motion of ['no-preference', 'reduce'] as const) {
  for (const input of ['mouse', 'touch'] as const) {
    test(`${motion}: ${input} release follows a late reversal`, async ({ page, context }) => {
      const { x, y } = await open(page, motion);
      const cd = await context.newCDPSession(page);
      const sendTouch = touch(cd, x, y, 1);
      const trace = observePanRelease(page, input, camera);
      if (input === 'mouse') { await page.mouse.move(x, y); await page.mouse.down(); }
      else await sendTouch('touchStart');
      for (const dx of [45, 90, 135, 180, 225, 270, 250, 230, 210, 190]) {
        if (input === 'mouse') await page.mouse.move(x + dx, y);
        else await sendTouch('touchMove', dx);
        await frame(page);
      }
      if (input === 'mouse') await page.mouse.up(); else await sendTouch('touchEnd');
      const observed = await trace;
      await test.info().attach('signed-release', { body: JSON.stringify({ motion, input, ...observed }), contentType: 'application/json' });
      // Check the handoff as well as its endpoint: a wrong-way first frame
      // must not pass just because a later frame corrects the destination.
      expect(observed.furthestRightPx).toBeLessThan(2);
      expect(observed.coastPx).toBeLessThan(-2);
      expect(observed.coastPx).toBeGreaterThan(-380); // 378 px configured cap plus sampling tolerance
      await cd.detach();
    });
  }

  test(`${motion}: a parallel two-finger pan coasts and can be caught`, async ({ page, context }) => {
    const { x, y } = await open(page, motion);
    const cd = await context.newCDPSession(page);
    const two = touch(cd, x, y, 2), one = touch(cd, x + 150, y, 1);
    const before = await anchor(page);
    await two('touchStart');
    for (const dx of [30, 60, 90, 120, 150]) { await two('touchMove', dx); await frame(page); }
    await two('touchEnd');
    await frame(page);
    const released = await anchor(page);
    expect(released - before).toBeGreaterThan(50);
    await page.waitForFunction(({ c, at }) => window.__bangkokRenderer!.project(c.lng, c.lat).x > at + 3,
      { c: camera, at: released }, { polling: 'raf', timeout: 2000 });
    await one('touchStart');
    const caught = await anchor(page);
    await page.waitForTimeout(180);
    const heldDrift = await anchor(page) - caught;
    await test.info().attach('two-finger-catch', { body: JSON.stringify({ motion, coastBeforeCatchPx: caught - released, heldDriftPx: heldDrift }), contentType: 'application/json' });
    expect(Math.abs(heldDrift)).toBeLessThan(3);
    await one('touchEnd');
    await page.waitForTimeout(350);
    expect(new URL(page.url()).searchParams.get('s')).toBeNull();
    await cd.detach();
  });
}

test('reduce: lifting one finger and continuing with the other does not throw the old two-finger pan', async ({ page, context }) => {
  const { x, y } = await open(page, 'reduce');
  const cd = await context.newCDPSession(page);
  const two = touch(cd, x, y, 2);
  await two('touchStart');
  for (const dx of [30, 60, 90, 120, 150]) { await two('touchMove', dx); await frame(page); }
  await cd.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [{ x: x + 180, y, id: 2 }] });
  await cd.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + 200, y, id: 2 }] });
  await frame(page);
  await cd.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await frame(page);
  const released = await anchor(page);
  await page.waitForTimeout(450);
  expect(Math.abs(await anchor(page) - released)).toBeLessThan(3);
  await cd.detach();
});

test('reduce: pinch changes zoom without throwing an earlier pan', async ({ page, context }) => {
  const { x, y } = await open(page, 'reduce');
  const cd = await context.newCDPSession(page);
  const send = (type: 'touchStart' | 'touchMove' | 'touchEnd', dx: number, spread: number) => cd.send('Input.dispatchTouchEvent', {
    type, touchPoints: type === 'touchEnd' ? [] : [
      { x: x + dx - spread, y, id: 1 }, { x: x + dx + spread, y, id: 2 },
    ],
  });
  const initialZoom = await page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom);
  await send('touchStart', 0, 30);
  for (const dx of [30, 60, 90]) { await send('touchMove', dx, 30); await frame(page); }
  for (const spread of [45, 60, 75]) { await send('touchMove', 90, spread); await frame(page); }
  await send('touchEnd', 90, 75);
  await frame(page);
  const released = await anchor(page);
  await page.waitForTimeout(450);
  expect((await page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom)) - initialZoom).toBeGreaterThan(.1);
  expect(Math.abs(await anchor(page) - released)).toBeLessThan(3);
  await cd.detach();
});

for (const motion of ['no-preference', 'reduce'] as const) {
  test(`${motion}: holding still before release does not coast`, async ({ page }) => {
    const { x, y } = await open(page, motion);
    await page.mouse.move(x, y); await page.mouse.down();
    for (const dx of [30, 60, 90, 120, 150]) { await page.mouse.move(x + dx, y); await frame(page); }
    await page.waitForTimeout(250);
    await page.mouse.up(); await frame(page);
    const released = await anchor(page);
    await page.waitForTimeout(450);
    const coast = await anchor(page) - released;
    await test.info().attach('held-release', { body: JSON.stringify({ motion, coastPx: coast }), contentType: 'application/json' });
    expect(Math.abs(coast)).toBeLessThan(3);
  });
}
