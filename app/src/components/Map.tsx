'use client';

import { useEffect, useMemo, useDeferredValue, useRef, useState, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { MapStation, DEFAULT_FILTERS } from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
  scoreToColor,
  ColorDimension,
  applyDealbreakers,
} from '@/lib/scoring';
import { useAppStore } from '@/lib/store';
import { useIsTouch } from '@/lib/use-is-touch';
import Link from 'next/link';

/**
 * Smart flyTo: adapts zoom target and animation based on current map state.
 * - Already zoomed in (≥13): just pan, don't zoom further → cheaper.
 * - Far away / zoomed out (<11): short fly with easeLinearity tuning.
 * - Mid-range (11-13): standard fly to 14 with reduced duration.
 * Emits `flystart`/`flyend` custom classes on the container for CSS guards.
 */
function FlyToStation({
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
  useEffect(() => {
    const currentZoom = map.getZoom();
    const currentCenter = map.getCenter();

    // Distance in degrees (rough) to decide animation strategy
    const dLat = Math.abs(currentCenter.lat - lat);
    const dLng = Math.abs(currentCenter.lng - lng);
    const roughDist = Math.sqrt(dLat * dLat + dLng * dLng);

    // Already looking at this station (within ~200m at zoom 14)
    if (roughDist < 0.003 && currentZoom >= 13) return;

    // Close any open popup before flying — prevents the popup card from
    // flying around the screen during zoom animation (especially on mobile
    // where tap auto-opens the popup).
    map.closePopup();
    onFlyStart?.();

    // Smart zoom: don't force zoom 14 if already zoomed in
    const targetZoom = currentZoom >= 13 ? currentZoom : 14;

    // Very close pan — instant setView, no animation needed
    if (roughDist < 0.01 && Math.abs(currentZoom - targetZoom) < 1) {
      map.setView([lat, lng], targetZoom, { animate: true, duration: 0.25 });
      // Short timeout to match the brief pan
      setTimeout(() => onFlyEnd?.(), 300);
      return;
    }

    // Adaptive duration: shorter for close pans, longer for far jumps
    const duration = roughDist > 0.1 ? 0.6 : 0.4;

    map.flyTo([lat, lng], targetZoom, {
      duration,
      easeLinearity: 0.4, // spend less time at intermediate zooms
    });

    const handleMoveEnd = () => {
      map.off('moveend', handleMoveEnd);
      onFlyEnd?.();
    };
    map.on('moveend', handleMoveEnd);

    return () => {
      map.off('moveend', handleMoveEnd);
    };
  }, [map, lat, lng, onFlyStart, onFlyEnd]);
  return null;
}

/** Touch-only zoom buttons — bottom-right, above the compare panel / drawer */
function TouchZoomControls() {
  const map = useMap();
  return (
    <div className="leaflet-bottom leaflet-right" style={{ pointerEvents: 'none' }}>
      <div
        className="leaflet-control flex flex-col gap-1"
        style={{ pointerEvents: 'auto', marginBottom: 'calc(80px + env(safe-area-inset-bottom, 0px))', marginRight: 10 }}
      >
        <button
          onClick={() => map.zoomIn()}
          className="bg-white rounded-lg shadow-md border border-gray-200 w-10 h-10 flex items-center justify-center text-xl font-bold text-gray-700 active:bg-gray-100"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => map.zoomOut()}
          className="bg-white rounded-lg shadow-md border border-gray-200 w-10 h-10 flex items-center justify-center text-xl font-bold text-gray-700 active:bg-gray-100"
          aria-label="Zoom out"
        >
          −
        </button>
      </div>
    </div>
  );
}

/**
 * Prefetch tiles at zoom 14 around a lat/lng into browser cache.
 * Called on hover so tiles are warm by click time.
 * Uses `<link rel="prefetch">` for low-priority background fetching.
 */
const retinaTag = typeof window !== 'undefined' && window.devicePixelRatio > 1 ? '@2x' : '';
function prefetchTilesAroundStation(lat: number, lng: number) {
  const z = 14;
  const n = Math.pow(2, z);
  const tileX = Math.floor(((lng + 180) / 360) * n);
  const tileY = Math.floor(
    ((1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2) * n,
  );
  const subs = ['a', 'b', 'c', 'd'];
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const x = tileX + dx;
      const y = tileY + dy;
      const s = subs[(x + y) % subs.length];
      const url = `https://${s}.basemaps.cartocdn.com/light_all/${z}/${x}/${y}${retinaTag}.png`;
      if (!document.querySelector(`link[href="${url}"]`)) {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.as = 'image';
        link.href = url;
        document.head.appendChild(link);
      }
    }
  }
}

