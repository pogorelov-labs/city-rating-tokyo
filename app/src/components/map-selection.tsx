'use client';

import { useEffect, useLayoutEffect } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { useAppStore } from '@/lib/store';

type LatLng = [number, number];
const MAX_FLY_ZOOM = 14;

/**
 * Smart flyTo: adapts zoom target and animation based on current map state.
 * - Already zoomed in (≥13): just pan, don't zoom further → cheaper.
 * - Far away / zoomed out (<11): short fly with easeLinearity tuning.
 * - Mid-range (11-13): standard fly to 14 with reduced duration.
 * Emits `flystart`/`flyend` custom classes on the container for CSS guards.
 */
export function MapSelectionPoint({
  lat,
  lng,
  onFlyStart,
  onFlyEnd,
}: {
  lat: number;
  lng: number;
  onFlyStart?: () => void;
  onFlyEnd?: () => void;
}) {
  const map = useMap();
  // useLayoutEffect so onFlyStart (→ setIsFlying(true)) fires BEFORE the
  // browser paints. This hides SVG overlays (halo, pulse) before the zoom
  // animation CSS-transforms them into giant circles.
  //
  // Deps: [map, lat, lng] only. onFlyStart/onFlyEnd are stable useCallback
  // refs but listing them would cause the effect to re-run when the parent
  // re-renders from setIsFlying(true) — the cleanup would detach the
  // moveend listener mid-animation, leaving .map-flying stuck forever.
  useLayoutEffect(() => {
    const currentZoom = map.getZoom();
    const currentCenter = map.getCenter();

    const dLat = Math.abs(currentCenter.lat - lat);
    const dLng = Math.abs(currentCenter.lng - lng);
    const roughDist = Math.sqrt(dLat * dLat + dLng * dLng);

    // Already looking at this station (within ~200m at zoom 14)
    if (roughDist < 0.003 && currentZoom >= 13) return;

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
      return () => clearTimeout(timer);
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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, lat, lng]);
  return null;
}

/** Fly (or pan) so the selection fits the viewport, mirroring the Tokyo
 *  `FlyToStation` contract: onFlyStart before paint, onFlyEnd after. */
export function MapSelectionBounds({
  bounds,
  bottomInset,
  onFlyStart,
  onFlyEnd,
}: {
  /** A district / station area bbox, or a 200 m cell (which then flies to
   *  MAX_FLY_ZOOM unless it is already in view at zoom ≥ 13). */
  bounds: [LatLng, LatLng];
  bottomInset: number;
  onFlyStart: () => void;
  onFlyEnd: () => void;
}) {
  const map = useMap();
  // Mount-only (the parent keys this component on the selection): the
  // callbacks are stable, and re-running on parent re-render would detach
  // the moveend listener mid-animation (same as Map.tsx FlyToStation).
  useLayoutEffect(() => {
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
    // Mark the flight first so any popup closed below knows it is not the
    // user's × (see the Popup `remove` handler).
    onFlyStart();
    map.closePopup();
    // The listener deliberately outlives this effect: if the selection is
    // cleared or changed mid-flight, the current animation still ends with a
    // moveend and must clear `isFlying` (otherwise labels / popup stay hidden).
    const done = () => {
      map.off('moveend', done);
      onFlyEnd();
    };
    map.on('moveend', done);
    map.flyToBounds(latLngBounds, {
      paddingTopLeft: padTL,
      paddingBottomRight: padBR,
      maxZoom: MAX_FLY_ZOOM,
      duration: 0.6,
      easeLinearity: 0.4,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
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
