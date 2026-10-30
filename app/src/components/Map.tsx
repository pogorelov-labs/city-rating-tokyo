'use client';

import { useMemo, useRef, useState, useCallback } from 'react';
import {
  AttributionControl,
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { MapStation } from '@/lib/types';
import {
  compositeToColor,
  scoreToColor,
  ColorDimension,
} from '@/lib/scoring';
import { useScoredAreas } from '@/lib/scoring-react';
import { useAppStore, useCityState, useCityActions } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import CompactAreaCard from './area/CompactAreaCard';
import LeafletAreaCard from './area/LeafletAreaCard';
import { useIsTouch } from '@/lib/use-is-touch';
import { useDelayedHover } from '@/lib/use-delayed-hover';
import { BASEMAP, tileUrl } from '@/lib/basemap';
import { MapContainerResize, TouchZoomControls, getSvgRenderer } from './map-shared';
import { MapSelectionPoint, MapDeselect } from './map-selection';

/**
 * Prefetch tiles at zoom 14 around a lat/lng into browser cache.
 * Called on hover so tiles are warm by click time.
 *
 * Uses `new Image()`, not `<link rel="prefetch">`: prefetch requests fall under
 * the CSP's `default-src 'self'`, so the browser refused every one of them —
 * image loads fall under `img-src`, which allows the tile host. Skipped when the
 * provider's terms do not allow prefetching (OSM fallback, see lib/basemap.ts).
 */
const prefetchedTiles = new Set<string>();
function prefetchTilesAroundStation(lat: number, lng: number) {
  if (!BASEMAP.prefetch) return;
  const z = 14;
  const n = Math.pow(2, z);
  const tileX = Math.floor(((lng + 180) / 360) * n);
  const tileY = Math.floor(
    ((1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2) * n,
  );
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const url = tileUrl(BASEMAP, z, tileX + dx, tileY + dy);
      if (!prefetchedTiles.has(url)) {
        prefetchedTiles.add(url);
        new Image().src = url;
      }
    }
  }
}

/** ~+40 % radius when selected or hovered (list or map) — CRTKY-59. */
const HIGHLIGHT_RADIUS_FACTOR = 1.4;

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