/**
 * Return a darker variant of an `rgb(r, g, b)` string produced by `scoreToColor`.
 * Used for the fallback gradient header so we can't accidentally produce invalid
 * CSS like `${rgbString}cc` (which would be silently dropped by the browser).
 */
function darkenRgb(rgb: string, factor = 0.7): string {
  const match = rgb.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if (!match) return rgb;
  const r = Math.round(Number(match[1]) * factor);
  const g = Math.round(Number(match[2]) * factor);
  const b = Math.round(Number(match[3]) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * SVG renderer for overlay markers (halo, top-5 pulse) that need CSS
 * className-based animations. The main 1493 markers use the Canvas
 * renderer (preferCanvas on MapContainer) for much cheaper flyTo animation.
 */
let svgOverlayRenderer: L.SVG | null = null;
function getSvgRenderer(): L.SVG {
  if (!svgOverlayRenderer) svgOverlayRenderer = L.svg();
  return svgOverlayRenderer;
}

/** ~+40 % radius when selected or hovered (list or map) — CRTKY-59. */
const HIGHLIGHT_RADIUS_FACTOR = 1.4;

/** Score-colored gradient fallback when no imagery is available. */
function GradientHeader({
  nameJp,
  score,
  color,
  height,
}: {
  nameJp: string;
  score: number | null;
  color: string;
  height: number;
}) {
  return (
    <div
      aria-hidden
      style={{
        width: '100%',
        height,
        backgroundImage:
          score !== null
            ? `linear-gradient(135deg, ${color}, ${darkenRgb(color)})`
            : 'linear-gradient(135deg, #e5e7eb, #9ca3af)',
        borderRadius: '6px 6px 0 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontFamily: 'serif',
        fontWeight: 700,
        fontSize: 26,
        letterSpacing: 2,
        textShadow: '0 1px 3px rgba(0,0,0,0.25)',
      }}
    >
      {nameJp}
    </div>
  );
}

/**
 * Tooltip header: three-tier image loading.
 * 1. LQIP base64 shown instantly (blurred, zero network)
 * 2. VPS thumbnail (320px, ~20 KB) crossfades in over LQIP
 * 3. Gradient fallback if no imagery at all
 *
 * The tooltip has a 400ms CSS show delay. If the thumbnail loads within
 * that window the user never sees the LQIP blur.
 */
function StationTooltipHero({
  slug,
  thumb,
  lqip,
  nameEn,
  nameJp,
  score,
  color,
}: {
  slug: string;
  thumb: string | undefined;
  lqip: string | undefined;
  nameEn: string;
  nameJp: string;
  score: number | null;
  color: string;
}) {
  const [thumbLoaded, setThumbLoaded] = useState(false);
  const [thumbFailed, setThumbFailed] = useState(false);

  // No imagery at all → compact gradient
  if (!thumb && !lqip) {
    return <GradientHeader nameJp={nameJp} score={score} color={color} height={60} />;
  }

  // Thumb failed → degrade to gradient (even if LQIP exists — permanent blur is worse)
  if (thumbFailed) {
    return <GradientHeader nameJp={nameJp} score={score} color={color} height={100} />;
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 100,
        overflow: 'hidden',
        borderRadius: '6px 6px 0 0',
      }}
    >
      {/* Base layer: LQIP (inline data URL, instant, blurred) */}
      {lqip && !thumbLoaded && (
        <img
          src={lqip}
          alt=""
          aria-hidden
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(20px)',
            transform: 'scale(1.1)',
          }}
        />
      )}
      {/* Top layer: sharp thumbnail, fades in over LQIP */}
      {thumb && !thumbFailed && (
        <img
          src={thumb}
          alt={nameEn}
          onLoad={() => setThumbLoaded(true)}
          onError={() => {
            setThumbFailed(true);
            window.umami?.track('error', {
              category: 'image',
              station: slug,
              context: 'tooltip',
            });
          }}
          style={{
            position: lqip ? 'absolute' : 'relative',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: thumbLoaded ? 1 : 0,
            transition: 'opacity 200ms ease-in',
          }}
        />
      )}
    </div>
  );
}

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

