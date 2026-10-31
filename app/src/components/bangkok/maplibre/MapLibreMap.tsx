'use client';

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import type { GeoJSONSource, Map as LibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '../prototype/prototype.css';
import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import type { MapStation, StationRatings } from '@/lib/types';
import { useCity } from '@/lib/city-context';
import { useAreaLists } from '@/lib/area-lists';
import { useAppStore, useCityActions, useCityState, MAX_COMPARE } from '@/lib/store';
import { useScoredAreas } from '@/lib/scoring-react';
import { useScoredGrid, useGridHotspots } from '@/lib/scoring-grid-react';
import { cellAt, cellCenter, cellInfo, useBangkokGrid } from '@/lib/bangkok-grid';
import { compositeToColor, scoreToColor } from '@/lib/scoring';
import { parseAreaKey } from '@/lib/area-key';
import { stationPrimaryName } from '@/lib/station-name';
import { useIsTouch } from '@/lib/use-is-touch';
import { ASOK_CAMERA, type BangkokRendererHandle } from '@/lib/bangkok-prototype';
import CompactAreaCard from '@/components/area/CompactAreaCard';
import { CellDetails } from '../CellDetails';
import { Legend } from '../MapLegend';
import { GridTextureLayer } from './GridTextureLayer';
import { cellFeature, collection, EMPTY, labelFeatures, stationIdsByArea } from './map-data';
import { installMapLayers, RAIL_LAYERS } from './map-style';
import { FeatureStateCache } from './feature-state';
import { analyticalCityStyle } from './map-colors';
import { classifyMapError, ContextRecoveryTimer } from './map-errors';
import { collapseInitialAttribution } from './attribution';
import rail from '@/data/bangkok/rail.json';
import { measure, measureAsync, renderProfile, retainRendererLab } from '@/lib/render-profile';
import { attachMapProfile } from './profile-map';

const stationById = new Map(rail.stations.map((s) => [s.id, s]));
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const setSource = (map: LibreMap, id: string, data: GeoJSON.FeatureCollection) => {
  const source = map.getSource(id) as GeoJSONSource | undefined;
  if (source) void measureAsync(`source.${id}.ready`, () => measure(`source.${id}.submit`, () => source.setData(data), data.features.length)).catch(() => {});
};

export default function MapLibreMap({ stations, thumbnails = {}, snippets = {}, prototype = false, onUnavailable }: { stations: MapStation[]; thumbnails?: Record<string, { thumb: string; lqip: string }>; snippets?: Record<string, string>; prototype?: boolean; onUnavailable?: (reason: 'webgl' | 'load' | 'context') => void }) {
  const host = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LibreMap | null>(null);
  const attributionRef = useRef<maplibregl.AttributionControl | null>(null);
  const uiReadyRef = useRef(false);
  const textureRef = useRef<GridTextureLayer | null>(null);
  const stateCache = useRef(new FeatureStateCache());
  const focusKeys = useRef(new Set<string>());
  const clearHoverOnMap = useRef<() => void>(() => {});
  const hoverOnMap = useRef<(key: string | null) => void>(() => {});
  const syncFocusVisibility = useRef<() => void>(() => {});
  const featureState = useCallback((map: LibreMap, key: string, patch: Record<string, unknown>) => {
    const apply = (source: string, id: string, values: Record<string, unknown>) => stateCache.current.set(source, id, values,
      (changed) => measure(`state.${source}.submit`, () => map.setFeatureState({ source, id }, changed), 1));
    apply('bkk-areas', key, patch);
    const focus = Object.fromEntries(Object.entries(patch).filter(([key]) => ['selected', 'hover', 'compared'].includes(key)));
    if (Object.keys(focus).length) for (const id of stationIdsByArea.get(key) ?? []) apply('bkk-stations', id, focus);
  }, []);
  const [ready, setReady] = useState(false);
  const [recovery, setRecovery] = useState(0);
  const [error, setError] = useState(false);
  const [fatal, setFatal] = useState<'webgl' | 'load' | 'context' | null>(null);
  const unavailableRef = useRef(onUnavailable);
  useEffect(() => { unavailableRef.current = onUnavailable; }, [onUnavailable]);
  const [tilted, setTilted] = useState(true);
  const [compactControls, setCompactControls] = useState(false);
  const [controlsOpen, setControlsOpen] = useState(false);
  useEffect(() => {
    if (!compactControls || !controlsOpen) return;
    const outside = (event: Event) => { if (!controlsRef.current?.contains(event.target as Node)) setControlsOpen(false); };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside); };
  }, [compactControls, controlsOpen]);
  const [buildings, setBuildings] = useState(() => typeof window === 'undefined' ? true : (prototype ? window.__bangkokInitialBuildings : undefined) ?? true);
  const t = useTranslations(), locale = useLocale() as Locale;
  const city = useCity(), lists = useAreaLists(), isTouch = useIsTouch();
  const stationAreas = useMemo(() => lists?.station ?? [], [lists]);
  const level = useCityState((s) => s.level);
  const selected = useCityState((s) => s.selectedStation);
  const hovered = useCityState((s) => s.hoveredStation);
  const compared = useCityState((s) => s.compareStations);
  const filters = useCityState((s) => s.filters);
  const flood = useCityState((s) => s.hideFloodRisk), adult = useCityState((s) => s.hideAdultZones);
  const heat = useAppStore((s) => s.heatmapMode), dimension = useAppStore((s) => s.heatmapDimension);
  const weights = useAppStore((s) => s.weights);
  const showRail = useAppStore((s) => s.showRailOverlay);
  const actions = useCityActions();
  const primary = useScoredAreas(stations, 'primary'), areas = useScoredAreas(stationAreas, 'station');
  const { grid } = useBangkokGrid(level === 'grid' || selected?.startsWith('cell.') === true);
  const gridScored = useScoredGrid(level === 'grid' || selected?.startsWith('cell.') ? grid : null, primary.areas, primary.deferredWeights, filters, city.defaultFilters, flood, adult);
  const spots = useGridHotspots(grid, gridScored, 5, level === 'grid' && !heat);
  const dim = heat && dimension !== 'composite' ? dimension as keyof StationRatings : null;
  const all = useMemo(() => [...primary.scored, ...areas.scored], [primary.scored, areas.scored]);
  const byKey = useMemo(() => new Map(all.map((a) => [a.slug, a])), [all]);
  const primaryPassing = useMemo(() => new Set(primary.passing.map((a) => a.slug)), [primary.passing]);
  const areaPassing = useMemo(() => new Set(areas.passing.map((a) => a.slug)), [areas.passing]);
  const current = useRef({ level, selected, compared, grid, gridScored, byKey, locale, isTouch, actions, cellTitle: t('map.cellTitle') });
  useEffect(() => { current.current = { level, selected, compared, grid, gridScored, byKey, locale, isTouch, actions, cellTitle: t('map.cellTitle') }; }, [level, selected, compared, grid, gridScored, byKey, locale, isTouch, actions, t]);

  useEffect(() => {
    if (!host.current) return;
    const cache = stateCache.current;
    let map: LibreMap;
    try {
      const initial = (prototype ? window.__bangkokInitialCamera : undefined) ?? ASOK_CAMERA;
      maplibregl.setWorkerUrl(`/map-assets/maplibre-gl-worker-${maplibregl.getVersion()}.mjs`);
      map = new maplibregl.Map({ container: host.current, style: 'https://tiles.openfreemap.org/styles/positron',
        transformStyle: (_, style) => analyticalCityStyle(style),
        center: [initial.lng, initial.lat], zoom: initial.zoom - 1, pitch: initial.pitch, bearing: initial.bearing,
        locale: { 'NavigationControl.ZoomIn': t('map.zoomIn'), 'NavigationControl.ZoomOut': t('map.zoomOut'), 'NavigationControl.ResetBearing': t('map.resetBearing'), 'AttributionControl.ToggleAttribution': t('map.mapAttribution'), 'Map.Title': t('map.interactiveBangkok') },
        maxPitch: 60, minZoom: 8, maxZoom: 19, maxBounds: [[100.0, 13.2], [101.25, 14.25]],
        attributionControl: false,
        pixelRatio: Math.min(window.devicePixelRatio, 2), canvasContextAttributes: { antialias: true, preserveDrawingBuffer: false },
      });
    } catch { setFatal('webgl'); unavailableRef.current?.('webgl'); return; }
    mapRef.current = map;
    const releaseLab = prototype ? retainRendererLab() : () => {};
    const detachProfile = prototype ? attachMapProfile(map) : () => {};
    let disposed = false, loaded = false, failed = false, frame = 0, renders = 0, errors = 0;
    let clickTimer: ReturnType<typeof setTimeout> | undefined;
    const fail = (reason: 'load' | 'context') => { if (disposed || failed) return; failed = true; setFatal(reason); setReady(false); unavailableRef.current?.(reason); };
    let loadTimeout = window.setTimeout(() => { if (!loaded) fail('load'); }, 20000);
    const contextTimeout = new ContextRecoveryTimer(() => fail('context'));
    let contextGeneration = 0;
    let pendingStyle: (() => void) | undefined;
    let hoverKey: string | null = null;
    const tooltip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
    const tooltipElement = document.createElement('div'); tooltipElement.className = 'bkk-lab-tooltip';
    tooltip.setDOMContent(tooltipElement);
    let focusedHover: string | null = null;
    const syncFocus = () => {
      if (!map.getLayer('bkk-area-focus-fill')) return;
      const active = [current.current.selected, ...current.current.compared, focusedHover].some((key) => key && !key.startsWith('cell.'));
      const visibility = active ? 'visible' : 'none';
      if (map.getLayoutProperty('bkk-area-focus-fill', 'visibility') !== visibility) map.setLayoutProperty('bkk-area-focus-fill', 'visibility', visibility);
    };
    syncFocusVisibility.current = syncFocus;
    const setHover = (key: string | null) => {
      if (key === focusedHover || !map.getSource('bkk-areas')) return;
      const old = focusedHover; focusedHover = key;
      if (old && !old.startsWith('cell.')) featureState(map, old, { hover: false });
      if (key && !key.startsWith('cell.')) featureState(map, key, { hover: true });
      if (old?.startsWith('cell.') || key?.startsWith('cell.')) {
        const p = key ? parseAreaKey(key) : null, grid = current.current.grid;
        setSource(map, 'bkk-hover', p?.kind === 'cell' && p.index !== null && grid ? collection([cellFeature(grid.header, p.index)]) : EMPTY);
      }
      syncFocus();
    };
    hoverOnMap.current = setHover;
    const clearHover = () => { cancelAnimationFrame(frame); frame = 0; hoverKey = null; tooltip.remove(); map.getCanvas().style.cursor = ''; setHover(null); };
    clearHoverOnMap.current = clearHover;
    const bridge: BangkokRendererHandle = {
      renderer: 'maplibre',
      ready: () => uiReadyRef.current && map.loaded() && map.areTilesLoaded() && (current.current.level !== 'grid' || (textureRef.current?.uploads ?? 0) > 0),
      setCamera: (c, duration = 0) => { map.stop(); map.easeTo({ center: [c.lng, c.lat], zoom: c.zoom - 1, pitch: c.pitch ?? map.getPitch(), bearing: c.bearing ?? map.getBearing(), duration, essential: false }); },
      getCamera: () => ({ lat: map.getCenter().lat, lng: map.getCenter().lng, zoom: map.getZoom() + 1, pitch: map.getPitch(), bearing: map.getBearing() }),
      project: (lng, lat) => { const p = map.project([lng, lat]); return { x: p.x, y: p.y }; },
      stats: () => ({ renders, errors, gridUploads: textureRef.current?.uploads ?? 0, gridDraws: textureRef.current?.draws ?? 0,
        gridGpuBytes: textureRef.current?.gpuBytes ?? 0, gridUpdateMs: textureRef.current?.updateMs ?? 0,
        buildingFeatures: map.isStyleLoaded() && map.getLayer('bkk-buildings') ? map.queryRenderedFeatures({ layers: ['bkk-buildings'] }).length : 0 }),
    };
    if (prototype) window.__bangkokRenderer = bridge;
    if (prototype && renderProfile()) {
      bridge.inspectCartography = () => {
        const style = map.getStyle();
        return {
          layers: map.getLayersOrder(),
          nature: ['bkk-landcover', 'park', 'landcover_wood', 'water', 'bkk-park-labels'].filter((id) => !!map.getLayer(id))
            .flatMap((id) => map.queryRenderedFeatures({ layers: [id] }).slice(0, 24))
            .map((f) => ({ layer: f.layer.id, kind: String(f.properties.class ?? ''), name: String(f.properties['name:en'] ?? f.properties.name_en ?? f.properties.name ?? '') })),
          paint: Object.fromEntries(['bkk-area-focus-fill', 'bkk-area-focus', 'bkk-area-compare', 'bkk-selected-fill', 'bkk-cell-compare', 'bkk-landcover', 'water'].map((id) => [id, style.layers.find((l) => l.id === id)?.paint])),
          focusVisible: map.getLayoutProperty('bkk-area-focus-fill', 'visibility') !== 'none',
        };
      };
      bridge.inspectArea = (key) => ({ area: map.getFeatureState({ source: 'bkk-areas', id: key }),
        stations: (stationIdsByArea.get(key) ?? []).map((id) => map.getFeatureState({ source: 'bkk-stations', id })),
        rendered: map.queryRenderedFeatures({ layers: ['bkk-area-fill'], filter: ['==', ['get', 'key'], key] }).map((f) => ({ id: f.id, state: f.state })),
        renderedFocus: map.queryRenderedFeatures({ layers: ['bkk-area-focus-fill'], filter: ['==', ['get', 'key'], key] }).map((f) => ({ id: f.id, state: f.state })),
        renderedStations: map.queryRenderedFeatures({ layers: ['bkk-stations'], filter: ['==', ['get', 'key'], key] }).map((f) => ({ id: f.id, state: f.state })) });
      const saved = new Map<string, 'visible' | 'none'>();
      bridge.setLayerGroup = (group, visible) => {
        if (group === 'grid') { if (textureRef.current) textureRef.current.visible = visible && current.current.level === 'grid'; }
        else for (const layer of map.getStyle().layers) {
          const matches = group === 'areas' ? layer.id.startsWith('bkk-area-') : group === 'rail' ? /^bkk-(rail|station)/.test(layer.id) : group === 'labels' ? layer.id === 'bkk-labels' : layer.id === 'bkk-buildings';
          if (!matches) continue;
          if (!visible) { saved.set(layer.id, map.getLayoutProperty(layer.id, 'visibility') === 'none' ? 'none' : 'visible'); map.setLayoutProperty(layer.id, 'visibility', 'none'); }
          else { map.setLayoutProperty(layer.id, 'visibility', saved.get(layer.id) ?? 'visible'); saved.delete(layer.id); }
        }
        map.triggerRepaint();
      };
    }
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    const attribution = new maplibregl.AttributionControl({ compact: host.current.clientWidth < 768 });
    attributionRef.current = attribution;
    map.addControl(attribution, 'bottom-right');
    map.on('error', (event) => {
      errors++;
      if (disposed) return;
      const kind = classifyMapError(event.error, loaded);
      if (kind === 'load') fail('load');
      else if (kind === 'tile') setError(true);
    });
    map.on('idle', () => { if (!disposed && loaded) setError(false); });
    map.on('render', () => { renders++; });
    map.on('pitchend', () => { if (!disposed) setTilted(map.getPitch() > 5); });
    map.on('movestart', clearHover);
    map.on('webglcontextlost', () => {
      if (disposed || failed) return;
      contextGeneration++;
      if (pendingStyle) map.off('style.load', pendingStyle);
      pendingStyle = undefined;
      window.clearTimeout(loadTimeout);
      cache.clear(); focusedHover = null; hoverKey = null;
      tooltip.remove(); uiReadyRef.current = false; setReady(false); contextTimeout.start();
    });
    map.on('webglcontextrestored', () => {
      if (disposed || failed) return;
      contextTimeout.clear();
      if (!loaded) {
        loadTimeout = window.setTimeout(() => { if (!loaded) fail('load'); }, 20000);
        return;
      }
      // MapLibre rebuilds its native style. Custom layers and feature state
      // must be replayed, including when loss/restoration are React-batched.
      const generation = contextGeneration;
      const restored = () => {
        pendingStyle = undefined;
        if (disposed || failed || generation !== contextGeneration) return;
        contextTimeout.clear();
        setRecovery((value) => value + 1);
        setReady(true);
      };
      if (map.getLayer('bkk-area-fill')) restored();
      else { pendingStyle = restored; contextTimeout.start(); map.once('style.load', restored); }
    });
    map.once('load', () => {
      if (disposed || failed) return;
      loaded = true; window.clearTimeout(loadTimeout);
      try { measure('map.install-layers', () => installMapLayers(map, map.getStyle())); } catch { fail('load'); return; }
      map.setSourceTileLodParams(4, 3);
      map.getCanvas().setAttribute('aria-label', t('map.interactiveBangkok'));
      setTilted(map.getPitch() > 5);
      setReady(true);
    });
    const keyAt = (point: maplibregl.Point, lng: number, lat: number) => {
      if (!map.getLayer('bkk-stations')) return null;
      const s = current.current;
      const hit = measure('map.pick', () => map.queryRenderedFeatures(point, { layers: ['bkk-spots', 'bkk-stations', ...(s.level === 'grid' ? [] : ['bkk-area-fill'])] }))[0];
      if (hit) return String(hit.layer.id === 'bkk-stations' ? (s.level === 'district' ? hit.properties.district : hit.properties.key) : hit.properties.key) || null;
      if (s.level === 'grid' && s.grid) { const i = cellAt(s.grid, lat, lng); return i >= 0 ? `cell.${i}` : null; }
      return null;
    };
    map.on('click', (e) => {
      if (e.originalEvent.detail > 1) return;
      const key = keyAt(e.point, e.lngLat.lng, e.lngLat.lat);
      clearHover();
      const select = () => current.current.actions.setSelectedStation(key === current.current.selected ? null : key);
      if (current.current.isTouch) select();
      else { clearTimeout(clickTimer); clickTimer = setTimeout(select, 250); }
    });
    map.on('dblclick', () => clearTimeout(clickTimer));
    map.on('mousemove', (e) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const s = current.current;
        if (s.isTouch || map.isMoving()) return;
        const key = keyAt(e.point, e.lngLat.lng, e.lngLat.lat);
        map.getCanvas().style.cursor = key ? 'pointer' : '';
        if (key === hoverKey) return;
        hoverKey = key; setHover(key);
        if (!key || key === s.selected) { tooltip.remove(); return; }
        const parsed = parseAreaKey(key), area = s.byKey.get(key);
        const title = area ? stationPrimaryName(area, s.locale) : s.cellTitle;
        const score = area?.score ?? (parsed.index !== null ? s.gridScored?.scores[parsed.index] : null);
        tooltipElement.textContent = `${title}${score != null ? ` · ${score.toFixed(1)}` : ''}`;
        tooltip.setLngLat(e.lngLat);
        if (!tooltip.isOpen()) tooltip.addTo(map);
      });
    });
    const leave = () => clearHover(); map.getCanvas().addEventListener('mouseleave', leave);
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') current.current.actions.setSelectedStation(null); };
    window.addEventListener('keydown', escape);
    const resize = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      const compact = width < 768 && height < 360;
      setCompactControls(compact);
      if (!compact) setControlsOpen(false);
      map.resize();
    }); resize.observe(host.current);
    return () => { disposed = true; uiReadyRef.current = false; clearTimeout(clickTimer); window.clearTimeout(loadTimeout); contextTimeout.clear(); if (pendingStyle) map.off('style.load', pendingStyle); cancelAnimationFrame(frame); resize.disconnect(); tooltip.remove(); window.removeEventListener('keydown', escape); map.getCanvas().removeEventListener('mouseleave', leave);
      if (window.__bangkokRenderer === bridge) { delete window.__bangkokRenderer; delete window.__bangkokGridPaint; }
      detachProfile(); releaseLab(); map.remove(); cache.clear(); focusKeys.current.clear(); hoverOnMap.current = () => {}; clearHoverOnMap.current = () => {}; syncFocusVisibility.current = () => {}; mapRef.current = null; attributionRef.current = null; textureRef.current = null;
    };
  // Locale changes remount this map through the localized route.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [featureState, prototype]);

  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    if (level === 'grid') return;
    const active = level === 'station' ? areas : primary;
    const passing = level === 'station' ? areaPassing : primaryPassing;
    measure('areas.sync', () => { for (const a of active.scored) {
      const pass = passing.has(a.slug);
      featureState(map, a.slug, { color: pass ? dim && a.ratings ? scoreToColor(a.ratings[dim], dim) : compositeToColor(a.score ?? 0, active.anchors) : '#e5e7eb', opacity: pass ? .6 : .4 });
    } }, active.scored.length);
  // Geometry/labels/visibility have independent lifetimes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, recovery, areas.scored, primary.scored, areaPassing, primaryPassing, areas.anchors, primary.anchors, dim, level, featureState]);
  useEffect(() => {
    const map = mapRef.current, attribution = attributionRef.current;
    if (!ready || !map || !attribution) return;
    map.removeControl(attribution);
    map.addControl(attribution, compactControls ? 'top-right' : 'bottom-right');
    const element = map.getContainer().querySelector<HTMLElement>('.maplibregl-ctrl-attrib');
    if (compactControls && element) return collapseInitialAttribution(element);
  }, [ready, compactControls]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    map.getCanvas().setAttribute('aria-label', t('map.interactiveBangkok'));
    for (const [selector, label] of [
      ['.maplibregl-ctrl-zoom-in', t('map.zoomIn')],
      ['.maplibregl-ctrl-zoom-out', t('map.zoomOut')],
      ['.maplibregl-ctrl-compass', t('map.resetBearing')],
      ['.maplibregl-ctrl-attrib-button', t('map.mapAttribution')],
    ]) {
      const control = map.getContainer().querySelector(selector);
      control?.setAttribute('aria-label', label);
      control?.setAttribute('title', label);
    }
  }, [ready, recovery, t]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    setSource(map, 'bkk-labels', measure('labels.build', () => labelFeatures(stations, (a) => stationPrimaryName(a, locale))));
    map.setLayoutProperty('bkk-station-labels', 'text-field', ['get', locale === 'ja' ? 'name_ja' : 'name']);
    if (map.getLayer('bkk-park-labels')) map.setLayoutProperty('bkk-park-labels', 'text-field', ['coalesce', ['get', `name:${locale}`], ['get', 'name:en'], ['get', 'name_en'], ['get', 'name'], '']);
  }, [ready, recovery, locale, stations]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    for (const id of ['bkk-area-fill', 'bkk-area-outline']) map.setFilter(id, ['==', ['get', 'kind'], level === 'grid' ? 'none' : level]);
    map.setLayoutProperty('bkk-area-context', 'visibility', level === 'district' ? 'none' : 'visible');
  }, [ready, recovery, level]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    for (const id of RAIL_LAYERS) map.setLayoutProperty(id, 'visibility', showRail ? 'visible' : 'none');
  }, [ready, recovery, showRail]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map || !map.getLayer('bkk-buildings')) return;
    map.setLayoutProperty('bkk-buildings', 'visibility', buildings ? 'visible' : 'none');
  }, [ready, recovery, buildings]);

  useLayoutEffect(() => {
    const map = mapRef.current; if (!ready || !map || !grid || !gridScored) return;
    if (!textureRef.current) textureRef.current = new GridTextureLayer(grid.header);
    if (!map.getLayer(textureRef.current.id)) map.addLayer(textureRef.current, 'bkk-area-fill');
    textureRef.current.update(grid, gridScored, dim);
  }, [ready, recovery, grid, gridScored, dim]);
  useEffect(() => { if (textureRef.current) { textureRef.current.visible = level === 'grid'; mapRef.current?.triggerRepaint(); } }, [ready, recovery, level, grid]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    setSource(map, 'bkk-spots', grid && level === 'grid' ? collection(spots.map((i, rank) => ({ type: 'Feature', properties: { key: `cell.${i}`, rank: String(rank + 1) }, geometry: { type: 'Point', coordinates: cellCenter(grid.header, i).reverse() } }))) : EMPTY);
  }, [ready, recovery, grid, level, spots]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    const keys = new Set([selected, ...compared].filter((s): s is string => !!s && !s.startsWith('cell.')));
    for (const key of new Set([...focusKeys.current, ...keys])) featureState(map, key, { selected: key === selected, compared: compared.includes(key) });
    focusKeys.current = keys;
    syncFocusVisibility.current();
  }, [ready, recovery, selected, compared, featureState]);
  useEffect(() => { if (ready) clearHoverOnMap.current(); }, [ready, selected]);
  const selectedCell = selected?.startsWith('cell.') ? selected : null;
  const comparedCells = compared.filter((key) => key.startsWith('cell.')).join(',');
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    const keys = [...new Set([selectedCell, ...comparedCells.split(',')].filter((s): s is string => !!s))];
    setSource(map, 'bkk-selected', collection(grid ? keys.flatMap((key) => {
      const parsed = parseAreaKey(key); if (parsed.index === null) return [];
      const shape = cellFeature(grid.header, parsed.index); shape.properties = { ...shape.properties, role: key === selectedCell ? 'selected' : 'compared' }; return [shape];
    }) : []));
  }, [ready, recovery, selectedCell, comparedCells, grid]);
  useEffect(() => { if (ready) hoverOnMap.current(hovered); }, [ready, recovery, hovered]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map || !selected) return;
    const p = parseAreaKey(selected), area = byKey.get(selected);
    const ll = area ? [area.lng, area.lat] : p.index !== null && grid ? cellCenter(grid.header, p.index).reverse() : null;
    if (!ll) return;
    const point = map.project(ll as [number, number]), box = map.getContainer();
    if (point.x < 30 || point.y < 30 || point.x > box.clientWidth - 30 || point.y > box.clientHeight - (isTouch ? 220 : 30) || map.getZoom() < 12) {
      map.stop(); map.easeTo({ center: ll as [number, number], zoom: Math.max(12, map.getZoom()), duration: reduced() ? 0 : 300 });
    }
  // Selection owns navigation; score changes must not restart it.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, recovery, selected, grid]);

  // Publish lab readiness after the state and source replay effects have run.
  useEffect(() => { uiReadyRef.current = ready; }, [ready, recovery]);

  const chosen = selected ? byKey.get(selected) : undefined;
  const parsed = selected ? parseAreaKey(selected) : null;
  const cell = grid && gridScored && parsed?.kind === 'cell' && parsed.index !== null ? cellInfo(grid, parsed.index, gridScored.districts) : null;
  const nameOf = (id: string) => { const a = byKey.get(id); return a ? stationPrimaryName(a, locale) : id; };
  const stationName = (id: string) => { const s = stationById.get(id); return s ? locale === 'ja' && s.name_ja ? s.name_ja : s.name_en : id; };
  const anchors = level === 'grid' ? gridScored?.anchors ?? primary.anchors : level === 'station' ? areas.anchors : primary.anchors;
  const passing = level === 'grid' ? gridScored?.passing.cells ?? grid?.cells.length ?? 0 : level === 'station' ? areas.passing.length : primary.passing.length;
  const total = level === 'grid' ? grid?.cells.length ?? 0 : level === 'station' ? areas.scored.length : primary.scored.length;
  return <>
    <div ref={host} data-testid="maplibre-map" className={`bangkok-maplibre h-full w-full${compactControls ? ' bkk-map-compact' : ''}`} />
    {!ready && !fatal && <div role="status" className="absolute inset-0 grid place-items-center bg-slate-100 text-slate-600 pointer-events-none">{t('loading.map')}</div>}
    {fatal && !onUnavailable && <div role="alert" className="absolute inset-0 grid place-items-center bg-slate-100 text-slate-600">{t(fatal === 'webgl' ? 'map.rendererUnavailableWebgl' : fatal === 'context' ? 'map.rendererUnavailableContext' : 'map.rendererUnavailableLoad')}</div>}
    {error && !fatal && <div role="status" className="absolute left-3 bottom-2 z-20 rounded bg-white px-3 py-2 text-xs text-amber-800">{t('map.tileError')}</div>}
    <div ref={controlsRef} role="group" aria-label={t('map.mapControls')} className={compactControls ? `bkk-compact-controls absolute right-2.5 bottom-0 ${controlsOpen ? 'z-[1003]' : 'z-[1001]'}` : 'absolute right-3 bottom-44 max-md:top-28 max-md:bottom-auto z-20'} onKeyDown={(event) => { if (event.key === 'Escape' && controlsOpen) { event.stopPropagation(); setControlsOpen(false); } }}>
      {compactControls && <button type="button" className="bkk-compact-trigger" disabled={!ready} aria-label={t('map.mapControls')} aria-expanded={controlsOpen} onClick={() => setControlsOpen(!controlsOpen)}>3D</button>}
      {(!compactControls || controlsOpen) && <div className={`${compactControls ? 'absolute right-14 bottom-0 ' : ''}flex flex-col gap-1 rounded-lg border border-slate-300 bg-white/95 p-1 shadow-sm`}>
        <button className="bkk-lab-button" disabled={!ready} onClick={() => { mapRef.current?.easeTo({ pitch: tilted ? 0 : 50, bearing: tilted ? 0 : -20, duration: reduced() ? 0 : 300 }); setControlsOpen(false); }}>{tilted ? t('map.view2d') : t('map.view3d')}</button>
        <button className="bkk-lab-button" disabled={!ready} aria-pressed={buildings} onClick={() => { setBuildings(!buildings); setControlsOpen(false); }}>{t('map.buildings')}</button>
        <button className="bkk-lab-button" disabled={!ready} onClick={() => { mapRef.current?.easeTo({ center: [ASOK_CAMERA.lng, ASOK_CAMERA.lat], zoom: ASOK_CAMERA.zoom - 1, pitch: ASOK_CAMERA.pitch, bearing: ASOK_CAMERA.bearing, duration: reduced() ? 0 : 300 }); setControlsOpen(false); }}>{t('map.resetAsok')}</button>
      </div>}
    </div>
    {!selected && <Legend anchors={anchors} level={level} heatmapMode={heat} heatmapDimension={dimension} filtersActive={passing < total} />}
    {selected && !isTouch && chosen && <section aria-label={t('map.selectedArea')} className="bkk-selection bkk-selection-area absolute bottom-6 left-3 z-30 w-[306px] max-w-[calc(100%-1.5rem)] overflow-hidden rounded-lg border border-slate-300 bg-white shadow-lg">
      <CompactAreaCard key={chosen.slug} area={chosen} city="bangkok" score={chosen.score} weights={weights}
        thumbnail={thumbnails[chosen.slug]} snippet={snippets[chosen.slug]} isCompared={compared.includes(chosen.slug)}
        compareFull={compared.length >= MAX_COMPARE} onCompare={() => actions.addCompareStation(chosen.slug)}
        onUncompare={() => actions.removeCompareStation(chosen.slug)}
        onClose={() => { if (current.current.selected === chosen.slug) actions.setSelectedStation(null); }} />
    </section>}
    {selected && !isTouch && cell && grid && gridScored && <section aria-label={t('map.selectedArea')} className="bkk-selection absolute bottom-6 left-3 z-30 max-h-[55%] w-80 max-w-[calc(100%-1.5rem)] overflow-auto rounded-lg border border-slate-300 bg-white p-5 shadow-lg">
      <button aria-label={t('map.closeSelectedArea')} onClick={() => actions.setSelectedStation(null)} className="absolute right-1 top-1 grid h-11 w-11 place-items-center rounded text-slate-600 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600">×</button>
      <CellDetails info={cell} score={gridScored.scores[cell.index]} medians={grid.header.medians} stationName={stationName} areaName={(id) => nameOf(`st.${id}`)} districtName={nameOf} />
      <span className="sr-only">{t('map.clickForDetails')}</span>
    </section>}
  </>;
}
