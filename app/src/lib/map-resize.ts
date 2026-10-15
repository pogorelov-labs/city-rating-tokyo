import type { Map } from 'leaflet';

/** Leaflet tracks window resize, but flex layout changes need their own signal. */
export function observeMapContainer(map: Pick<Map, 'getContainer' | 'invalidateSize'>) {
  const container = map.getContainer();
  let width = -1;
  let height = -1;
  let active = true;
  const resize = () => {
    if (!active) return;
    const nextWidth = container.clientWidth;
    const nextHeight = container.clientHeight;
    if (!nextWidth || !nextHeight || (nextWidth === width && nextHeight === height)) return;
    // Set before invalidation: tile/overlay updates must not cause a resize loop.
    width = nextWidth;
    height = nextHeight;
    map.invalidateSize({ animate: false, pan: true, debounceMoveend: true });
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  resize();
  return () => {
    active = false;
    observer.disconnect();
  };
}
