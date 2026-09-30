'use client';

import { useEffect, useLayoutEffect, useMemo, useDeferredValue, useRef, useState, useCallback } from 'react';
import {
  AttributionControl,
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation } from '@/lib/types';
import { stationDisplayName } from '@/lib/station-name';
import type { Locale } from '@/i18n/routing';
import {
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
  scoreToColor,
  ColorDimension,
  applyDealbreakers,
} from '@/lib/scoring';
import { useAppStore, useCityState, useCityActions } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { areaPath, formatRentShort, hasActiveFilters } from '@/lib/cities';
import { useIsTouch } from '@/lib/use-is-touch';
import { BASEMAP, tileUrl } from '@/lib/basemap';
import { Link } from '@/i18n/navigation';
import { TouchZoomControls, getSvgRenderer, StationTooltipHero } from './map-shared';

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
  // useLayoutEffect so onFlyStart (→ setIsFlying(true)) fires BEFORE the
  // browser paints. This hides SVG overlays (halo, pulse) before the zoom
  // animation CSS-transforms them into giant circles.
  //
  // Deps: [map, lat, lng] only. onFlyStart/onFlyEnd are stable useCallback
  // refs but listing them would cause the effect to re-run when the parent
  // re-renders from setIsFlying(true) — the cleanup would detach the
  // moveend listener mid-animation, leaving .map-flying stuck forever.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
  }, [map, lat, lng]);
  return null;
}

/**
 * Background-click dismiss: clicking the map (not a marker) clears the selected
 * station so the halo, popup, and MobileStationCard all vanish. The
 * `.leaflet-interactive` check filters out marker clicks — markers bubble a
 * click event to the map layer, but they are wrapped in this class by Leaflet.
 */