export default function MapView({ stations, thumbnails = {}, snippets = {} }: MapViewProps) {
  const weights = useAppStore((s) => s.weights);
  const selectedStation = useAppStore((s) => s.selectedStation);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const hoveredStation = useAppStore((s) => s.hoveredStation);
  const setHoveredStation = useAppStore((s) => s.setHoveredStation);
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const compareStations = useAppStore((s) => s.compareStations);
  const addCompareStation = useAppStore((s) => s.addCompareStation);
  const removeCompareStation = useAppStore((s) => s.removeCompareStation);
  const filters = useAppStore((s) => s.filters);

  // Guard: hide SVG overlays (halo, top-5 pulse) during flyTo to prevent
  // dual-renderer desync — the SVG layer's coordinate transform lags behind
  // Canvas during zoom animation, causing a giant misplaced halo ring.
  const [isFlying, setIsFlying] = useState(false);
  const onFlyStart = useCallback(() => { setIsFlying(true); }, []);
  const onFlyEnd = useCallback(() => { setIsFlying(false); }, []);
  const hideFloodRisk = useAppStore((s) => s.hideFloodRisk);
  const hideHighSeismic = useAppStore((s) => s.hideHighSeismic);

  const isTouch = useIsTouch();

  // Touch radius bump — meets WCAG 44px minimum at zoom 12+
  const TOUCH_RADIUS_BUMP = 4;

  // Scoring 1493 stations on every drag frame is expensive. Use a deferred
  // copy of the weights so React can skip stale recomputes while the user
  // is still dragging. The slider UI itself (in FilterPanel) reads the live
  // value so the handle stays glued to the pointer.
  const deferredWeights = useDeferredValue(weights);

  // Delay clearing hover when the pointer leaves the circle so moving toward
  // the Leaflet tooltip (above the marker) does not flicker the highlight.
  const mapHoverClearRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    return () => clearTimeout(mapHoverClearRef.current);
  }, []);

  const scoredStations = useMemo(() => {
    return stations.map((s) => ({
      ...s,
      score: s.ratings ? calculateWeightedScore(s.ratings, deferredWeights) : null,
    }));
  }, [stations, deferredWeights]);

  // Percentile anchors for the diverging composite palette. Recomputed
  // as the user changes weights so the akane↔kon range always stretches
  // across the actual observed distribution, not a fixed 1-10.
  // Use deferredWeights so the (expensive) sort over 1493 scores stays
  // in lockstep with the deferred score map above — otherwise colors
  // would be computed against anchors that disagree with the scores
  // they color, producing a brief mid-drag flash.
  const compositeAnchors = useMemo(
    () => computeCompositeAnchors(stations, deferredWeights),
    [stations, deferredWeights],
  );

  // Dealbreaker filters: rent, commute, category mins, environment safety
  const visibleStations = useMemo(() => {
    const noFilters =
      !hideFloodRisk &&
      !hideHighSeismic &&
      filters.minRent <= DEFAULT_FILTERS.minRent &&
      filters.maxRent >= DEFAULT_FILTERS.maxRent &&
      filters.minCommute <= DEFAULT_FILTERS.minCommute &&
      filters.maxCommute >= DEFAULT_FILTERS.maxCommute &&
      Object.keys(filters.categoryMins).length === 0;
    if (noFilters) return scoredStations.map((s) => ({ ...s, rentUnknown: false }));
    return applyDealbreakers(scoredStations, filters, hideFloodRisk, hideHighSeismic);
  }, [scoredStations, filters, hideFloodRisk, hideHighSeismic]);

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
      center={[35.6762, 139.7503]}
      zoom={12}
      className="h-full w-full"
      zoomControl={false}
      attributionControl={false}
      preferCanvas
    >
      <TileLayer
        attribution=""
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      {flyTarget && (
        <FlyToStation
          lat={flyTarget.lat}
          lng={flyTarget.lng}
          onFlyStart={onFlyStart}
          onFlyEnd={onFlyEnd}
        />
      )}
      {isTouch && <TouchZoomControls />}
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
                clearTimeout(mapHoverClearRef.current);
                setHoveredStation(station.slug);
                // Prefetch thumbnail into browser cache during 400ms tooltip delay
                if (thumbEntry?.thumb) { const i = new Image(); i.src = thumbEntry.thumb; }
                // Prefetch zoom-14 tiles around this station so flyTo lands on warm cache
                prefetchTilesAroundStation(station.lat, station.lng);
              },
              mouseout: () => {
                mapHoverClearRef.current = setTimeout(() => {
                  const { hoveredStation: h, setHoveredStation: clear } = useAppStore.getState();
                  if (h === station.slug) clear(null);
                }, 150);
              },
            }}
          >
            {/* Rich hover tooltip — desktop only (touch users get enriched Popup) */}
            {!isTouch && (
              <Tooltip
                direction="top"
                offset={[0, -10]}
                opacity={1}
                className="station-tooltip"
              >
                <div style={{ width: 260 }}>
                  <StationTooltipHero
                    key={`${station.slug}-${thumbEntry?.thumb ?? ''}`}
                    slug={station.slug}
                    thumb={thumbEntry?.thumb}
                    lqip={thumbEntry?.lqip}
                    nameEn={station.name_en}
                    nameJp={station.name_jp}
                    score={score}
                    color={color}
                  />
                  <div style={{ padding: '8px 10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 14 }}>{station.name_en}</div>
                        <div style={{ color: '#6b7280', fontSize: 12 }}>{station.name_jp}</div>
                      </div>
                      {score !== null && (
                        <div style={{ fontWeight: 700, fontSize: 18, color: '#1e293b' }}>
                          {score.toFixed(1)}
                        </div>
                      )}
                    </div>
                    {snippet && (
                      <div style={{
                        fontSize: 11,
                        color: '#4b5563',
                        marginTop: 6,
                        lineHeight: 1.4,
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}>
                        {snippet}
                      </div>
                    )}
                    <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
                      {station.line_count} lines
                      {station.rent_1k && (
                        <> · ~¥{(station.rent_1k / 1000).toFixed(0)}k/mo</>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: '#2563eb', marginTop: 4 }}>
                      Click for details →
                    </div>
                  </div>
                </div>
              </Tooltip>
            )}

            {/* Click popup — enriched on touch with image + snippet */}
            <Popup autoPan={false}>
              <div className="min-w-[180px]">
                {/* Touch: show thumbnail header (same as desktop tooltip) */}
                {isTouch && (thumbEntry?.thumb || thumbEntry?.lqip) && (
                  <div style={{ margin: '-10px -12px 8px', overflow: 'hidden', borderRadius: '8px 8px 0 0' }}>
                    <StationTooltipHero
                      key={`popup-${station.slug}`}
                      slug={station.slug}
                      thumb={thumbEntry?.thumb}
                      lqip={thumbEntry?.lqip}
                      nameEn={station.name_en}
                      nameJp={station.name_jp}
                      score={score}
                      color={color}
                    />
                  </div>
                )}
                <div className="font-bold text-base">
                  {station.name_en}
                </div>
                <div className="text-gray-500 text-sm mb-1">
                  {station.name_jp}
                </div>
                {score !== null ? (
                  <>
                    <div className="text-lg font-bold text-slate-800">
                      {score.toFixed(1)} / 10
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      {station.line_count} lines
                      {station.rent_1k && (
                        <> · ~¥{(station.rent_1k / 1000).toFixed(0)}k/mo</>
                      )}
                    </div>
                    {/* Touch: show snippet in popup */}
                    {isTouch && snippet && (
                      <div className="text-xs text-gray-600 mb-2 line-clamp-3 leading-relaxed">
                        {snippet}
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <Link
                        href={`/station/${station.slug}`}
                        className="text-blue-600 text-xs hover:underline"
                        data-umami-event="view-details"
                        data-umami-event-station={station.slug}
                      >
                        View details &rarr;
                      </Link>
                      {isCompared ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); removeCompareStation(station.slug); }}
                          className="text-red-500 text-xs hover:underline"
                        >
                          Remove compare
                        </button>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); addCompareStation(station.slug); }}
                          className="text-purple-600 text-xs hover:underline disabled:opacity-40"
                          disabled={compareStations.length >= 3}
                        >
                          + Compare
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-gray-400">
                    {station.line_count} lines &middot; Data coming soon
                  </div>
                )}
              </div>
            </Popup>
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
