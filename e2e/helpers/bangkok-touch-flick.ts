import type { CDPSession, Page } from '@playwright/test';
import { gestureFrame, pauseGestureClock } from './bangkok-gesture-clock';

const defaultLandmark = { lng: 100.5606, lat: 13.7374 };
const anchor = (page: Page, landmark: { lng: number; lat: number }) => page.evaluate(c => window.__bangkokRenderer!.project(c.lng, c.lat).x, landmark);

/** Leave the catching finger down. Install the gesture clock before navigation.
 * Measure coast only after the final drag frame has committed; freeze time
 * between verifying live movement and delivering the next real touch. */
export async function flickAndCatch(page: Page, cd: CDPSession, options: {
  x: number; y: number; threshold: number; fingers?: 1 | 2;
  landmark?: { lng: number; lat: number }; keepPaused?: boolean;
}) {
  const { x, y, threshold, fingers = 1, landmark = defaultLandmark, keepPaused = false } = options;
  await pauseGestureClock(page);
  const points = (dx: number) => Array.from({ length: fingers }, (_, i) => ({
    x: x + dx + (i - (fingers - 1) / 2) * 60, y, id: i + 1,
  }));
  const frames: number[] = [], drag: number[] = [];
  let caught = false;
  try {
    await cd.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: points(0) });
    for (const dx of [30, 60, 90, 120, 150]) {
      await cd.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: points(dx) });
      await gestureFrame(page);
      drag.push(await anchor(page, landmark));
    }
    if (drag.at(-1)! <= drag.at(-2)!) throw new Error('Final drag input was not committed before release');
    const release = drag.at(-1)!;
    await cd.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    for (let i = 0; i < 40; i++) {
      await gestureFrame(page);
      frames.push(await anchor(page, landmark));
      if (frames.at(-1)! > release + threshold) break;
    }
    if (!frames.length || frames.at(-1)! <= release + threshold) throw new Error(`Coast did not exceed ${threshold}px after release`);
    // Advance one more frame to prove that the glide is still live, then keep
    // virtual time frozen until the catching contact has reached the map.
    await gestureFrame(page);
    frames.push(await anchor(page, landmark));
    if (frames.at(-1)! - frames.at(-2)! <= .1) throw new Error('Glide stopped before the catch');
    await cd.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x + 150, y, id: 1 }] });
    caught = true;
    return { release, frames, drag };
  } catch (error) {
    throw new Error(`Flick/catch failed: ${String(error)}\nPost-release projected positions: ${JSON.stringify({ drag, frames })}`);
  } finally {
    if (!caught || !keepPaused) await page.clock.resume();
  }
}