function MapClickHandler() {
  const { setSelectedStation } = useCityActions();
  useMapEvents({
    click: (e) => {
      const target = e.originalEvent?.target as HTMLElement | null;
      if (!target?.closest('.leaflet-interactive')) {
        setSelectedStation(null);
      }
    },
  });
  return null;
}

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
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const weights = useAppStore((s) => s.weights);
  const selectedStation = useCityState((s) => s.selectedStation);
  const hoveredStation = useCityState((s) => s.hoveredStation);
  const { setSelectedStation, setHoveredStation, addCompareStation, removeCompareStation } = useCityActions();
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const compareStations = useCityState((s) => s.compareStations);
  const filters = useCityState((s) => s.filters);

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
  const onFlyEnd = useCallback(() => {
    setIsFlying(false);
    // Auto-open popup after flyTo lands (desktop only — touch has no bound popup).
    // 50ms delay lets the canvas opacity fade-in complete before the popup renders.
    setTimeout(() => { selectedMarkerRef.current?.openPopup(); }, 50);
  }, [setIsFlying]);
  const hideFloodRisk = useCityState((s) => s.hideFloodRisk);
  const hideHighSeismic = useCityState((s) => s.hideHighSeismic);

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
  // Fast path when nothing is set. Uses the same `hasActiveFilters` check as
  // FilterPanel so the map and the match counter always agree (the old inline
  // check forgot `hasLiveCamera`, so that filter alone never hid a marker).
  const visibleStations = useMemo(() => {
    if (!hasActiveFilters(city.id, filters, { hideFloodRisk, hideHighSeismic })) {
      return scoredStations.map((s) => ({ ...s, rentUnknown: false }));
    }
    return applyDealbreakers(scoredStations, filters, hideFloodRisk, hideHighSeismic, city.defaultFilters);
  }, [scoredStations, filters, hideFloodRisk, hideHighSeismic, city]);

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
      <TileLayer attribution={BASEMAP.attribution} url={BASEMAP.url} />
      {/* The tile providers' terms require their attribution on the map. */}
      <AttributionControl position="bottomright" prefix={false} />
      {flyTarget && (
        <FlyToStation
          lat={flyTarget.lat}
          lng={flyTarget.lng}
          onFlyStart={onFlyStart}
          onFlyEnd={onFlyEnd}
        />
      )}
      {isTouch && <TouchZoomControls />}
      <MapClickHandler />
      {sortedForRender.map((station) => {
        const score = station.score;
        const thumbEntry = thumbnails[station.slug];
        // Snippets are Russian-only until CRTKY-109 provides multilingual descriptions
        const snippet = locale === 'ru' ? snippets[station.slug] : undefined;

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
                clearTimeout(mapHoverClearRef.current);
                setHoveredStation(station.slug);
                // Prefetch thumbnail into browser cache during 400ms tooltip delay
                if (thumbEntry?.thumb) { const i = new Image(); i.src = thumbEntry.thumb; }
                // Prefetch zoom-14 tiles around this station so flyTo lands on warm cache
                prefetchTilesAroundStation(station.lat, station.lng);
              },
              mouseout: () => {
                mapHoverClearRef.current = setTimeout(() => {
                  if (useAppStore.getState().cities[city.id].hoveredStation === station.slug) {
                    setHoveredStation(null);
                  }
                }, 150);
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
                <div style={{ width: 260 }}>
                  <StationTooltipHero
                    key={`${station.slug}-${thumbEntry?.thumb ?? ''}`}
                    slug={station.slug}
                    thumb={thumbEntry?.thumb}
                    lqip={thumbEntry?.lqip}
                    nameEn={stationDisplayName(station, locale).primary}
                    nameJp={stationDisplayName(station, locale).secondary}
                    score={score}
                    color={color}
                  />
                  <div style={{ padding: '8px 10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', gap: 5 }}>
                          <span>{stationDisplayName(station, locale).primary}</span>
                          {station.hasLiveCamera && (
                            <span
                              role="img"
                              aria-label={t('filter.hasLiveCamera')}
                              title={t('filter.hasLiveCamera')}
                              style={{ fontSize: 14, lineHeight: 1 }}
                            >
                              📹
                            </span>
                          )}
                        </div>
                        <div style={{ color: '#6b7280', fontSize: 12 }}>{stationDisplayName(station, locale).secondary}</div>
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
                      {t('filter.lines', { count: station.line_count })}
                      {station.rent_1k && (
                        <> · ~{formatRentShort(city.id, station.rent_1k)}/mo</>
                      )}
                    </div>
                  </div>
                </div>
              </Tooltip>
            )}

            {/* Click popup — desktop only. Touch uses MobileStationCard (bottom-docked). */}
            {!isTouch && (
            <Popup
              autoPan={false}
              eventHandlers={{
                add: () => setOpenPopupSlug(station.slug),
                remove: () => setOpenPopupSlug((prev) => (prev === station.slug ? null : prev)),
              }}
            >
              <div className="min-w-[180px]">
                {/* Thumbnail header — shown on all platforms now (click ≥ hover) */}
                {(thumbEntry?.thumb || thumbEntry?.lqip) && (
                  <div style={{ margin: '-10px -12px 8px', overflow: 'hidden', borderRadius: '8px 8px 0 0' }}>
                    <StationTooltipHero
                      key={`popup-${station.slug}`}
                      slug={station.slug}
                      thumb={thumbEntry?.thumb}
                      lqip={thumbEntry?.lqip}
                      nameEn={stationDisplayName(station, locale).primary}
                      nameJp={stationDisplayName(station, locale).secondary}
                      score={score}
                      color={color}
                    />
                  </div>
                )}
                <div className="font-bold text-base flex items-center gap-1.5">
                  <span>{stationDisplayName(station, locale).primary}</span>
                  {station.hasLiveCamera && (
                    <span
                      role="img"
                      aria-label={t('filter.hasLiveCamera')}
                      title={t('filter.hasLiveCamera')}
                      className="text-base leading-none"
                    >
                      📹
                    </span>
                  )}
                </div>
                <div className="text-gray-500 text-sm mb-1">
                  {stationDisplayName(station, locale).secondary}
                </div>
                {score !== null ? (
                  <>
                    <div className="text-lg font-bold text-slate-800">
                      {score.toFixed(1)} / 10
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      {t('filter.lines', { count: station.line_count })}
                      {station.rent_1k && (
                        <> · ~{formatRentShort(city.id, station.rent_1k)}/mo</>
                      )}
                    </div>
                    {/* Snippet: shown on all platforms for full click-context */}
                    {snippet && (
                      <div className="text-xs text-gray-600 mb-2 line-clamp-3 leading-relaxed">
                        {snippet}
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <Link
                        href={areaPath(city.id, station.slug)}
                        className="text-blue-600 text-xs hover:underline"
                        data-umami-event="view-details"
                        data-umami-event-station={station.slug}
                      >
                        {t('map.viewDetails')}
                      </Link>
                      {isCompared ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); removeCompareStation(station.slug); }}
                          className="text-red-500 text-xs hover:underline"
                        >
                          {t('map.removeCompare')}
                        </button>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); addCompareStation(station.slug); }}
                          className="text-purple-600 text-xs hover:underline disabled:opacity-40"
                          disabled={compareStations.length >= 3}
                        >
                          {t('map.compare')}
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-gray-400">
                    {t('filter.lines', { count: station.line_count })} &middot; {t('map.dataComingSoon')}
                  </div>
                )}
              </div>
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
