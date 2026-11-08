'use client';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { ASOK_CAMERA, type BangkokRendererHandle } from '@/lib/bangkok-prototype';

export default function LeafletBridge() {
  const map = useMap();
  useEffect(() => {
    const initial = window.__bangkokInitialCamera ?? ASOK_CAMERA;
    map.setView([initial.lat, initial.lng], initial.zoom, { animate: false });
    let pending: { camera: typeof ASOK_CAMERA; duration: number } | undefined;
    let disposed = false, generation = 0;
    const cancelPending = () => { generation++; pending = undefined; map.off('zoomend', finishNativeZoom); };
    const apply = (camera: typeof ASOK_CAMERA, duration: number) => {
      if (duration) map.flyTo([camera.lat, camera.lng], camera.zoom, { duration: duration / 1000, easeLinearity: 0.4 });
      else map.setView([camera.lat, camera.lng], camera.zoom, { animate: false });
    };
    const finishNativeZoom = () => {
      map.off('zoomend', finishNativeZoom);
      const scheduled = generation;
      queueMicrotask(() => {
        if (disposed || scheduled !== generation || !pending) return;
        const request = pending; pending = undefined;
        apply(request.camera, request.duration);
      });
    };
    const container = map.getContainer();
    container.addEventListener('mousedown', cancelPending, true);
    container.addEventListener('touchstart', cancelPending, true);
    container.addEventListener('wheel', cancelPending, true);
    const handle: BangkokRendererHandle = {
      renderer: 'leaflet',
      ready: () => {
        const tiles = [...map.getContainer().querySelectorAll<HTMLImageElement>('img.leaflet-tile')];
        return !pending && tiles.length > 0 && tiles.every((img) => img.complete && img.naturalWidth > 0);
      },
      setCamera: (c, duration = 0) => {
        cancelPending();
        // Leaflet has no public way to interrupt an active native CSS zoom.
        // Apply only the latest lab request once that transition finishes.
        if (container.querySelector('.leaflet-zoom-anim')) {
          pending = { camera: c, duration };
          map.on('zoomend', finishNativeZoom);
        } else apply(c, duration);
      },
      getCamera: () => ({ lat: map.getCenter().lat, lng: map.getCenter().lng, zoom: map.getZoom(), pitch: 0, bearing: 0 }),
      project: (lng, lat) => { const p = map.latLngToContainerPoint([lat, lng]); return { x: p.x, y: p.y }; },
      stats: () => ({ paths: map.getContainer().querySelectorAll('path').length, tiles: map.getContainer().querySelectorAll('img.leaflet-tile').length }),
    };
    window.__bangkokRenderer = handle;
    return () => {
      disposed = true; cancelPending();
      container.removeEventListener('mousedown', cancelPending, true);
      container.removeEventListener('touchstart', cancelPending, true);
      container.removeEventListener('wheel', cancelPending, true);
      if (window.__bangkokRenderer === handle) delete window.__bangkokRenderer;
    };
  }, [map]);
  return null;
}
