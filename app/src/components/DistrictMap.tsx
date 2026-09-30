'use client';

import { useCallback, useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
  AttributionControl,
  CircleMarker,
  MapContainer,
  Marker,
  Pane,
  Polygon,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useLocale, useTranslations } from 'next-intl';
import geometryData from '@/data/bangkok/geometry.json';
import railData from '@/data/bangkok/rail.json';
import type { MapStation, RailLine, RailStation, StationRatings } from '@/lib/types';
import type { Locale } from '@/i18n/routing';
import { Link } from '@/i18n/navigation';
import {
  applyDealbreakers,
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
  dealbreakerReasons,
  scoreToColor,
  type ColorDimension,
  type DealbreakerReason,
  type PercentileAnchors,
} from '@/lib/scoring';
import { useAppStore, useCityActions, useCityState } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { areaPath, formatRentShort } from '@/lib/cities';
import { stationDisplayName } from '@/lib/station-name';
import { useIsTouch } from '@/lib/use-is-touch';
import { StationTooltipHero, TouchZoomControls } from './map-shared';
import { BASEMAP } from '@/lib/basemap';

type LatLng = [number, number];
interface DistrictShape {
  polygons: LatLng[][][];
  bbox: [LatLng, LatLng];
  label: LatLng;
}
const GEOMETRY = geometryData as unknown as Record<string, DistrictShape>;
const RAIL = railData as unknown as { lines: (RailLine & { paths: LatLng[][] })[]; stations: RailStation[] };
const LINE_BY_ID = new Map(RAIL.lines.map((l) => [l.id, l]));

/** Fill of a district that fails the current dealbreakers. */
const FILTERED_FILL = '#E5E7EB';
const MAX_FLY_ZOOM = 14;

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

/** Fly (or pan) so the selected district fits the viewport, mirroring the
 *  Tokyo `FlyToStation` contract: onFlyStart before paint, onFlyEnd after. */
function FlyToDistrict({
  slug,
  bottomInset,
  onFlyStart,
  onFlyEnd,
}: {
  slug: string;
  bottomInset: number;
  onFlyStart: () => void;
  onFlyEnd: () => void;
}) {
  const map = useMap();
  // Deps: [map, slug] only — same reasoning as Map.tsx FlyToStation: the
  // callbacks are stable, and re-running on parent re-render would detach
  // the moveend listener mid-animation.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useLayoutEffect(() => {
    const shape = GEOMETRY[slug];
    if (!shape) return;
    const bounds = L.latLngBounds(shape.bbox);
    const padTL = L.point(40, 40);
    const padBR = L.point(40, 40 + bottomInset);
    const target = Math.min(MAX_FLY_ZOOM, map.getBoundsZoom(bounds, false, padTL.add(padBR)));
    const view = map.getBounds();
    // Already framed well enough: don't make the map jump. Not while another
    // flight is still animating, though — the map is about to leave this view.
    if (!useAppStore.getState().isFlying && view.contains(bounds) && map.getZoom() >= target - 1) {
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
    map.flyToBounds(bounds, {
      paddingTopLeft: padTL,
      paddingBottomRight: padBR,
      maxZoom: MAX_FLY_ZOOM,
      duration: 0.6,
      easeLinearity: 0.4,
    });
  }, [map, slug]);
  return null;
}

/** Phones: re-frame on the inner city once, before the first paint. */
function NarrowScreenFrame({ bounds }: { bounds?: [LatLng, LatLng] }) {
  const map = useMap();
  useLayoutEffect(() => {
    if (!bounds || map.getSize().x >= 640) return;
    // A deep link (?s=…) will fly to its district right after; framing first
    // keeps that fly short.
    map.fitBounds(bounds, { animate: false, padding: [8, 8] });
  }, [map, bounds]);
  return null;
}

function ZoomWatcher({ onZoom }: { onZoom: (z: number) => void }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => onZoom(map.getZoom()), [map, onZoom]);
  return null;
}

/** Click outside every district (sea, neighbouring provinces) clears the
 *  selection; Escape does the same from anywhere. */