export default function MapView({ stations, thumbnails = {}, snippets = {} }: MapViewProps) {
  const city = useCity();
  const selectedStation = useCityState((s) => s.selectedStation);
  const hoveredStation = useCityState((s) => s.hoveredStation);
  const { setSelectedStation, setHoveredStation, addCompareStation, removeCompareStation } = useCityActions();
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const compareStations = useCityState((s) => s.compareStations);

  // Guard: hide SVG overlays (halo, top-5 pulse) during flyTo to prevent
  // dual-renderer desync — the SVG layer's coordinate transform lags behind
  // Canvas during zoom animation, causing a giant misplaced halo ring.
  // isFlying is in the store (not local state) so MobileStationCard can read it.
  const isFlying = useAppStore((s) => s.isFlying);
  const setIsFlying = useAppStore((s) => s.setIsFlying);
  const selectedMarkerRef = useRef<L.CircleMarker | null>(null);
  // Tracks which station's popup is currently open, so we can suppress the
  // tooltip on that same marker (avoids tooltip+popup overlap on one target).
  const [openPopupSlug, setOpenPopupSlug] = useState<string | null>(null);
  const onFlyStart = useCallback(() => { setIsFlying(true); }, [setIsFlying]);
  const onFlyCancel = useCallback(() => { setIsFlying(false); }, [setIsFlying]);
  const onFlyEnd = useCallback(() => {
    setIsFlying(false);
    // Auto-open popup after flyTo lands (desktop only — touch has no bound popup).
    // 50ms delay lets the canvas opacity fade-in complete before the popup renders.
    setTimeout(() => { selectedMarkerRef.current?.openPopup(); }, 50);
  }, [setIsFlying]);
  const isTouch = useIsTouch();

  // Touch radius bump — meets WCAG 44px minimum at zoom 12+
  const TOUCH_RADIUS_BUMP = 4;

  const { scored: scoredStations, anchors: compositeAnchors, passing: visibleStations, deferredWeights } = useScoredAreas(stations, 'primary');

  // Delay clearing hover when the pointer leaves the circle so moving toward
  // the Leaflet tooltip (above the marker) does not flicker the highlight.
  const hoverClear = useDelayedHover();

  // Sort ascending by score so high-rated stations paint on top (SVG paint order = DOM order).
  // Also used (reversed) for top-5 pulse — one sort instead of two.
  const sortedForRender = useMemo(
    () => [...visibleStations].sort((a, b) => (a.score ?? 0) - (b.score ?? 0)),
    [visibleStations],
  );

  // Top-5 ranked slugs for subtle pulse effect on map
  const top5Slugs = useMemo(() => {
    const withScore = sortedForRender.filter((s) => s.score !== null);
    return new Set(withScore.slice(-5).map((s) => s.slug));
  }, [sortedForRender]);

  const flyTarget = useMemo(() => {
    if (!selectedStation) return null;
    return scoredStations.find((s) => s.slug === selectedStation);
  }, [selectedStation, scoredStations]);

  // Station to highlight with halo: selected (from click/search) or hovered (from list)
  const highlightedSlug = selectedStation || hoveredStation;
  const highlightedStation = useMemo(() => {
    if (!highlightedSlug) return null;
    return scoredStations.find((s) => s.slug === highlightedSlug);
  }, [highlightedSlug, scoredStations]);

  return (
    <MapContainer
      center={city.map.center}
      zoom={city.map.zoom}
      className="h-full w-full"
      zoomControl={false}
      attributionControl={false}
      preferCanvas
    >
      <MapContainerResize />
      <TileLayer attribution={BASEMAP.attribution} url={BASEMAP.url} />
      {/* The tile providers' terms require their attribution on the map. */}
      <AttributionControl position="bottomright" prefix={false} />
      {flyTarget && (
        <MapSelectionPoint
          lat={flyTarget.lat}
          lng={flyTarget.lng}
          onFlyStart={onFlyStart}
          onFlyEnd={onFlyEnd}
          onFlyCancel={onFlyCancel}
        />
      )}
      {isTouch && <TouchZoomControls />}
      <MapDeselect onClear={() => setSelectedStation(null)} clickClears escapeClears />
      {sortedForRender.map((station) => {
        const score = station.score;
        const thumbEntry = thumbnails[station.slug];
        const snippet = snippets[station.slug];

        // Heatmap mode: color by selected dimension
        let displayValue: number | null = null;
        if (heatmapMode && station.ratings) {
          displayValue = heatmapDimension === 'composite'
            ? score
            : (station.ratings as unknown as Record<string, number>)[heatmapDimension] ?? null;
        }

        const color = heatmapMode
          ? (displayValue !== null
              ? scoreToColor(displayValue, heatmapDimension as ColorDimension)
              : '#9CA3AF')
          : (score !== null ? compositeToColor(score, compositeAnchors) : '#9CA3AF');
        const baseRadius = heatmapMode
          ? (displayValue !== null ? 14 + displayValue * 1.2 : 0)
          : (score !== null ? 6 + score * 0.5 : 5);
        const radius = isTouch ? baseRadius + TOUCH_RADIUS_BUMP : baseRadius;

        if (heatmapMode && displayValue === null) return null;

        const isCompared = compareStations.includes(station.slug);
        const isSelected = station.slug === selectedStation;
        const isHovered = station.slug === hoveredStation;
        const isHighlighted = isSelected || isHovered;

        // Selected/hovered stations: ~+40 % radius (CRTKY-59), bolder stroke
        const effectiveRadius = isHighlighted ? radius * HIGHLIGHT_RADIUS_FACTOR : radius;
        const strokeColor = isSelected
          ? '#1d4ed8'
          : isHovered
            ? '#2563eb'
            : isCompared
              ? '#7c3aed'
              : heatmapMode
                ? color
                : '#374151';
        const strokeWeight = isSelected
          ? 3.5
          : isHovered
            ? 2.5
            : isCompared
              ? 3
              : heatmapMode
                ? 0
                : (station.rentUnknown ? 0.5 : 1);

        return (
          <CircleMarker
            key={station.slug}
            ref={station.slug === selectedStation ? selectedMarkerRef : undefined}
            center={[station.lat, station.lng]}
            radius={effectiveRadius}
            pathOptions={{
              fillColor: color,
              color: strokeColor,
              weight: strokeWeight,
              opacity: heatmapMode && !isHighlighted && !isCompared ? 0 : (station.rentUnknown && !isHighlighted && !isCompared ? 0.3 : 0.9),
              fillOpacity: isHighlighted ? 1 : (heatmapMode ? 0.45 : (station.rentUnknown ? 0.35 : 0.85)),
            }}
            eventHandlers={{
              click: () => {
                setSelectedStation(station.slug);
                window.umami?.track('map-click', { station: station.slug });
              },
              mouseover: () => {
                hoverClear.cancel();
                setHoveredStation(station.slug);
                // Prefetch thumbnail into browser cache during 400ms tooltip delay
                if (thumbEntry?.thumb) { const i = new Image(); i.src = thumbEntry.thumb; }
                // Prefetch zoom-14 tiles around this station so flyTo lands on warm cache
                prefetchTilesAroundStation(station.lat, station.lng);
              },
              mouseout: () => {
                hoverClear.schedule(() => {
                  if (useAppStore.getState().cities[city.id].hoveredStation === station.slug) {
                    setHoveredStation(null);
                  }
                });
              },
            }}
          >
            {/* Rich hover tooltip — desktop only, suppressed when this marker's popup is open */}
            {!isTouch && openPopupSlug !== station.slug && (
              <Tooltip
                direction="top"
                offset={[0, -10]}
                opacity={1}
                className="station-tooltip"
              >
                <CompactAreaCard area={station} city={city.id} score={score} weights={deferredWeights}
                  thumbnail={thumbEntry} snippet={snippet} variant="hover" />
              </Tooltip>
            )}

            {/* Click popup — desktop only. Touch uses MobileStationCard (bottom-docked). */}
            {!isTouch && (
            <Popup
              className="area-guide-popup" autoPan closeButton={false} maxHeight={440} minWidth={280} maxWidth={340} autoPanPadding={[18, 18]}
              eventHandlers={{
                add: () => setOpenPopupSlug(station.slug),
                remove: () => setOpenPopupSlug((prev) => (prev === station.slug ? null : prev)),
              }}
            >
              <LeafletAreaCard area={station} city={city.id} score={score} weights={deferredWeights}
                thumbnail={thumbEntry} snippet={snippet} isCompared={isCompared} compareFull={compareStations.length >= 3}
                onCompare={() => addCompareStation(station.slug)} onUncompare={() => removeCompareStation(station.slug)} />
            </Popup>
            )}
          </CircleMarker>
        );
      })}
      {/* Pulsating halo ring under the currently selected/hovered station.
          `className` must be a top-level prop — react-leaflet forwards top-level
          props to Leaflet's CircleMarker constructor, but className inside
          `pathOptions` gets dropped by Leaflet's setStyle() which only updates
          stroke/fill attributes. With className set at the constructor level,
          Leaflet's _initPath applies it to the SVG path and the CSS keyframes
          animation can run.
          `renderer={getSvgRenderer()}` forces these onto an SVG layer so CSS
          animations work even though the map uses preferCanvas for the main
          1493 markers. */}
      {/* Top-5 ranked: barely visible pulse in their composite color.
          Hidden during flyTo to avoid SVG/Canvas renderer desync. */}
      {!heatmapMode && !isFlying && visibleStations
        .filter((s) => top5Slugs.has(s.slug) && s.slug !== highlightedSlug)
        .map((s) => {
          const c = s.score !== null ? compositeToColor(s.score, compositeAnchors) : '#374151';
          return (
            <CircleMarker
              key={`top5-${s.slug}`}
              center={[s.lat, s.lng]}
              radius={14}
              interactive={false}
              className="top-ranked-pulse"
              renderer={getSvgRenderer()}
              pathOptions={{
                color: c,
                weight: 1,
                fillColor: c,
                fillOpacity: 0.05,
              }}
            />
          );
        })}
      {highlightedStation && !isFlying && (
        <CircleMarker
          key={`halo-${highlightedStation.slug}`}
          center={[highlightedStation.lat, highlightedStation.lng]}
          radius={18}
          interactive={false}
          renderer={getSvgRenderer()}
          className="station-halo"
          pathOptions={{
            color: '#2563eb',
            weight: 2,
            fillColor: '#2563eb',
            fillOpacity: 0.15,
          }}
        />
      )}
    </MapContainer>
  );
}
