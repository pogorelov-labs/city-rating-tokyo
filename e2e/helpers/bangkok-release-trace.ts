import type { Page } from '@playwright/test';

/** A lab observer, not an animation driver. Track the same geographic point
 * through the drag and release using the renderer's public diagnostic bridge. */
export function observePanRelease(page: Page, input: 'mouse' | 'touch', landmark: { lng: number; lat: number }) {
  return page.evaluate(({ input, landmark }) => new Promise<{
    frames: { ms: number; x: number; y: number }[];
    coastPx: number;
    furthestRightPx: number;
    firstFrameDx: number;
  }>(resolve => {
    const renderer = window.__bangkokRenderer!;
    const frames: { ms: number; x: number; y: number }[] = [];
    let xAtLift: number | undefined, firstReleaseFrame = -1;
    window.addEventListener(input === 'mouse' ? 'mouseup' : 'touchend', () => {
      xAtLift = renderer.project(landmark.lng, landmark.lat).x;
    }, { capture: true, once: true });
    const sample = (time: number) => {
      const point = renderer.project(landmark.lng, landmark.lat);
      if (xAtLift !== undefined && firstReleaseFrame === -1) firstReleaseFrame = frames.length;
      frames.push({ ms: time, x: point.x, y: point.y });
      const origin = frames[firstReleaseFrame];
      if (origin && xAtLift !== undefined && time - origin.ms >= 600) {
        const relative = frames.map(p => ({ ms: p.ms - origin.ms, x: p.x - origin.x, y: p.y - origin.y }));
        const firstFrameDx = origin.x - xAtLift;
        resolve({ frames: relative, coastPx: point.x - origin.x, firstFrameDx,
          furthestRightPx: Math.max(...relative.slice(firstReleaseFrame).map(p => p.x + firstFrameDx)) });
      } else requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  }), { input, landmark });
}
