'use client';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { ASOK_CAMERA, type BangkokRendererHandle } from '@/lib/bangkok-prototype';

export default function LeafletBridge() {
  const map = useMap();
  useEffect(() => {
    const initial = window.__bangkokInitialCamera ?? ASOK_CAMERA;
    map.setView([initial.lat, initial.lng], initial.zoom, { animate: false });
    const handle: BangkokRendererHandle = {
      renderer: 'leaflet',
      ready: () => {
        const tiles = [...map.getContainer().querySelectorAll<HTMLImageElement>('img.leaflet-tile')];
        return tiles.length > 0 && tiles.every((img) => img.complete && img.naturalWidth > 0);
      },
      setCamera: (c, duration = 0) => {
        map.stop();
        if (duration) map.flyTo([c.lat, c.lng], c.zoom, { duration: duration / 1000, easeLinearity: 0.4 });
        else map.setView([c.lat, c.lng], c.zoom, { animate: false });
      },
      getCamera: () => ({ lat: map.getCenter().lat, lng: map.getCenter().lng, zoom: map.getZoom(), pitch: 0, bearing: 0 }),
      project: (lng, lat) => { const p = map.latLngToContainerPoint([lat, lng]); return { x: p.x, y: p.y }; },
      stats: () => ({ paths: map.getContainer().querySelectorAll('path').length, tiles: map.getContainer().querySelectorAll('img.leaflet-tile').length }),
    };
    window.__bangkokRenderer = handle;
    return () => { if (window.__bangkokRenderer === handle) delete window.__bangkokRenderer; };
  }, [map]);
  return null;
}
