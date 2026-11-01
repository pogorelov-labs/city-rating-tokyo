interface Point { x: number; y: number }
interface Box { left: number; top: number; right: number; bottom: number }

/** Prefer a card position that keeps the selected polygon's projected bounds clear. */
export function districtPopupOffset(size: Point, anchor: Point, width: number, height: number, outline: Box): Point {
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
  const minX = 18 + width / 2, maxX = size.x - 18 - width / 2;
  const minY = height + 38, maxY = size.y - 18;
  const original = { x: clamp(anchor.x, minX, maxX), y: clamp(anchor.y, minY, maxY) };
  const corners = [
    { x: minX, y: maxY }, { x: maxX, y: maxY },
    { x: minX, y: minY }, { x: maxX, y: minY },
  ];
  const overlap = (candidate: Point) => {
    const left = candidate.x - width / 2, right = candidate.x + width / 2;
    const top = candidate.y - height, bottom = candidate.y;
    const w = Math.max(0, Math.min(right, outline.right + 8) - Math.max(left, outline.left - 8));
    const h = Math.max(0, Math.min(bottom, outline.bottom + 8) - Math.max(top, outline.top - 8));
    return w * h;
  };
  if (overlap(original) === 0) return { x: original.x - anchor.x, y: original.y - anchor.y };
  let best = corners[0], bestOverlap = overlap(best);
  for (const candidate of corners.slice(1)) {
    const area = overlap(candidate);
    if (area < bestOverlap) { best = candidate; bestOverlap = area; }
  }
  return { x: best.x - anchor.x, y: best.y - anchor.y };
}
