import type { Map as LibreMap, MapMovementEvent } from 'maplibre-gl';
import { bangkokCameraReduced, PAN_INERTIA, smoothOverride, subscribeBangkokMotion } from '@/lib/map-motion';

type Sample = { x: number; y: number; time: number };
const sampleWindow = 100;
function point(event: MapMovementEvent['originalEvent']): Sample | undefined {
  if (!event) return;
  if ('touches' in event) {
    if (event.touches.length > 1) return;
    const p = event.touches[0] ?? event.changedTouches[0];
    if (p) return { x: p.clientX, y: p.clientY, time: event.timeStamp };
  } else if ('clientX' in event) return { x: event.clientX, y: event.clientY, time: event.timeStamp };
}

/** Native MapLibre suppresses its release ease when the OS requests less
 * motion. Its constructor override is global to the library; do not use it.
 * Only for an explicit opt-in on such a device, hand a single screen-space
 * displacement to the map's own camera. Never run a parallel frame loop. */
export function bindBangkokPan(map: LibreMap) {
  let override = smoothOverride(), disposed = false;
  let singlePan = false, coasting = false, brakeTap = false;
  let samples: Sample[] | null = null;
  const cancel = () => { singlePan = false; samples = null; };
  const settled = () => { coasting = false; };
  const catchGlide = (event: PointerEvent) => {
    if (!event.isPrimary) return;
    brakeTap = coasting && map.isMoving();
    if (brakeTap) map.stop();
  };
  const move = (event: MapMovementEvent) => {
    if (!samples) return;
    const p = point(event.originalEvent);
    if (!p) { cancel(); return; }
    while (samples.length && p.time - samples[0].time > sampleWindow) samples.shift();
    if (samples.at(-1)?.time !== p.time) samples.push(p);
  };
  const start = (event: MapMovementEvent) => {
    singlePan = !!point(event.originalEvent) && !map.isZooming() && !map.isRotating();
    if (singlePan && override) { samples = []; move(event); }
  };
  const end = (event: MapMovementEvent) => {
    const recent = samples, wasSingle = singlePan; cancel();
    const input = event.originalEvent, released = point(input);
    if (!wasSingle || !released || !input || !['mouseup', 'touchend'].includes(input.type)) return;
    if ('touches' in input && input.touches.length !== 0) return;
    // For native inertia the final moveend follows the glide; without a glide
    // it fires immediately after dragend.
    if (!override) { coasting = true; return; }
    if (!recent) return;
    const first = recent.find(p => released.time - p.time <= sampleWindow);
    if (!first) return; // held still before release
    const dx = released.x - first.x, dy = released.y - first.y;
    const distance = Math.hypot(dx, dy), dt = released.time - first.time;
    if (dt <= 0 || distance < 2) return;
    const speed = Math.min(distance / dt * 1000, PAN_INERTIA.maxSpeed);
    const seconds = speed / PAN_INERTIA.deceleration;
    const box = map.getContainer();
    const travel = Math.min(speed * seconds / 2, box.clientHeight * .5, box.clientWidth * .75);
    if (travel < 1) return;
    // dragend precedes MapLibre's own moveend. Finish that transaction first.
    queueMicrotask(() => {
      if (disposed || !override || map.isMoving()) return;
      coasting = true;
      map.panBy([-dx / distance * travel, -dy / distance * travel], {
        duration: 2000 * travel / speed, easing: PAN_INERTIA.easing, essential: true,
      });
    });
  };
  const changed = () => { cancel(); override = smoothOverride(); if (bangkokCameraReduced()) map.stop(); };
  const unsubscribe = subscribeBangkokMotion(changed);
  const canvas = map.getCanvas();
  canvas.addEventListener('pointerdown', catchGlide, true);
  map.on('moveend', settled);
  map.on('dragstart', start); map.on('drag', move); map.on('dragend', end);
  map.on('zoomstart', cancel); map.on('rotatestart', cancel); map.on('pitchstart', cancel);
  return {
    consumeBrakeTap: () => { const caught = brakeTap; brakeTap = false; return caught; },
    remove: () => {
      disposed = true; cancel(); unsubscribe();
      canvas.removeEventListener('pointerdown', catchGlide, true);
      map.off('moveend', settled);
      map.off('dragstart', start); map.off('drag', move); map.off('dragend', end);
      map.off('zoomstart', cancel); map.off('rotatestart', cancel); map.off('pitchstart', cancel);
    },
  };
}
