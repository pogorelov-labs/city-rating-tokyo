import type { Page } from '@playwright/test';

// Install before navigation: Leaflet captures requestAnimationFrame at import.
// Leave time running during startup, rendering readiness and ordinary UI actions.
export async function installGestureClock(page: Page) {
  await page.clock.install();
}

// Start a scripted input only after the map has settled. pauseAt needs a
// future wall time; the lead leaves room for a busy software-rendered browser.
export async function pauseGestureClock(page: Page) {
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 2_000));
}

// Unlike fastForward, runFor executes each due animation frame. Trusted input
// timestamps, Date.now, performance.now and the renderer share this clock.
export const gestureFrame = (page: Page) => page.clock.runFor(16);
