import type L from 'leaflet';

/** Keep button presses relative to the requested destination while a flight runs. */
export function installSmoothZoom(map: L.Map) {
  let target: number | undefined;
  let starting = false;
  const clear = () => { if (!starting) target = undefined; };
  const container = map.getContainer();
  const gesture = (event: Event) => {
    if (!(event.target instanceof Element) || !event.target.closest('.leaflet-control')) clear();
  };
  map.on('movestart moveend', clear);
  container.addEventListener('touchstart', gesture, true);
  container.addEventListener('mousedown', gesture, true);
  container.addEventListener('wheel', gesture, true);
  return {
    step(delta: number) {
      target = Math.max(map.getMinZoom(), Math.min(map.getMaxZoom(), (target ?? map.getZoom()) + delta));
      starting = true;
      try { map.flyTo(map.getCenter(), target, { animate: true, duration: .22 }); }
      finally { starting = false; }
    },
    clear,
    dispose() {
      map.off('movestart moveend', clear);
      container.removeEventListener('touchstart', gesture, true);
      container.removeEventListener('mousedown', gesture, true);
      container.removeEventListener('wheel', gesture, true);
      target = undefined;
    },
  };
}

/** A released drag owns its coast until Leaflet emits moveend. */
export function installCoastBrake(map: L.Map) {
  const container = map.getContainer();
  let releasedDrag = false;
  let touchBrake = false;
  let mouseBrake = false;
  let suppressMouseClick = false;
  let startX = 0, startY = 0;
  let pendingFrame = 0;
  let cancelScheduled = false;
  let clearClickTimer: ReturnType<typeof setTimeout> | undefined;
  const onDragEnd = () => { releasedDrag = true; };
  const onMoveEnd = () => { releasedDrag = false; };
  map.on('dragend', onDragEnd);
  map.on('moveend', onMoveEnd);
  const surface = (event: Event) => !(event.target instanceof Element && event.target.closest('.leaflet-control'));
  const stop = () => {
    if (pendingFrame) cancelAnimationFrame(pendingFrame);
    cancelScheduled = true;
    map.stop();
    // Leaflet schedules inertia on the next animation frame after dragend.
    // A contact in that small gap must stop the newly scheduled pan too.
    pendingFrame = requestAnimationFrame(() => { pendingFrame = 0; if (cancelScheduled) map.stop(); cancelScheduled = false; });
  };
  const touchDown = (event: TouchEvent) => {
    if (!releasedDrag || event.touches.length !== 1 || !surface(event)) return;
    touchBrake = true;
    startX = event.touches[0].clientX; startY = event.touches[0].clientY;
    stop();
  };
  const touchMove = (event: TouchEvent) => {
    if (!touchBrake) return;
    const touch = event.touches[0];
    if (!touch || event.touches.length !== 1 || Math.hypot(touch.clientX - startX, touch.clientY - startY) > 3) { touchBrake = false; cancelScheduled = false; }
  };
  const touchEnd = (event: TouchEvent) => {
    if (touchBrake && event.cancelable) event.preventDefault();
    touchBrake = false;
  };
  const mouseDown = (event: MouseEvent) => {
    if (!releasedDrag || event.button !== 0 || !surface(event) || (event as MouseEvent & { sourceCapabilities?: { firesTouchEvents?: boolean } }).sourceCapabilities?.firesTouchEvents) return;
    mouseBrake = true;
    startX = event.clientX; startY = event.clientY;
    stop();
  };
  const mouseMove = (event: MouseEvent) => {
    if (mouseBrake && Math.hypot(event.clientX - startX, event.clientY - startY) > 3) { mouseBrake = false; cancelScheduled = false; }
  };
  const mouseUp = () => {
    if (!mouseBrake) return;
    mouseBrake = false;
    suppressMouseClick = true;
    clearTimeout(clearClickTimer);
    clearClickTimer = setTimeout(() => { suppressMouseClick = false; }, 0);
  };
  const click = (event: MouseEvent) => {
    if (!suppressMouseClick) return;
    suppressMouseClick = false;
    event.preventDefault(); event.stopImmediatePropagation();
  };
  container.addEventListener('touchstart', touchDown, { capture: true, passive: true });
  container.addEventListener('touchmove', touchMove, { capture: true, passive: true });
  container.addEventListener('touchend', touchEnd, { capture: true, passive: false });
  container.addEventListener('touchcancel', touchEnd, { capture: true, passive: false });
  container.addEventListener('mousedown', mouseDown, true);
  document.addEventListener('mousemove', mouseMove, true);
  document.addEventListener('mouseup', mouseUp, true);
  container.addEventListener('click', click, true);
  return () => {
    map.off('dragend', onDragEnd); map.off('moveend', onMoveEnd);
    if (pendingFrame) cancelAnimationFrame(pendingFrame);
    clearTimeout(clearClickTimer);
    container.removeEventListener('touchstart', touchDown, true);
    container.removeEventListener('touchmove', touchMove, true);
    container.removeEventListener('touchend', touchEnd, true);
    container.removeEventListener('touchcancel', touchEnd, true);
    container.removeEventListener('mousedown', mouseDown, true);
    document.removeEventListener('mousemove', mouseMove, true);
    document.removeEventListener('mouseup', mouseUp, true);
    container.removeEventListener('click', click, true);
  };
}
