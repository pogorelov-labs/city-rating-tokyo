import type { LngLatBoundsLike, Map as LibreMap } from 'maplibre-gl';
import geometry from '@/data/bangkok/geometry.json';
import { smoothOverride } from '@/lib/map-motion';

type LatLng = [number, number];
type Shape = { bbox: [LatLng, LatLng] };
const districts = geometry as unknown as Record<string, Shape>;

/** Use the published polygon bounds; this does not rebuild or upload geometry. */
export function districtBounds(key: string): LngLatBoundsLike | undefined {
  const bbox = districts[key]?.bbox;
  if (!bbox) return;
  const [[south, west], [north, east]] = bbox;
  return [[west, south], [east, north]];
}

/** Fit in the workspace left after reserving the selected card and controls. */
export function districtPadding(width: number, height: number, touch: boolean, cardHeight = 0, toolbarBottom = 0) {
  const x = Math.max(0, width), y = Math.max(0, height);
  const marginX = Math.min(40, x * .1), marginY = Math.min(40, y * .1);
  const top = Math.min(y * .3, Math.max(marginY, toolbarBottom + 8));
  return touch
    ? { left: marginX, right: marginX, top, bottom: Math.min(Math.max(220, cardHeight + 24), Math.max(0, y - top - 40)) }
    : { left: Math.min(x * .45, 330), right: marginX, top: marginY, bottom: marginY };
}

/** MapLibre's bounds calculation is planar: deliberately flatten district fits. */
export function frameDistrict(map: LibreMap, key: string, touch: boolean, duration: number): boolean {
  const bounds = districtBounds(key); if (!bounds) return false;
  const container = map.getContainer();
  const workspace = container.closest('.map-workspace');
  const card = touch ? workspace?.querySelector<HTMLElement>('.map-touch-card') : null;
  const toolbar = touch ? workspace?.querySelector<HTMLElement>('[role="radiogroup"]') : null;
  const toolbarBottom = toolbar ? toolbar.getBoundingClientRect().bottom - container.getBoundingClientRect().top : 0;
  const target = map.cameraForBounds(bounds, { bearing: map.getBearing(), maxZoom: 13, absolutePadding: true,
    padding: districtPadding(container.clientWidth, container.clientHeight, touch, card?.offsetHeight ?? 0, toolbarBottom) });
  if (!target) return false;
  map.stop(); map.easeTo({ ...target, pitch: 0, duration, ...(smoothOverride() && { essential: true }) });
  return true;
}
