'use client';

import { Legend, ZoomHint } from '@/components/bangkok/MapLegend';
import { districtMapLabels, stationAreaMapLabels } from '@/lib/bangkok-labels';

import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import {
  AttributionControl,
  MapContainer,
  Marker,
  Pane,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useLocale, useTranslations } from 'next-intl';
import geometryData from '@/data/bangkok/geometry.json';
import stationGeometryData from '@/data/bangkok/station-geometry.json';
import railData from '@/data/bangkok/rail.json';
import type { MapStation, RailLine, RailStation, StationRatings } from '@/lib/types';
import type { Locale } from '@/i18n/routing';
import {
  compositeToColor,
  dealbreakerReasons,
  scoreToColor,
  type ColorDimension,
  type DealbreakerReason,
  type PercentileAnchors,
} from '@/lib/scoring';
import { useScoredAreas } from '@/lib/scoring-react';
import { useGridHotspots, useScoredGrid } from '@/lib/scoring-grid-react';
import { MAX_COMPARE, useAppStore, useCityActions, useCityState } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { useAreaLists } from '@/lib/area-lists';
import { cellKey, parseAreaKey, stationAreaKey } from '@/lib/area-key';
import {
  cellBounds,
  cellCenter,
  cellInfo,
  useBangkokGrid,
  type GridDistrict,
} from '@/lib/bangkok-grid';
import { stationPrimaryName } from '@/lib/station-name';
import { useIsTouch } from '@/lib/use-is-touch';
import { MapContainerResize, TouchZoomControls } from './map-shared';
import { MapDeselect, MapSelectionBounds } from './map-selection';
import { BASEMAP } from '@/lib/basemap';
import GridLayer from './bangkok/GridLayer';
import BangkokRailLayer from './bangkok/BangkokRailLayer';
import BangkokOutlines from './bangkok/BangkokOutlines';
import DistrictLayer from './bangkok/DistrictLayer';
import StationAreaLayer, { type AreaShape } from './bangkok/StationAreaLayer';
import { CellDetails, DistrictPopupBody, StationAreaPopupBody } from './bangkok/popups';

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
const EMPTY_GRID_DISTRICTS: GridDistrict[] = [];

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
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

function reasonText(t: ReturnType<typeof useTranslations<never>>, r: DealbreakerReason): string {
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

export default function DistrictMap({ stations: districts, thumbnails = {}, snippets = {} }: MapViewProps) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const isTouch = useIsTouch();
  const lists = useAreaLists();
  const stationAreas = useMemo(() => lists?.station ?? [], [lists]);

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
  const hideAdultZones = useCityState((s) => s.hideAdultZones);
  const { setLevel, setSelectedStation, setHoveredStation, addCompareStation, removeCompareStation } = useCityActions();

  const selection = selected ? parseAreaKey(selected) : null;
  // The grid downloads when its level is shown — or when a shared link
  // points at a cell.
  const { grid } = useBangkokGrid(level === 'grid' || selection?.kind === 'cell');

  const [zoom, setZoom] = useState(city.map.zoom);
  const dim = heatmapMode && heatmapDimension !== 'composite' ? (heatmapDimension as keyof StationRatings) : null;

  // ── districts ──
  const { areas: sharedDistricts, scored, anchors, passing: passingDistricts, deferredWeights } = useScoredAreas(districts, 'primary');
  const passing = useMemo(() => new Set(passingDistricts.map((d) => d.slug)), [passingDistricts]);
  const bySlug = useMemo(() => new Map(scored.map((d) => [d.slug, d])), [scored]);

  // ── station areas ──
  const { scored: scoredAreas, anchors: areaAnchors, passing: passingAreas } = useScoredAreas(stationAreas, 'station');
  const areaPassing = useMemo(() => new Set(passingAreas.map((a) => a.slug)), [passingAreas]);
  const areaByKey = useMemo(() => new Map(scoredAreas.map((a) => [a.slug, a])), [scoredAreas]);

  // ── 200 m grid ──
  const gridScoring = useScoredGrid(grid, sharedDistricts, deferredWeights, filters, city.defaultFilters, hideFloodRisk);
  const gridDistricts = gridScoring?.districts ?? EMPTY_GRID_DISTRICTS;
  const gridScores = gridScoring?.scores ?? null;
  const gridAnch = gridScoring?.anchors ?? null;
  const gridPass = gridScoring?.pass ?? null;
  // Best spots rank the weighted score, so a single-category heatmap hides them
  // (like the districts' top-5 pulse).
  const gridTop = useGridHotspots(grid, gridScoring, 5, level === 'grid' && !heatmapMode);

  const levelAnchors = level === 'grid' ? (gridAnch ?? anchors) : level === 'station' ? areaAnchors : anchors;
  const gridPassing = gridScoring?.passing.cells ?? 0;
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
    () => districtMapLabels(districts, GEOMETRY, zoom, locale).map(({ key, pos, className, html }) => ({
      key, pos, icon: L.divIcon({ className, html, iconSize: [0, 0] }),
    })),
    [districts, zoom, locale],
  );
  const areaLabels = useMemo(
    () => stationAreaMapLabels(stationAreas, AREA_GEOMETRY, zoom, locale).map(({ key, pos, className, html }) => ({
      key, pos, icon: L.divIcon({ className, html, iconSize: [0, 0] }),
    })),
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
        <MapContainerResize />
        {/* Same provider as the Tokyo map (lib/basemap.ts); the district data
            itself also carries Overture's attribution. */}
        <TileLayer url={BASEMAP.url} attribution={`${BASEMAP.attribution} &middot; Overture Maps`} />
        <AttributionControl position="bottomright" prefix={false} />
        <NarrowScreenFrame bounds={city.map.fitBoundsNarrow} />
        <ZoomWatcher onZoom={setZoom} />
        <MapDeselect onClear={clearSelection} clickClears={level !== 'grid'} escapeClears />
        {isTouch && <TouchZoomControls />}
        {selected && flyBounds && (
          <MapSelectionBounds
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

        <DistrictLayer isDistrictLevel={isDistrictLevel} scored={scored} shapes={GEOMETRY} passing={passing}
          selected={selected} hovered={hovered} heatmapMode={heatmapMode} isTouch={isTouch} thumbnails={thumbnails}
          colorFor={(d) => colorFor(d, anchors)}
          reasonsFor={(d) => dealbreakerReasons(d, filters, hideFloodRisk, hideHighSeismic, hideAdultZones, city.defaultFilters).map((r) => reasonText(t, r))} />

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
              dealbreakerReasons(a, filters, hideFloodRisk, hideHighSeismic, hideAdultZones, city.defaultFilters).map((r) => reasonText(t, r))
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

        <BangkokOutlines districts={districts} geometry={GEOMETRY} level={level} isDistrictLevel={isDistrictLevel}
          heatmapMode={heatmapMode} isFlying={isFlying} topDistricts={topDistricts} topAreas={topAreas}
          selected={selected} hovered={hovered} shapeFor={shapeFor} hoveredShape={hoveredShape} hoveredCell={hoveredCell}
          selectedCell={selectedCell} grid={grid} compareStations={compareStations} />

        <BangkokRailLayer rail={RAIL} showRail={showRail} zoom={zoom} isDistrictLevel={isDistrictLevel}
          isTouch={isTouch} stationRadius={stationRadius} locale={locale} lineChip={lineChip} setSelectedStation={setSelectedStation} />

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
