export type PanSample = { x: number; y: number; time: number };
export const PAN_SAMPLE_WINDOW = 100;

/** Estimate from the most recent continuous direction, so a reversal does not
 * carry momentum from the earlier part of the gesture. Include release time to
 * account for a pause before lifting. */
export function panReleaseVelocity(samples: PanSample[], released: PanSample) {
  const recent = samples.filter(p => released.time - p.time <= PAN_SAMPLE_WINDOW && p.time <= released.time);
  const last = recent.at(-1);
  if (!last) return;
  const points = last.x === released.x && last.y === released.y ? recent : [...recent, released];
  let end = points.length - 1;
  while (end > 0 && points[end].x === points[end - 1].x && points[end].y === points[end - 1].y) end--;
  if (end === 0) return;
  const direction = { x: points[end].x - points[end - 1].x, y: points[end].y - points[end - 1].y };
  let start = end - 1;
  while (start > 0) {
    const dx = points[start].x - points[start - 1].x, dy = points[start].y - points[start - 1].y;
    if (dx * direction.x + dy * direction.y < 0) break;
    start--;
  }
  const dx = points[end].x - points[start].x, dy = points[end].y - points[start].y;
  const dt = released.time - points[start].time, distance = Math.hypot(dx, dy);
  if (dt <= 0 || distance < 2) return;
  return { dx, dy, distance, speed: distance / dt * 1000 };
}
