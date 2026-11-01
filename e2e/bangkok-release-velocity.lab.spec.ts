import { expect, test, type BrowserContext, type CDPSession, type Page } from '@playwright/test';
import { observePanRelease } from './helpers/bangkok-release-trace';
import { gestureFrame, installGestureClock, pauseGestureClock } from './helpers/bangkok-gesture-clock';
import { flickAndCatch } from './helpers/bangkok-touch-flick';

test.use({ viewport: { width: 740, height: 650 }, hasTouch: true, deviceScaleFactor: 1 });
const camera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: 50, bearing: -20 };
const anchor = (page: Page) => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, camera);

async function open(page: Page, motion: 'reduce' | 'no-preference') {
  await installGestureClock(page);
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

async function assertReversal(page: Page, context: BrowserContext, motion: 'no-preference' | 'reduce',
  input: 'mouse' | 'touch', steps: number[]) {
  const { x, y } = await open(page, motion);
  const cd = await context.newCDPSession(page);
  const sendTouch = touch(cd, x, y, 1);
  await pauseGestureClock(page);
  const initial = await anchor(page);
  const readTrace = await observePanRelease(page, input, camera);
  if (input === 'mouse') { await page.mouse.move(x, y); await page.mouse.down(); }
  else await sendTouch('touchStart');
  for (const dx of steps.slice(0, -1)) {
    if (input === 'mouse') await page.mouse.move(x + dx, y);
    else await sendTouch('touchMove', dx);
    await gestureFrame(page);
  }
  // The previous and final input must both reach the camera before lift, so
  // first-frame coast cannot include a still-pending movement of the finger.
  expect(await anchor(page)).toBeLessThan(initial + steps.at(-2)! + 8);
  const beforeLastMove = await anchor(page);
  if (input === 'mouse') await page.mouse.move(x + steps.at(-1)!, y);
  else await sendTouch('touchMove', steps.at(-1)!);
  await gestureFrame(page);
  expect(await anchor(page)).toBeLessThan(beforeLastMove - 10);
  if (input === 'mouse') await page.mouse.up(); else await sendTouch('touchEnd');
  await page.clock.runFor(650);
  const observed = await readTrace();
  await page.clock.resume();
  await test.info().attach('signed-release', { body: JSON.stringify({ motion, input, steps, ...observed }), contentType: 'application/json' });
  expect(observed.inputToLiftMs, `gesture was held before release: ${JSON.stringify(observed.events)}`).toBeLessThan(100);
  expect(observed.furthestRightPx).toBeLessThan(2);
  expect(observed.coastPx).toBeLessThan(-2);
  expect(observed.coastPx).toBeGreaterThan(-380); // 378 px configured cap plus sampling tolerance
  await cd.detach();
}

for (const motion of ['no-preference', 'reduce'] as const) {
  for (const input of ['mouse', 'touch'] as const) {
    test(`${motion}: ${input} release follows a late reversal`, async ({ page, context }) => {
      await assertReversal(page, context, motion, input, [45, 90, 135, 180, 225, 270, 250, 230, 210, 190]);
    });
  }

  test(`${motion}: a parallel two-finger pan coasts and can be caught`, async ({ page, context }) => {
    const { x, y } = await open(page, motion);
    const cd = await context.newCDPSession(page);
    const one = touch(cd, x + 150, y, 1);
    const before = await anchor(page);
    const { release: released, frames } = await flickAndCatch(page, cd, { x, y, threshold: 3, fingers: 2 });
    expect(released - before).toBeGreaterThan(50);
    const caught = await anchor(page);
    await page.waitForTimeout(180);
    const heldDrift = await anchor(page) - caught;
    await test.info().attach('two-finger-catch', { body: JSON.stringify({ motion, coastBeforeCatchPx: caught - released, frames, heldDriftPx: heldDrift }), contentType: 'application/json' });
    expect(Math.abs(heldDrift)).toBeLessThan(3);
    await one('touchEnd');
    await page.waitForTimeout(350);
    expect(new URL(page.url()).searchParams.get('s')).toBeNull();
    await cd.detach();
  });
}

test('reduce: Smooth follows a final 35 px mouse reversal', async ({ page, context }) => {
  // At 16 ms per step, the old 100 ms endpoint average includes x=135 and
  // finishes at x=235: it points +100 px right despite the final -35 px.
  await assertReversal(page, context, 'reduce', 'mouse', [45, 90, 135, 180, 225, 270, 253, 235]);
});

test('reduce: lifting one finger and continuing with the other does not throw the old two-finger pan', async ({ page, context }) => {
  const { x, y } = await open(page, 'reduce');
  const cd = await context.newCDPSession(page);
  const two = touch(cd, x, y, 2);
  await pauseGestureClock(page);
  await two('touchStart');
  for (const dx of [30, 60, 90, 120, 150]) { await two('touchMove', dx); await gestureFrame(page); }
  await cd.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [{ x: x + 180, y, id: 2 }] });
  await cd.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + 200, y, id: 2 }] });
  await gestureFrame(page);
  const released = await anchor(page);
  await cd.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await page.clock.runFor(450);
  expect(Math.abs(await anchor(page) - released)).toBeLessThan(3);
  await page.clock.resume();
  await cd.detach();
});

test('reduce: cancelled two-finger pan does not coast', async ({ page, context }) => {
  const { x, y } = await open(page, 'reduce');
  const cd = await context.newCDPSession(page);
  const two = touch(cd, x, y, 2);
  await pauseGestureClock(page);
  const before = await anchor(page);
  await two('touchStart');
  for (const dx of [30, 60, 90, 120, 150]) { await two('touchMove', dx); await gestureFrame(page); }
  const released = await anchor(page);
  expect(released - before).toBeGreaterThan(50);
  await cd.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
  await page.clock.runFor(450);
  expect(Math.abs(await anchor(page) - released)).toBeLessThan(3);
  await page.clock.resume();
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
  await pauseGestureClock(page);
  await send('touchStart', 0, 30);
  for (const dx of [30, 60, 90]) { await send('touchMove', dx, 30); await gestureFrame(page); }
  for (const spread of [45, 60, 75]) { await send('touchMove', 90, spread); await gestureFrame(page); }
  const released = await anchor(page);
  await send('touchEnd', 90, 75);
  await page.clock.runFor(450);
  expect((await page.evaluate(() => window.__bangkokRenderer!.getCamera().zoom)) - initialZoom).toBeGreaterThan(.1);
  expect(Math.abs(await anchor(page) - released)).toBeLessThan(3);
  await page.clock.resume();
  await cd.detach();
});

for (const motion of ['no-preference', 'reduce'] as const) {
  test(`${motion}: holding still before release does not coast`, async ({ page }) => {
    const { x, y } = await open(page, motion);
    await pauseGestureClock(page);
    await page.mouse.move(x, y); await page.mouse.down();
    for (const dx of [30, 60, 90, 120, 150]) { await page.mouse.move(x + dx, y); await gestureFrame(page); }
    await page.clock.runFor(250);
    const released = await anchor(page);
    await page.mouse.up();
    await page.clock.runFor(450);
    const coast = await anchor(page) - released;
    await test.info().attach('held-release', { body: JSON.stringify({ motion, coastPx: coast }), contentType: 'application/json' });
    expect(Math.abs(coast)).toBeLessThan(3);
    await page.clock.resume();
  });
}
