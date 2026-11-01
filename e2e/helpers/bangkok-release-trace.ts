import type { Page } from '@playwright/test';

type Point = { ms: number; x: number; y: number };

/** Arm before the first move, then read after running the observation window.
 * The caller verifies the final drag reached the camera before lifting. */
export async function observePanRelease(page: Page, input: 'mouse' | 'touch',
  landmark: { lng: number; lat: number }, duration = 600) {
  const handle = await page.evaluateHandle(({ input, landmark, duration }) => {
    const state: { lift?: Point; frames: Point[]; events: { type: string; ms: number; x: number }[] } =
      { frames: [], events: [] };
    const renderer = window.__bangkokRenderer!;
    const [move, end] = input === 'mouse' ? ['mousemove', 'mouseup'] : ['touchmove', 'touchend'];
    const collect = (event: Event) => {
      const touch = event as TouchEvent;
      const x = input === 'mouse' ? (event as MouseEvent).clientX : (touch.touches[0] ?? touch.changedTouches[0]).clientX;
      state.events.push({ type: event.type, ms: event.timeStamp, x });
      if (event.type !== end || (input === 'touch' && touch.touches.length)) return;
      const lift = { ms: event.timeStamp, ...renderer.project(landmark.lng, landmark.lat) };
      state.lift = lift;
      window.removeEventListener(move, collect, true);
      window.removeEventListener(end, collect, true);
      const sample = (now: number) => {
        const p = renderer.project(landmark.lng, landmark.lat);
        state.frames.push({ ms: now - lift.ms, x: p.x - lift.x, y: p.y - lift.y });
        if (now - lift.ms < duration) requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    };
    window.addEventListener(move, collect, true);
    window.addEventListener(end, collect, true);
    return state;
  }, { input, landmark, duration });

  return async () => {
    try {
      const { frames, lift, events } = await handle.jsonValue();
      const end = frames.at(-1);
      const lastMove = events.filter(e => e.type.endsWith('move')).at(-1);
      if (!lift || !lastMove || !end || end.ms < duration) throw new Error('Incomplete release trace: ' + JSON.stringify({ lift, lastMove, end }));
      let lastMotionMs = 0;
      frames.forEach((p, i) => {
        const previous = frames[i - 1] ?? { x: 0, y: 0 };
        if (Math.hypot(p.x - previous.x, p.y - previous.y) > .05) lastMotionMs = p.ms;
      });
      return { frames, events: events.map(e => ({ ...e, ms: e.ms - lift.ms })),
        coastPx: end.x, firstFrameDx: frames[0].x, inputToLiftMs: lift.ms - lastMove.ms, lastMotionMs,
        travelPx: Math.max(...frames.map(p => Math.hypot(p.x, p.y))),
        furthestRightPx: Math.max(0, ...frames.map(p => p.x)) };
    } finally {
      await handle.dispose();
    }
  };
}
