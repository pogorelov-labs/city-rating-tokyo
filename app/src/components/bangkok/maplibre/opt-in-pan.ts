import type { Map as LibreMap, MapMovementEvent } from 'maplibre-gl';
import { bangkokCameraReduced, PAN_INERTIA, smoothOverride, subscribeBangkokMotion } from '@/lib/map-motion';

import { PAN_SAMPLE_WINDOW, panReleaseVelocity, type PanSample } from './pan-velocity';

type InputPoint = PanSample & { fingers: number; ids: string };
function point(event: MapMovementEvent['originalEvent']): InputPoint | undefined {
  if (!event) return;
  if ('touches' in event) {
    const touches = event.touches.length ? event.touches : event.changedTouches;
    if (touches.length < 1 || touches.length > 2) return;
    const points = Array.from(touches);
    return { x: points.reduce((sum, p) => sum + p.clientX, 0) / points.length,
      y: points.reduce((sum, p) => sum + p.clientY, 0) / points.length,
      time: event.timeStamp, fingers: points.length, ids: points.map(p => p.identifier).sort((a, b) => a - b).join(',') };
  }
  if ('clientX' in event) return { x: event.clientX, y: event.clientY, time: event.timeStamp, fingers: 0, ids: 'mouse' };
}

/** Native MapLibre suppresses its release ease when the OS requests less
 * motion. Its constructor override is global to the library; do not use it.
 * Only for an explicit opt-in on such a device, hand a single screen-space
 * displacement to the map's own camera. Never run a parallel frame loop. */
export function bindBangkokPan(map: LibreMap, onCatch?: (event: PointerEvent) => void) {
  let override = smoothOverride(), disposed = false;
  let panFingers: number | null = null, panIds: string | null = null, coasting = false, brakeTap = false;
  let samples: PanSample[] | null = null;
  let lifted: { points: Touch[]; time: number } | null = null;
  let touchRelease: InputPoint | null = null;
  const cancel = () => { panFingers = null; panIds = null; samples = null; lifted = null; touchRelease = null; };
  const settled = () => { coasting = false; };
  const catchGlide = (event: PointerEvent) => {
    if (!event.isPrimary) return;
    brakeTap = coasting && map.isMoving();
    if (brakeTap) { onCatch?.(event); map.stop(); }
  };
  const move = (event: MapMovementEvent) => {
    if (!samples) return;
    const p = point(event.originalEvent);
    if (!p || p.fingers !== panFingers || p.ids !== panIds) { cancel(); return; }
    while (samples.length && p.time - samples[0].time > PAN_SAMPLE_WINDOW) samples.shift();
    if (samples.at(-1)?.time !== p.time) samples.push(p);
  };
  const start = (event: MapMovementEvent) => {
    const p = point(event.originalEvent);
    panFingers = p && !map.isZooming() && !map.isRotating() ? p.fingers : null;
    panIds = panFingers !== null ? p!.ids : null;
    if (panFingers !== null && override) { samples = []; move(event); }
  };
  const end = (event: MapMovementEvent) => {
    const recent = samples, fingers = panFingers, ids = panIds, combinedRelease = touchRelease; cancel();
    const input = event.originalEvent, released = combinedRelease ?? point(input);
    if (fingers === null || !released || released.fingers !== fingers || released.ids !== ids || !input || !['mouseup', 'touchend'].includes(input.type)) return;
    if ('touches' in input && input.touches.length !== 0) return;
    // For native inertia the final moveend follows the glide; without a glide
    // it fires immediately after dragend.
    if (!override) { coasting = true; return; }
    if (!recent) return;
    const velocity = panReleaseVelocity(recent, released);
    if (!velocity) return;
    const { dx, dy, distance } = velocity;
    const speed = Math.min(velocity.speed, PAN_INERTIA.maxSpeed);
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
  const contactChange = (event: TouchEvent) => {
    if (panFingers === null || panFingers === 0) return;
    if (event.type === 'touchcancel') { cancel(); return; }
    if (event.type === 'touchstart' && (lifted || point(event)?.ids !== panIds)) { cancel(); return; }
    // Browsers can emit one touchend per finger even for a simultaneous lift.
    // Preserve the original centroid only if the remaining contact also ends
    // promptly, with no intervening movement or new contact.
    if (event.type === 'touchmove' && lifted) { cancel(); return; }
    if (event.type !== 'touchend') return;
    if (event.touches.length) {
      if (panFingers !== 2 || lifted) { cancel(); return; }
      lifted = { points: Array.from(event.changedTouches), time: event.timeStamp };
    } else if (lifted) {
      if (event.timeStamp - lifted.time > 80) { cancel(); return; }
      const points = [...lifted.points, ...Array.from(event.changedTouches)];
      const ids = points.map(p => p.identifier).sort((a, b) => a - b).join(',');
      if (points.length !== panFingers || ids !== panIds) { cancel(); return; }
      touchRelease = { x: points.reduce((sum, p) => sum + p.clientX, 0) / points.length,
        y: points.reduce((sum, p) => sum + p.clientY, 0) / points.length,
        time: event.timeStamp, fingers: points.length, ids };
    }
  };
  canvas.addEventListener('pointerdown', catchGlide, true);
  canvas.addEventListener('touchstart', contactChange, true);
  canvas.addEventListener('touchmove', contactChange, true);
  canvas.addEventListener('touchend', contactChange, true);
  canvas.addEventListener('touchcancel', contactChange, true);
  map.on('moveend', settled);
  map.on('dragstart', start); map.on('drag', move); map.on('dragend', end);
  map.on('zoomstart', cancel); map.on('rotatestart', cancel); map.on('pitchstart', cancel);
  return {
    consumeBrakeTap: () => { const caught = brakeTap; brakeTap = false; return caught; },
    remove: () => {
      disposed = true; cancel(); unsubscribe();
      canvas.removeEventListener('pointerdown', catchGlide, true);
      canvas.removeEventListener('touchstart', contactChange, true);
      canvas.removeEventListener('touchmove', contactChange, true);
      canvas.removeEventListener('touchend', contactChange, true);
      canvas.removeEventListener('touchcancel', contactChange, true);
      map.off('moveend', settled);
      map.off('dragstart', start); map.off('drag', move); map.off('dragend', end);
      map.off('zoomstart', cancel); map.off('rotatestart', cancel); map.off('pitchstart', cancel);
    },
  };
}