function DeselectHandlers({ onClear }: { onClear: () => void }) {
  useMapEvents({
    click: (e) => {
      const target = e.originalEvent?.target as HTMLElement | null;
      if (!target?.closest('.leaflet-interactive')) onClear();
    },
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClear();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClear]);
  return null;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

/** Pixel size of a lat/lng box at a zoom (Web Mercator, fine at Bangkok's latitude). */
function boxPixels(bbox: [LatLng, LatLng], zoom: number): { w: number; h: number } {
  const world = 256 * 2 ** zoom;
  const w = ((bbox[1][1] - bbox[0][1]) / 360) * world;
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const h = ((merc(bbox[1][0]) - merc(bbox[0][0])) / (2 * Math.PI)) * world;
  return { w, h };
}

/** Rough rendered width of an 11 px semibold label: kana / kanji are about
 *  twice as wide as Latin or Cyrillic glyphs. */
function labelWidth(text: string): number {
  let w = 12;
  for (const ch of text) w += ch.charCodeAt(0) >= 0x2e80 ? 11 : 6.6;
  return w;
}

/** Map-label form of a name: the JA "区" (ward) suffix is implied on a map
 *  of districts and costs a full-width glyph in the densest part of the map. */
function mapLabel(name: string, locale: Locale): string {
  return locale === 'ja' ? name.replace(/区$/, '') : name;
}

function reasonText(t: ReturnType<typeof useTranslations>, r: DealbreakerReason): string {
  if (r.kind === 'category') {
    return t('map.reasonCategory', { category: t(`shortLabels.${r.key}`), min: r.min });
  }
  return t(`map.reason_${r.kind}`);
}

function Legend({
  anchors,
  heatmapMode,
  heatmapDimension,
  filtersActive,
}: {
  anchors: PercentileAnchors;
  heatmapMode: boolean;
  heatmapDimension: string;
  filtersActive: boolean;
}) {
  const t = useTranslations();
  const dim = heatmapMode && heatmapDimension !== 'composite' ? (heatmapDimension as ColorDimension) : null;
  const stops = dim
    ? [1, 5.5, 10].map((v) => scoreToColor(v, dim))
    : [anchors.p5, (anchors.p5 + anchors.p50) / 2, anchors.p50, (anchors.p50 + anchors.p95) / 2, anchors.p95].map((v) =>
        compositeToColor(v, anchors),
      );
  const title = dim ? t(`ratings.${dim}`) : t('map.compositeScore');
  return (
    <div className="hidden md:block absolute bottom-6 left-3 z-[900] bg-white/95 border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-[10px] text-gray-600 w-48 pointer-events-none">
      <div className="font-semibold text-gray-700 mb-1 truncate">{title}</div>
      <div className="h-2 rounded-full" style={{ backgroundImage: `linear-gradient(90deg, ${stops.join(', ')})` }} />
      <div className="flex justify-between mt-0.5 tabular-nums">
        <span>{dim ? '1' : anchors.p5.toFixed(1)}</span>
        {!dim && <span>{anchors.p50.toFixed(1)}</span>}
        <span>{dim ? '10' : anchors.p95.toFixed(1)}</span>
      </div>
      <div className="mt-1 text-gray-500 leading-snug">{t('map.legendDistricts')}</div>
      {filtersActive && (
        <div className="mt-1 flex items-center gap-1.5">
          <span className="inline-block w-3 h-2 rounded-sm border border-gray-300" style={{ backgroundColor: FILTERED_FILL }} />
          {t('map.legendFilteredOut')}
        </div>
      )}
    </div>
  );
}

export default function DistrictMap({ stations: districts, thumbnails = {}, snippets = {} }: MapViewProps) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const isTouch = useIsTouch();

  const weights = useAppStore((s) => s.weights);
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const showRail = useAppStore((s) => s.showRailOverlay);
  const isFlying = useAppStore((s) => s.isFlying);
  const setIsFlying = useAppStore((s) => s.setIsFlying);
  const selected = useCityState((s) => s.selectedStation);
  const hovered = useCityState((s) => s.hoveredStation);
  const compareStations = useCityState((s) => s.compareStations);
  const filters = useCityState((s) => s.filters);
  const hideFloodRisk = useCityState((s) => s.hideFloodRisk);
  const hideHighSeismic = useCityState((s) => s.hideHighSeismic);
  const { setSelectedStation, setHoveredStation, addCompareStation, removeCompareStation } = useCityActions();

  const [zoom, setZoom] = useState(city.map.zoom);
  const hoverClear = useRef<ReturnType<typeof setTimeout>>(undefined);
  // Every click on a choropleth lands on some district, so a double-click
  // (zoom) would otherwise select + deselect it and start a fly under the
  // zoom animation. Select after a short delay; a dblclick cancels it.
  const pendingClick = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(
    () => () => {
      clearTimeout(hoverClear.current);
      clearTimeout(pendingClick.current);
    },
    [],
  );

  // Same deferral as the Tokyo map: slider frames must not recompute 50
  // scores + percentile anchors synchronously.
  const deferredWeights = useDeferredValue(weights);
  const scored = useMemo(
    () =>
      districts.map((d) => ({
        ...d,
        score: d.ratings ? calculateWeightedScore(d.ratings, deferredWeights) : null,
      })),
    [districts, deferredWeights],
  );
  const anchors = useMemo(() => computeCompositeAnchors(districts, deferredWeights), [districts, deferredWeights]);
  const passing = useMemo(
    () =>
      new Set(
        applyDealbreakers(scored, filters, hideFloodRisk, hideHighSeismic, city.defaultFilters).map((d) => d.slug),
      ),
    [scored, filters, hideFloodRisk, hideHighSeismic, city],
  );
  const filtersActive = passing.size < scored.length;
  const top5 = useMemo(
    () =>
      new Set(
        scored
          .filter((d) => passing.has(d.slug) && d.score !== null)
          .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
          .slice(0, 5)
          .map((d) => d.slug),
      ),
    [scored, passing],
  );
  const bySlug = useMemo(() => new Map(scored.map((d) => [d.slug, d])), [scored]);

  const onFlyStart = useCallback(() => setIsFlying(true), [setIsFlying]);
  const onFlyEnd = useCallback(() => setIsFlying(false), [setIsFlying]);
  const clearSelection = useCallback(() => setSelectedStation(null), [setSelectedStation]);

  const colorFor = (d: (typeof scored)[number]): string => {
    if (heatmapMode && heatmapDimension !== 'composite' && d.ratings) {
      return scoreToColor((d.ratings as StationRatings)[heatmapDimension as keyof StationRatings], heatmapDimension as ColorDimension);
    }
    return d.score !== null ? compositeToColor(d.score, anchors) : '#9CA3AF';
  };

  const selectedDistrict = selected ? bySlug.get(selected) : undefined;
  const hoveredDistrict = hovered && hovered !== selected ? bySlug.get(hovered) : undefined;

  const labels = useMemo(
    () =>
      districts
        .map((d) => {
          const shape = GEOMETRY[d.slug];
          if (!shape) return null;
          const name = mapLabel(stationDisplayName(d, locale).primary, locale);
          const { w, h } = boxPixels(shape.bbox, zoom);
          if (w < labelWidth(name) * 1.1 || h < 22) return null;
          // Icon built here (not in render) so hover re-renders don't swap
          // every label's DOM node.
          const icon = L.divIcon({ className: 'district-label', html: `<span>${escapeHtml(name)}</span>`, iconSize: [0, 0] });
          return { slug: d.slug, pos: shape.label, icon };
        })
        .filter((x): x is { slug: string; pos: LatLng; icon: L.DivIcon } => x !== null),
    // `scored` changes with weights, but names/positions don't — key on districts.
    [districts, zoom, locale],
  );

  const stationRadius = zoom >= 14 ? 5 : zoom >= 13 ? 4 : zoom >= 12 ? 3.2 : 2.4;

  return (
    <>
      <MapContainer
        bounds={city.map.fitBounds}
        boundsOptions={{ padding: [12, 12] }}
        maxBounds={city.map.maxBounds}
        maxBoundsViscosity={0.8}
        minZoom={city.map.minZoom}
        className="h-full w-full"
        zoomControl={false}
        attributionControl={false}
      >
        {/* Same provider as the Tokyo map (lib/basemap.ts); the district data
            itself also carries Overture's attribution. */}
        <TileLayer url={BASEMAP.url} attribution={`${BASEMAP.attribution} &middot; Overture Maps`} />
        <AttributionControl position="bottomright" prefix={false} />
        <NarrowScreenFrame bounds={city.map.fitBoundsNarrow} />
        <ZoomWatcher onZoom={setZoom} />
        <DeselectHandlers onClear={clearSelection} />
        {isTouch && <TouchZoomControls />}
        {selected && (
          <FlyToDistrict
            key={selected}
            slug={selected}
            bottomInset={isTouch ? 220 : 0}
            onFlyStart={onFlyStart}
            onFlyEnd={onFlyEnd}
          />
        )}

        <Pane name="bkk-districts" style={{ zIndex: 410 }}>
          {scored.map((d) => {
            const shape = GEOMETRY[d.slug];
            if (!shape) return null;
            const pass = passing.has(d.slug);
            const isSel = d.slug === selected;
            const isHov = d.slug === hovered;
            const fill = pass ? colorFor(d) : FILTERED_FILL;
            const reasons = pass ? [] : dealbreakerReasons(d, filters, hideFloodRisk, hideHighSeismic, city.defaultFilters);
            const names = stationDisplayName(d, locale);
            return (
              <Polygon
                key={d.slug}
                positions={shape.polygons}
                pathOptions={{
                  color: '#ffffff',
                  weight: 1,
                  opacity: 0.9,
                  fillColor: fill,
                  fillOpacity: isSel || isHov ? 0.82 : pass ? (heatmapMode ? 0.62 : 0.55) : 0.45,
                  dashArray: pass ? undefined : '3 3',
                }}
                eventHandlers={{
                  click: () => {
                    // Same delay on touch: a double-tap zoom is two clicks + dblclick too.
                    clearTimeout(pendingClick.current);
                    pendingClick.current = setTimeout(() => {
                      setSelectedStation(isSel ? null : d.slug);
                      window.umami?.track('map-click', { station: d.slug, city: 'bangkok' });
                    }, 230);
                  },
                  dblclick: () => clearTimeout(pendingClick.current),
                  mouseover: () => {
                    clearTimeout(hoverClear.current);
                    setHoveredStation(d.slug);
                    const thumb = thumbnails[d.slug]?.thumb;
                    if (thumb) {
                      const img = new Image();
                      img.src = thumb;
                    }
                  },
                  mouseout: () => {
                    hoverClear.current = setTimeout(() => {
                      if (useAppStore.getState().cities[city.id].hoveredStation === d.slug) setHoveredStation(null);
                    }, 120);
                  },
                }}
              >
                {!isTouch && !isSel && (
                  <Tooltip sticky direction="top" offset={[0, -12]} opacity={1} className="district-tooltip">
                    <div style={{ minWidth: 190, maxWidth: 240 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 700, fontSize: 14 }}>{names.primary}</div>
                          <div style={{ color: '#6b7280', fontSize: 12 }}>{names.secondary}</div>
                        </div>
                        {d.score !== null && (
                          <div style={{ fontWeight: 700, fontSize: 18, color: '#1e293b' }}>{d.score.toFixed(1)}</div>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
                        {d.station_count ? (
                          <>
                            {t('filter.stations', { count: d.station_count })} · {t('filter.lines', { count: d.line_count })}
                          </>
                        ) : (
                          t('map.noRailInDistrict')
                        )}
                        {d.rent_1k != null && <> · ~{formatRentShort(city.id, d.rent_1k)}/mo</>}
                      </div>
                      {reasons.length > 0 && (
                        <div style={{ fontSize: 11, color: '#b45309', marginTop: 4 }}>
                          {t('map.filteredOut')}: {reasons.map((r) => reasonText(t, r)).join(', ')}
                        </div>
                      )}
                    </div>
                  </Tooltip>
                )}
              </Polygon>
            );
          })}
        </Pane>

        {/* Outline overlays: top-5 pulse, hovered, selected (non-interactive). */}
        <Pane name="bkk-outlines" style={{ zIndex: 420, pointerEvents: 'none' }}>
          {!heatmapMode &&
            !isFlying &&
            [...top5]
              .filter((slug) => slug !== selected && slug !== hovered)
              .map((slug) => (
                <Polygon
                  key={`top-${slug}`}
                  positions={GEOMETRY[slug].polygons}
                  interactive={false}
                  className="district-top-pulse"
                  pathOptions={{ color: '#2C4A5F', weight: 2, fill: false }}
                />
              ))}
          {hoveredDistrict && (
            <Polygon
              key={`hover-${hoveredDistrict.slug}`}
              positions={GEOMETRY[hoveredDistrict.slug].polygons}
              interactive={false}
              pathOptions={{ color: '#2563eb', weight: 2.5, fill: false }}
            />
          )}
          {selectedDistrict && (
            <Polygon
              key={`sel-${selectedDistrict.slug}`}
              positions={GEOMETRY[selectedDistrict.slug].polygons}
              interactive={false}
              pathOptions={{ color: '#1d4ed8', weight: 3.5, fill: false }}
            />
          )}
          {compareStations
            .filter((slug) => slug !== selected && GEOMETRY[slug])
            .map((slug) => (
              <Polygon
                key={`cmp-${slug}`}
                positions={GEOMETRY[slug].polygons}
                interactive={false}
                pathOptions={{ color: '#7c3aed', weight: 2.5, dashArray: '6 4', fill: false }}
              />
            ))}
        </Pane>

        {showRail && (
          <Pane name="bkk-rail" style={{ zIndex: 430, pointerEvents: 'none' }}>
            {RAIL.lines.map((line) =>
              line.paths.map((path, i) => (
                <Polyline
                  key={`${line.id}-${i}`}
                  positions={path}
                  interactive={false}
                  pathOptions={{ color: line.color, weight: zoom >= 13 ? 4 : 3, opacity: 0.9, lineCap: 'round' }}
                />
              )),
            )}
          </Pane>
        )}

        {showRail && zoom >= 11 && (
          <Pane name="bkk-stations" style={{ zIndex: 440 }}>
            {RAIL.stations.map((s) => {
              const interchange = s.lines.length > 1;
              const color = LINE_BY_ID.get(s.lines[0])?.color ?? '#374151';
              return (
                <CircleMarker
                  key={s.id}
                  center={[s.lat, s.lng]}
                  radius={interchange ? stationRadius + 1 : stationRadius}
                  pathOptions={{
                    color: interchange ? '#1f2937' : color,
                    weight: interchange ? 2 : 1.5,
                    fillColor: '#ffffff',
                    fillOpacity: 1,
                  }}
                  eventHandlers={{
                    click: () => {
                      if (s.district) setSelectedStation(s.district);
                    },
                  }}
                >
                  {!isTouch && (
                    <Tooltip direction="top" offset={[0, -6]} opacity={1} className="station-dot-tooltip">
                      <div style={{ fontWeight: 600, fontSize: 12 }}>
                        {s.name_en} <span style={{ color: '#6b7280', fontWeight: 400 }}>{s.name_th}</span>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 3 }}>
                        {s.lines.map((lid) => {
                          const line = LINE_BY_ID.get(lid);
                          if (!line) return null;
                          return (
                            <span key={lid} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, color: '#374151' }}>
                              <span style={{ width: 8, height: 8, borderRadius: 9999, backgroundColor: line.color, display: 'inline-block' }} />
                              {line.name_en}
                            </span>
                          );
                        })}
                      </div>
                    </Tooltip>
                  )}
                </CircleMarker>
              );
            })}
          </Pane>
        )}

        {!isFlying && (
          <Pane name="bkk-labels" style={{ zIndex: 450, pointerEvents: 'none' }}>
            {labels.map((l) => (
              <Marker key={`label-${l.slug}`} position={l.pos} interactive={false} keyboard={false} icon={l.icon} />
            ))}
          </Pane>
        )}

        {/* Desktop popup for the selected district (touch uses MobileStationCard). */}
        {selectedDistrict && !isTouch && !isFlying && GEOMETRY[selectedDistrict.slug] && (
          <Popup
            key={`popup-${selectedDistrict.slug}`}
            position={GEOMETRY[selectedDistrict.slug].label}
            autoPan={false}
            eventHandlers={{
              remove: () => {
                // The × button: clear the selection. Unmounts caused by a new
                // selection or a fly start leave the store untouched.
                const state = useAppStore.getState();
                if (!state.isFlying && state.cities[city.id].selectedStation === selectedDistrict.slug) {
                  setSelectedStation(null);
                }
              },
            }}
          >
            <DistrictPopupBody
              district={selectedDistrict}
              thumb={thumbnails[selectedDistrict.slug]?.thumb}
              snippet={snippets[selectedDistrict.slug]}
              color={colorFor(selectedDistrict)}
              isCompared={compareStations.includes(selectedDistrict.slug)}
              compareFull={compareStations.length >= 3}
              onCompare={() => addCompareStation(selectedDistrict.slug)}
              onUncompare={() => removeCompareStation(selectedDistrict.slug)}
            />
          </Popup>
        )}
      </MapContainer>
      <Legend anchors={anchors} heatmapMode={heatmapMode} heatmapDimension={heatmapDimension} filtersActive={filtersActive} />
    </>
  );
}

