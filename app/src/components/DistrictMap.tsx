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
  Rectangle,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useLocale, useTranslations } from 'next-intl';
import geometryData from '@/data/bangkok/geometry.json';
import stationGeometryData from '@/data/bangkok/station-geometry.json';
import railData from '@/data/bangkok/rail.json';
import type { AreaLevel, MapStation, RailLine, RailStation, StationRatings } from '@/lib/types';
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
import { MAX_COMPARE, useAppStore, useCityActions, useCityState } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { useAreaLists } from '@/lib/area-lists';
import { areaPath, formatRentShort } from '@/lib/cities';
import { cellKey, parseAreaKey, stationAreaKey } from '@/lib/area-key';
import {
  cellBounds,
  cellCenter,
  cellInfo,
  countPassing,
  gridAnchors,
  gridHotspots,
  passMask,
  scoreCells,
  useBangkokGrid,
  type GridDistrict,
} from '@/lib/bangkok-grid';
import { stationDisplayName, stationPrimaryName } from '@/lib/station-name';
import { useIsTouch } from '@/lib/use-is-touch';
import { StationTooltipHero, TouchZoomControls } from './map-shared';
import { BASEMAP } from '@/lib/basemap';
import GridLayer from './bangkok/GridLayer';
import StationAreaLayer, { type AreaShape, type ScoredArea } from './bangkok/StationAreaLayer';
import { CellDetails, StationAreaPopupBody } from './bangkok/popups';

type LatLng = [number, number];
interface DistrictShape {
  polygons: LatLng[][][];
  bbox: [LatLng, LatLng];
  label: LatLng;
}
const GEOMETRY = geometryData as unknown as Record<string, DistrictShape>;
const AREA_GEOMETRY = stationGeometryData as unknown as Record<string, AreaShape>;
const RAIL = railData as unknown as { lines: (RailLine & { paths: LatLng[][] })[]; stations: RailStation[] };
const LINE_BY_ID = new Map(RAIL.lines.map((l) => [l.id, l]));
const STATION_BY_ID = new Map(RAIL.stations.map((s) => [s.id, s]));

/** Fill of a district that fails the current dealbreakers. */
const FILTERED_FILL = '#E5E7EB';
const MAX_FLY_ZOOM = 14;

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

/** Fly (or pan) so the selection fits the viewport, mirroring the Tokyo
 *  `FlyToStation` contract: onFlyStart before paint, onFlyEnd after. */
