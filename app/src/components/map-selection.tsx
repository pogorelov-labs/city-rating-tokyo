'use client';

import { useEffect, useLayoutEffect } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { useAppStore } from '@/lib/store';

type LatLng = [number, number];
const MAX_FLY_ZOOM = 14;
const pendingBoundsFlights = new WeakMap<L.Map, () => void>();

type PointSelection = { kind: 'point'; lat: number; lng: number; onFlyStart?: () => void; onFlyEnd?: () => void; onFlyCancel?: () => void };
type BoundsSelection = { kind: 'bounds'; bounds: [LatLng, LatLng]; bottomInset: number; onFlyStart: () => void; onFlyEnd: () => void };

/** Share the selection lifecycle while retaining each city's flight strategy. */
export function useMapSelection(selection: PointSelection | BoundsSelection) {
  const map = useMap();
  const lat = selection.kind === 'point' ? selection.lat : undefined;
  const lng = selection.kind === 'point' ? selection.lng : undefined;
  const kind = selection.kind;
  useLayoutEffect(() => {
    if (selection.kind === 'point') {
      const { lat, lng, onFlyStart, onFlyEnd, onFlyCancel } = selection;
      const currentZoom = map.getZoom();
      const currentCenter = map.getCenter();

      const dLat = Math.abs(currentCenter.lat - lat);
      const dLng = Math.abs(currentCenter.lng - lng);
      const roughDist = Math.sqrt(dLat * dLat + dLng * dLng);

      // Already looking at this station (within ~200m at zoom 14)
      if (roughDist < 0.003 && currentZoom >= 13) {
        map.stop();
        onFlyEnd?.();
        return;
      }

      // Close any open popup before flying — prevents the popup card from
      // flying around the screen during zoom animation (mobile tap auto-opens).
      map.closePopup();
      onFlyStart?.();

      const targetZoom = currentZoom >= 13 ? currentZoom : 14;

      // Fade canvas markers during flyTo to hide CSS-scaling artifact.
      // Leaflet applies transform:scale(2^Δzoom) to the canvas during zoom
      // animation (by design, #6050/#6409). The .map-flying class sets
      // canvas opacity to 0 via CSS transition; tiles stay visible since
      // they're in a separate pane. Markers fade back in after moveend.
      const container = map.getContainer();
      const needsFade = Math.abs(currentZoom - targetZoom) >= 1;
      if (needsFade) container.classList.add('map-flying');

      // Very close pan — short animated setView
      if (roughDist < 0.01 && currentZoom === targetZoom) {
        map.setView([lat, lng], targetZoom, { animate: true, duration: 0.25 });
        const timer = setTimeout(() => {
          container.classList.remove('map-flying');
          onFlyEnd?.();
        }, 300);
        return () => { clearTimeout(timer); onFlyCancel?.(); };
      }

      // Adaptive duration: shorter for close pans, longer for far jumps
      const duration = roughDist > 0.1 ? 0.6 : 0.4;
      map.flyTo([lat, lng], targetZoom, {
        duration,
        easeLinearity: 0.4,
      });

      const handleMoveEnd = () => {
        map.off('moveend', handleMoveEnd);
        container.classList.remove('map-flying');
        onFlyEnd?.();
      };
      map.on('moveend', handleMoveEnd);

      return () => {
        map.off('moveend', handleMoveEnd);
        container.classList.remove('map-flying');
        onFlyCancel?.();
      };
    }
    const { bounds, bottomInset, onFlyStart, onFlyEnd } = selection;
    const latLngBounds = L.latLngBounds(bounds);
    const padTL = L.point(40, 40);
    const padBR = L.point(40, 40 + bottomInset);
    const target = Math.min(MAX_FLY_ZOOM, map.getBoundsZoom(latLngBounds, false, padTL.add(padBR)));
    const view = map.getBounds();
    // Already framed well enough: don't make the map jump. Not while another
    // flight is still animating, though — the map is about to leave this view.
    if (!useAppStore.getState().isFlying && view.contains(latLngBounds) && map.getZoom() >= target - 1) {
      onFlyEnd();
      return;
    }
    pendingBoundsFlights.get(map)?.();
    map.stop();
    // Mark the flight first so any popup closed below knows it is not the
    // user's × (see the Popup `remove` handler).
    onFlyStart();
    map.closePopup();
    // The listener deliberately outlives this effect: if the selection is
    // cleared or changed mid-flight, the current animation still ends with a
    // moveend and must clear `isFlying` (otherwise labels / popup stay hidden).
    const detach = () => {
      map.off('moveend', done);
      map.off('unload', done);
      if (pendingBoundsFlights.get(map) === detach) pendingBoundsFlights.delete(map);
    };
    const done = () => { detach(); onFlyEnd(); };
    pendingBoundsFlights.set(map, detach);
    map.on('moveend', done);
    map.on('unload', done);
    map.flyToBounds(latLngBounds, {
      paddingTopLeft: padTL,
      paddingBottomRight: padBR,
      maxZoom: MAX_FLY_ZOOM,
      duration: 0.6,
      easeLinearity: 0.4,
    });
    // The bounds component is keyed by selection. As before, callback changes
    // must not detach a flight listener or restart an in-progress animation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, kind, lat, lng]);
}

export function MapSelectionPoint(props: Omit<PointSelection, 'kind'>) {
  useMapSelection({ kind: 'point', ...props });
  return null;
}

export function MapSelectionBounds(props: Omit<BoundsSelection, 'kind'>) {
  useMapSelection({ kind: 'bounds', ...props });
  return null;
}

/** Dismiss a background selection without treating Leaflet controls as background. */
export function MapDeselect({ onClear, clickClears, escapeClears }: {
  onClear: () => void; clickClears: boolean; escapeClears: boolean;
}) {
  useMapEvents({
    click: (e) => {
      if (!clickClears) return;
      const target = e.originalEvent?.target as HTMLElement | null;
      if (!target?.closest('.leaflet-interactive, .leaflet-control')) onClear();
    },
  });
  useEffect(() => {
    if (!escapeClears) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClear(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClear, escapeClears]);
  return null;
}