function DistrictPopupBody({
  district: d,
  thumb,
  snippet,
  color,
  isCompared,
  compareFull,
  onCompare,
  onUncompare,
}: {
  district: MapStation & { score: number | null };
  thumb?: string;
  snippet?: string;
  color: string;
  isCompared: boolean;
  compareFull: boolean;
  onCompare: () => void;
  onUncompare: () => void;
}) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const names = stationDisplayName(d, locale);
  return (
    <div className="min-w-[220px] max-w-[260px]">
      <div style={{ margin: '-10px -12px 8px', overflow: 'hidden', borderRadius: '8px 8px 0 0' }}>
        <StationTooltipHero
          key={`popup-${d.slug}`}
          slug={d.slug}
          thumb={thumb}
          lqip={undefined}
          nameEn={names.primary}
          nameJp={d.name_th ?? names.secondary}
          score={d.score}
          color={color}
        />
      </div>
      <div className="font-bold text-base">{names.primary}</div>
      <div className="text-gray-500 text-sm mb-1">{names.secondary}</div>
      {d.score !== null && <div className="text-lg font-bold text-slate-800">{d.score.toFixed(1)} / 10</div>}
      <div className="text-xs text-gray-500 mb-2">
        {d.station_count ? (
          <>
            {t('filter.stations', { count: d.station_count })} · {t('filter.lines', { count: d.line_count })}
          </>
        ) : (
          t('map.noRailInDistrict')
        )}
        {d.rent_1k != null && <> · ~{formatRentShort('bangkok', d.rent_1k)}/mo</>}
      </div>
      {snippet && <div className="text-xs text-gray-600 mb-2 line-clamp-3 leading-relaxed">{snippet}</div>}
      <div className="flex items-center gap-3 mt-1">
        <Link
          href={areaPath('bangkok', d.slug)}
          className="text-blue-600 text-xs hover:underline"
          data-umami-event="view-details"
          data-umami-event-station={d.slug}
        >
          {t('map.viewDetails')}
        </Link>
        {isCompared ? (
          <button onClick={(e) => { e.stopPropagation(); onUncompare(); }} className="text-red-500 text-xs hover:underline">
            {t('map.removeCompare')}
          </button>
        ) : (
          <button
            onClick={(e) => { e.stopPropagation(); onCompare(); }}
            className="text-purple-600 text-xs hover:underline disabled:opacity-40"
            disabled={compareFull}
          >
            {t('map.compare')}
          </button>
        )}
      </div>
    </div>
  );
}