function FlyToBounds({
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

/** Click outside every painted shape (sea, neighbouring provinces) clears the
 *  selection; Escape does the same from anywhere. On the grid every click
 *  lands on a cell, so the grid layer handles clicks itself. */
function DeselectHandlers({ onClear, clickClears }: { onClear: () => void; clickClears: boolean }) {
  useMapEvents({
    click: (e) => {
      if (!clickClears) return;
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

/** Station name in the UI language: katakana for JA; the Latin name that is
 *  on BTS / MRT signage otherwise (there is no Russian signage). */
function railStationName(s: RailStation | undefined, locale: Locale): string {
  if (!s) return '';
  return locale === 'ja' && s.name_ja ? s.name_ja : s.name_en;
}

function Legend({
  anchors,
  level,
  heatmapMode,
  heatmapDimension,
  filtersActive,
}: {
  anchors: PercentileAnchors;
  level: AreaLevel;
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
  const caption = level === 'grid' ? 'map.legendGrid' : level === 'station' ? 'map.legendStations' : 'map.legendDistricts';
  return (
    <div className="hidden md:block absolute bottom-6 left-3 z-[900] bg-white/95 border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-[10px] text-gray-600 w-52 pointer-events-none">
      <div className="font-semibold text-gray-700 mb-1 truncate">{title}</div>
      <div className="h-2 rounded-full" style={{ backgroundImage: `linear-gradient(90deg, ${stops.join(', ')})` }} />
      <div className="flex justify-between mt-0.5 tabular-nums">
        <span>{dim ? '1' : anchors.p5.toFixed(1)}</span>
        {!dim && <span>{anchors.p50.toFixed(1)}</span>}
        <span>{dim ? '10' : anchors.p95.toFixed(1)}</span>
      </div>
      {/* The captions describe the weighted score, not a single-category heatmap. */}
      {!dim && <div className="mt-1 text-gray-500 leading-snug">{t(caption)}</div>}
      {level === 'station' && <div className="mt-1 text-gray-500 leading-snug">{t('map.legendNoStation')}</div>}
      {level === 'grid' && (
        <div className="mt-1 text-gray-500 leading-snug">
          {t('map.legendGridFaded')} {t('map.legendGridDistrict')}
        </div>
      )}
      {filtersActive && (
        <div className="mt-1 flex items-center gap-1.5">
          <span className="inline-block w-3 h-2 rounded-sm border border-gray-300" style={{ backgroundColor: FILTERED_FILL }} />
          {t('map.legendFilteredOut')}
        </div>
      )}
    </div>
  );
}

/** District level, zoomed in: point at the finer levels once. */
function ZoomHint({ onPick }: { onPick: (level: AreaLevel) => void }) {
  const t = useTranslations('map');
  return (
    <div className="hidden md:flex absolute left-3 top-14 z-[999] items-center gap-2 rounded-lg border border-blue-200 bg-blue-50/95 px-2.5 py-1.5 text-[11px] text-blue-800 shadow-sm">
      <span>{t('zoomHint')}</span>
      <button onClick={() => onPick('station')} className="font-semibold hover:underline">
        {t('level_station')}
      </button>
      <span aria-hidden>·</span>
      <button onClick={() => onPick('grid')} className="font-semibold hover:underline">
        {t('level_grid')}
      </button>
    </div>
  );
}

export default function DistrictMap({ stations: districts, thumbnails = {}, snippets = {} }: MapViewProps) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const isTouch = useIsTouch();
  const lists = useAreaLists();
  const stationAreas = useMemo(() => lists?.station ?? [], [lists]);

  const weights = useAppStore((s) => s.weights);
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const showRail = useAppStore((s) => s.showRailOverlay);
  const isFlying = useAppStore((s) => s.isFlying);
  const setIsFlying = useAppStore((s) => s.setIsFlying);
  const level = useCityState((s) => s.level);
  const selected = useCityState((s) => s.selectedStation);
  const hovered = useCityState((s) => s.hoveredStation);
  const compareStations = useCityState((s) => s.compareStations);
  const filters = useCityState((s) => s.filters);
  const hideFloodRisk = useCityState((s) => s.hideFloodRisk);
  const hideHighSeismic = useCityState((s) => s.hideHighSeismic);
  const { setLevel, setSelectedStation, setHoveredStation, addCompareStation, removeCompareStation } = useCityActions();

  const selection = selected ? parseAreaKey(selected) : null;
  // The grid downloads when its level is shown — or when a shared link
  // points at a cell.
  const { grid } = useBangkokGrid(level === 'grid' || selection?.kind === 'cell');

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

  // Same deferral as the Tokyo map: slider frames must not recompute scores
  // + percentile anchors synchronously (≈ 40k cells on the grid level).
  const deferredWeights = useDeferredValue(weights);
  const dim = heatmapMode && heatmapDimension !== 'composite' ? (heatmapDimension as keyof StationRatings) : null;

  // ── districts ──
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
  const bySlug = useMemo(() => new Map(scored.map((d) => [d.slug, d])), [scored]);

  // ── station areas ──
  const scoredAreas: ScoredArea[] = useMemo(
    () =>
      stationAreas.map((a) => ({
        ...a,
        score: a.ratings ? calculateWeightedScore(a.ratings, deferredWeights) : null,
      })),
    [stationAreas, deferredWeights],
  );
  const areaAnchors = useMemo(() => computeCompositeAnchors(stationAreas, deferredWeights), [stationAreas, deferredWeights]);
  const areaPassing = useMemo(
    () =>
      new Set(
        applyDealbreakers(scoredAreas, filters, hideFloodRisk, hideHighSeismic, city.defaultFilters).map((a) => a.slug),
      ),
    [scoredAreas, filters, hideFloodRisk, hideHighSeismic, city],
  );
  const areaByKey = useMemo(() => new Map(scoredAreas.map((a) => [a.slug, a])), [scoredAreas]);

  // ── 200 m grid ──
  // Aligned with `grid.header.districts` (the cell's district plane is an index).
  const gridDistricts: GridDistrict[] = useMemo(() => {
    if (!grid) return [];
    const bySlugRaw = new Map(districts.map((d) => [d.slug, d]));
    return grid.header.districts.map((slug) => {
      const d = bySlugRaw.get(slug);
      return { ratings: (d?.ratings ?? {}) as StationRatings, rent_1k: d?.rent_1k ?? null };
    });
  }, [grid, districts]);
  const gridScores = useMemo(
    () => (grid ? scoreCells(grid, deferredWeights, gridDistricts) : null),
    [grid, deferredWeights, gridDistricts],
  );
  const gridAnch = useMemo(() => (grid && gridScores ? gridAnchors(grid, gridScores) : null), [grid, gridScores]);
  const gridPass = useMemo(
    () => (grid ? passMask(grid, filters, city.defaultFilters, gridDistricts) : null),
    [grid, filters, city, gridDistricts],
  );
  // Best spots rank the weighted score, so a single-category heatmap hides them
  // (like the districts' top-5 pulse).
  const gridTop = useMemo(
    () =>
      level === 'grid' && !heatmapMode && grid && gridScores && gridPass ? gridHotspots(grid, gridScores, gridPass, 5) : [],
    [level, heatmapMode, grid, gridScores, gridPass],
  );

  const levelAnchors = level === 'grid' ? (gridAnch ?? anchors) : level === 'station' ? areaAnchors : anchors;
  const gridPassing = useMemo(() => (grid && gridPass ? countPassing(grid, gridPass).cells : 0), [grid, gridPass]);
  const filtersActive =
    level === 'grid'
      ? grid !== null && gridPassing < grid.cells.length
      : level === 'station'
        ? areaPassing.size < scoredAreas.length
        : passing.size < scored.length;

  const topDistricts = useMemo(
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
  const topAreas = useMemo(
    () =>
      new Set(
        scoredAreas
          .filter((a) => areaPassing.has(a.slug) && a.score !== null)
          .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
          .slice(0, 5)
          .map((a) => a.slug),
      ),
    [scoredAreas, areaPassing],
  );

  const onFlyStart = useCallback(() => setIsFlying(true), [setIsFlying]);
  const onFlyEnd = useCallback(() => setIsFlying(false), [setIsFlying]);
  const clearSelection = useCallback(() => setSelectedStation(null), [setSelectedStation]);

  const colorFor = (d: { ratings: StationRatings | null; score: number | null }, a: PercentileAnchors): string => {
    if (dim && d.ratings) return scoreToColor(d.ratings[dim], dim as ColorDimension);
    return d.score !== null ? compositeToColor(d.score, a) : '#9CA3AF';
  };

  // ── names (locale-aware) for layers that only know ids ──
  const districtName = useCallback(
    (slug: string) => {
      const d = bySlug.get(slug);
      return d ? stationPrimaryName(d, locale) : slug;
    },
    [bySlug, locale],
  );
  const stationName = useCallback((id: string) => railStationName(STATION_BY_ID.get(id), locale), [locale]);
  const areaName = useCallback(
    (id: string) => {
      const a = areaByKey.get(stationAreaKey(id));
      return a ? stationPrimaryName(a, locale) : stationName(id);
    },
    [areaByKey, locale, stationName],
  );
  const lineChip = useCallback(
    (lid: string) => {
      const l = LINE_BY_ID.get(lid);
      return l ? { name: locale === 'ja' ? l.name_ja : locale === 'ru' ? l.name_ru : l.name_en, color: l.color } : null;
    },
    [locale],
  );
  const gridNames = useMemo(() => ({ station: stationName, district: districtName }), [stationName, districtName]);

  // ── selection ──
  const selectedDistrict = selection?.kind === 'district' ? bySlug.get(selection.id) : undefined;
  const selectedArea = selection?.kind === 'station' ? areaByKey.get(selected!) : undefined;
  const selectedCell =
    selection?.kind === 'cell' && grid && selection.index !== null && grid.planes.district[selection.index]
      ? selection.index
      : null;
  const selectedCellInfo = useMemo(
    () => (selectedCell !== null && grid ? cellInfo(grid, selectedCell, gridDistricts) : null),
    [selectedCell, grid, gridDistricts],
  );
  const flyBounds: [LatLng, LatLng] | null = selectedDistrict
    ? GEOMETRY[selectedDistrict.slug]?.bbox ?? null
    : selectedArea
      ? AREA_GEOMETRY[selectedArea.slug.slice(3)]?.bbox ?? null
      : selectedCell !== null && grid
        ? cellBounds(grid.header, selectedCell)
        : null;

  const hoveredKey = hovered && hovered !== selected ? parseAreaKey(hovered) : null;
  const hoveredKind = hoveredKey?.kind ?? null;
  // "Best spots" list rows hover a cell key.
  const hoveredCell = hoveredKey?.kind === 'cell' && grid && hoveredKey.index !== null ? hoveredKey.index : null;
  const hoveredShape =
    hoveredKind === 'district'
      ? GEOMETRY[hovered!]?.polygons
      : hoveredKind === 'station'
        ? AREA_GEOMETRY[hovered!.slice(3)]?.polygons
        : undefined;

  const shapeFor = (key: string): LatLng[][][] | undefined => {
    const { kind, id } = parseAreaKey(key);
    return kind === 'district' ? GEOMETRY[id]?.polygons : kind === 'station' ? AREA_GEOMETRY[id]?.polygons : undefined;
  };

  // ── labels ──
  const districtLabels = useMemo(
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
          return { key: d.slug, pos: shape.label, icon };
        })
        .filter((x): x is { key: string; pos: LatLng; icon: L.DivIcon } => x !== null),
    // `scored` changes with weights, but names/positions don't — key on districts.
    [districts, zoom, locale],
  );
  const areaLabels = useMemo(
    () =>
      zoom < 13
        ? []
        : stationAreas
            .map((a) => {
              const shape = AREA_GEOMETRY[a.slug.slice(3)];
              if (!shape) return null;
              // Interchanges ("Asok / Sukhumvit") are labelled by their first
              // station: the full pair rarely fits inside the area.
              const name = stationPrimaryName(a, locale).split(' / ')[0];
              const { w } = boxPixels(shape.bbox, zoom);
              if (w < labelWidth(name) * 0.9) return null;
              const icon = L.divIcon({
                className: 'district-label station-area-label',
                html: `<span>${escapeHtml(name)}</span>`,
                iconSize: [0, 0],
              });
              return { key: a.slug, pos: [a.lat, a.lng] as LatLng, icon };
            })
            .filter((x): x is { key: string; pos: LatLng; icon: L.DivIcon } => x !== null),
    [stationAreas, zoom, locale],
  );
  const labels = level === 'station' && zoom >= 13 ? areaLabels : districtLabels;

  const hotspotIcons = useMemo(
    () => gridTop.map((_, rank) => L.divIcon({ className: 'grid-hotspot', html: `<span>${rank + 1}</span>`, iconSize: [22, 22] })),
    [gridTop],
  );

  /** The popup × clears the selection; unmounts caused by a new selection
   *  or a fly start leave the store untouched. */
  const clearIfStillSelected = (key: string) => {
    const state = useAppStore.getState();
    if (!state.isFlying && state.cities[city.id].selectedStation === key) setSelectedStation(null);
  };

  const stationRadius = zoom >= 14 ? 5 : zoom >= 13 ? 4 : zoom >= 12 ? 3.2 : 2.4;
  const isDistrictLevel = level === 'district';

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
        <DeselectHandlers onClear={clearSelection} clickClears={level !== 'grid'} />
        {isTouch && <TouchZoomControls />}
        {selected && flyBounds && (
          <FlyToBounds
            key={selected}
            bounds={flyBounds}
            bottomInset={isTouch ? 220 : 0}
            onFlyStart={onFlyStart}
            onFlyEnd={onFlyEnd}
          />
        )}

        {/* ── 200 m grid (painted canvas, below every vector layer) ── */}
        <Pane name="bkk-grid" style={{ zIndex: 405 }} />
        {level === 'grid' && grid && gridScores && gridPass && gridAnch && (
          <GridLayer
            grid={grid}
            scores={gridScores}
            pass={gridPass}
            anchors={gridAnch}
            heatDimension={dim}
            districts={gridDistricts}
            pane="bkk-grid"
            hoverEnabled={!isTouch && !isFlying}
            selectedIndex={selectedCell}
            names={gridNames}
            onSelect={(i) => {
              setSelectedStation(i === null || i === selectedCell ? null : cellKey(i));
              if (i !== null) window.umami?.track('map-click', { station: 'cell', city: 'bangkok' });
            }}
          />
        )}

        {/* ── districts: the choropleth on their level, context outlines otherwise ── */}
        <Pane name="bkk-districts" style={{ zIndex: 410 }}>
          {isDistrictLevel &&
            scored.map((d) => {
              const shape = GEOMETRY[d.slug];
              if (!shape) return null;
              const pass = passing.has(d.slug);
              const isSel = d.slug === selected;
              const isHov = d.slug === hovered;
              const fill = pass ? colorFor(d, anchors) : FILTERED_FILL;
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
                    // Explicit pane: inside a custom <Pane> react-leaflet would put
                    // the tooltip in that pane, under its own polygons.
                    <Tooltip pane="tooltipPane" sticky direction="top" offset={[0, -12]} opacity={1} className="district-tooltip">
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

        {level === 'station' && (
          <StationAreaLayer
            areas={scoredAreas}
            shapes={AREA_GEOMETRY}
            passing={areaPassing}
            colorFor={(a) => colorFor(a, areaAnchors)}
            filteredFill={FILTERED_FILL}
            selected={selected}
            hovered={hovered}
            heatmapMode={heatmapMode}
            isTouch={isTouch}
            reasonsFor={(a) =>
              dealbreakerReasons(a, filters, hideFloodRisk, hideHighSeismic, city.defaultFilters).map((r) => reasonText(t, r))
            }
            lineChip={lineChip}
            districtName={districtName}
            onSelect={setSelectedStation}
            onHover={(key) => {
              if (key === null) {
                if (useAppStore.getState().cities[city.id].hoveredStation?.startsWith('st.')) setHoveredStation(null);
              } else {
                setHoveredStation(key);
                const thumb = thumbnails[key]?.thumb;
                if (thumb) {
                  const img = new Image();
                  img.src = thumb;
                }
              }
            }}
          />
        )}

        {/* Outline overlays: district context lines, top-5 pulse, hovered,
            selected, compared (non-interactive). */}
        <Pane name="bkk-outlines" style={{ zIndex: 420, pointerEvents: 'none' }}>
          {!isDistrictLevel &&
            districts.map((d) =>
              GEOMETRY[d.slug] ? (
                <Polygon
                  key={`ctx-${d.slug}`}
                  positions={GEOMETRY[d.slug].polygons}
                  interactive={false}
                  pathOptions={{
                    color: level === 'grid' ? '#ffffff' : '#94a3b8',
                    weight: level === 'grid' ? 1.2 : 1,
                    opacity: level === 'grid' ? 0.85 : 0.7,
                    fill: false,
                  }}
                />
              ) : null,
            )}
          {!heatmapMode &&
            !isFlying &&
            level !== 'grid' &&
            [...(isDistrictLevel ? topDistricts : topAreas)]
              .filter((key) => key !== selected && key !== hovered && shapeFor(key))
              .map((key) => (
                <Polygon
                  key={`top-${key}`}
                  positions={shapeFor(key)!}
                  interactive={false}
                  className="district-top-pulse"
                  pathOptions={{ color: '#2C4A5F', weight: 2, fill: false }}
                />
              ))}
          {hoveredShape && (
            <Polygon
              key={`hover-${hovered}`}
              positions={hoveredShape}
              interactive={false}
              pathOptions={{ color: '#2563eb', weight: 2.5, fill: false }}
            />
          )}
          {selected && shapeFor(selected) && (
            <Polygon
              key={`sel-${selected}`}
              positions={shapeFor(selected)!}
              interactive={false}
              pathOptions={{ color: '#1d4ed8', weight: 3.5, fill: false }}
            />
          )}
          {hoveredCell !== null && grid && (
            <Rectangle
              key={`hover-cell-${hoveredCell}`}
              bounds={cellBounds(grid.header, hoveredCell)}
              interactive={false}
              pathOptions={{ color: '#2563eb', weight: 2.5, fill: false }}
            />
          )}
          {selectedCell !== null && grid && (
            <Rectangle
              key={`sel-cell-${selectedCell}`}
              bounds={cellBounds(grid.header, selectedCell)}
              interactive={false}
              pathOptions={{ color: '#1d4ed8', weight: 3, fill: false }}
            />
          )}
          {compareStations
            .filter((key) => key !== selected && shapeFor(key))
            .map((key) => (
              <Polygon
                key={`cmp-${key}`}
                positions={shapeFor(key)!}
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
              // On the finer levels a station dot opens its station area.
              const target = !isDistrictLevel && s.area ? stationAreaKey(s.area) : s.district;
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
                  bubblingMouseEvents={false}
                  eventHandlers={{
                    click: () => {
                      if (target) setSelectedStation(target);
                    },
                  }}
                >
                  {!isTouch && (
                    <Tooltip pane="tooltipPane" direction="top" offset={[0, -6]} opacity={1} className="station-dot-tooltip">
                      <div style={{ fontWeight: 600, fontSize: 12 }}>
                        {railStationName(s, locale)}{' '}
                        <span style={{ color: '#6b7280', fontWeight: 400 }}>{s.name_th}</span>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 3 }}>
                        {s.lines.map((lid) => {
                          const chip = lineChip(lid);
                          if (!chip) return null;
                          return (
                            <span key={lid} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, color: '#374151' }}>
                              <span style={{ width: 8, height: 8, borderRadius: 9999, backgroundColor: chip.color, display: 'inline-block' }} />
                              {chip.name}
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
              <Marker key={`label-${l.key}`} position={l.pos} interactive={false} keyboard={false} icon={l.icon} />
            ))}
          </Pane>
        )}

        {/* Grid: the five best spots under the current weights, numbered. */}
        {level === 'grid' && grid && !isFlying && gridTop.length > 0 && (
          <Pane name="bkk-hotspots" style={{ zIndex: 455 }}>
            {gridTop.map((i, rank) => (
              <Marker
                key={`spot-${i}`}
                position={cellCenter(grid.header, i)}
                keyboard={false}
                icon={hotspotIcons[rank]}
                eventHandlers={{ click: () => setSelectedStation(cellKey(i)) }}
                title={t('map.hotspotTitle', { rank: rank + 1 })}
              />
            ))}
          </Pane>
        )}

        {/* Desktop popups for the selection (touch uses the bottom cards). */}
        {selectedDistrict && !isTouch && !isFlying && GEOMETRY[selectedDistrict.slug] && (
          <Popup
            key={`popup-${selectedDistrict.slug}`}
            position={GEOMETRY[selectedDistrict.slug].label}
            autoPan={false}
            eventHandlers={{ remove: () => clearIfStillSelected(selectedDistrict.slug) }}
          >
            <DistrictPopupBody
              district={selectedDistrict}
              thumb={thumbnails[selectedDistrict.slug]?.thumb}
              snippet={snippets[selectedDistrict.slug]}
              color={colorFor(selectedDistrict, anchors)}
              isCompared={compareStations.includes(selectedDistrict.slug)}
              compareFull={compareStations.length >= MAX_COMPARE}
              onCompare={() => addCompareStation(selectedDistrict.slug)}
              onUncompare={() => removeCompareStation(selectedDistrict.slug)}
            />
          </Popup>
        )}
        {selectedArea && !isTouch && !isFlying && (
          <Popup
            key={`popup-${selectedArea.slug}`}
            position={[selectedArea.lat, selectedArea.lng]}
            autoPan={false}
            eventHandlers={{ remove: () => clearIfStillSelected(selectedArea.slug) }}
          >
            <StationAreaPopupBody
              area={selectedArea}
              thumb={thumbnails[selectedArea.slug]?.thumb}
              color={colorFor(selectedArea, areaAnchors)}
              lineChip={lineChip}
              districtName={districtName}
              isCompared={compareStations.includes(selectedArea.slug)}
              compareFull={compareStations.length >= MAX_COMPARE}
              onCompare={() => addCompareStation(selectedArea.slug)}
              onUncompare={() => removeCompareStation(selectedArea.slug)}
            />
          </Popup>
        )}
        {selectedCellInfo && grid && gridScores && !isTouch && !isFlying && (
          <Popup
            key={`popup-cell-${selectedCellInfo.index}`}
            position={cellCenter(grid.header, selectedCellInfo.index)}
            // Taller than the other popups (ten rating rows): let Leaflet pan
            // it into view. The cell itself is already on screen, so the
            // pan is short.
            autoPan
            autoPanPadding={[16, 16]}
            eventHandlers={{ remove: () => clearIfStillSelected(cellKey(selectedCellInfo.index)) }}
          >
            <CellDetails
              info={selectedCellInfo}
              score={Number.isNaN(gridScores[selectedCellInfo.index]) ? null : gridScores[selectedCellInfo.index]}
              medians={grid.header.medians}
              stationName={stationName}
              areaName={areaName}
              districtName={districtName}
            />
          </Popup>
        )}
      </MapContainer>
      {isDistrictLevel && zoom >= 13 && !selected && <ZoomHint onPick={setLevel} />}
      <Legend
        anchors={levelAnchors}
        level={level}
        heatmapMode={heatmapMode}
        heatmapDimension={heatmapDimension}
        filtersActive={filtersActive}
      />
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
