import type { Map as LibreMap } from 'maplibre-gl';

/** Keep a touch used to stop inertia out of MapLibre's tap recognizers.
 * Restore them after the gesture ends, so the next tap starts a fresh sequence. */
export function bindBrakeTap(map: LibreMap) {
  let restore: (() => void) | undefined;
  let afterCatch = false, suppressDoubleClick = false;
  let restoreTimer: ReturnType<typeof setTimeout> | undefined;
  let doubleTimer: ReturnType<typeof setTimeout> | undefined;
  const additionalTouch = (event: TouchEvent) => {
    // Restore before MapLibre sees the second contact, so it can initialize a pinch.
    if (event.touches.length > 1) restore?.();
  };
  const doubleClick = (event: MouseEvent) => {
    if (!suppressDoubleClick) return;
    suppressDoubleClick = false; event.preventDefault(); event.stopImmediatePropagation();
  };
  const finish = (event: TouchEvent) => {
    if (event.touches.length) return;
    const pending = restore;
    // MapLibre must observe the end while its recognizers are disabled.
    if (pending) {
      clearTimeout(restoreTimer);
      restoreTimer = setTimeout(() => { if (restore === pending) pending(); }, 0);
    }
  };
  const catchTouch = (event: PointerEvent) => {
    if (event.pointerType !== 'touch' || restore) return;
    const doubleZoom = map.doubleClickZoom.isEnabled();
    const touchZoom = map.touchZoomRotate.isEnabled();
    if (doubleZoom) map.doubleClickZoom.disable();
    if (touchZoom) map.touchZoomRotate.disable();
    restore = () => {
      restore = undefined;
      if (doubleZoom) map.doubleClickZoom.enable();
      if (touchZoom) map.touchZoomRotate.enable();
    };
  };
  map.getCanvas().addEventListener('dblclick', doubleClick, true);
  document.addEventListener('touchstart', additionalTouch, true);
  document.addEventListener('touchend', finish, true);
  document.addEventListener('touchcancel', finish, true);
  return {
    catchTouch,
    caughtClick: () => { afterCatch = true; },
    allowClick: (event: MouseEvent) => {
      const allowed = afterCatch;
      afterCatch = false;
      suppressDoubleClick = allowed && event.detail > 1;
      clearTimeout(doubleTimer);
      if (suppressDoubleClick) doubleTimer = setTimeout(() => { suppressDoubleClick = false; }, 0);
      return allowed;
    },
    remove: () => {
      map.getCanvas().removeEventListener('dblclick', doubleClick, true);
      document.removeEventListener('touchstart', additionalTouch, true);
      document.removeEventListener('touchend', finish, true);
      document.removeEventListener('touchcancel', finish, true);
      clearTimeout(restoreTimer); clearTimeout(doubleTimer);
      restore?.();
    },
  };
}
