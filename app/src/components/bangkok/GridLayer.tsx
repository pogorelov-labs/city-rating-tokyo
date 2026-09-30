'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { Rectangle, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import { useTranslations } from 'next-intl';
import type { StationRatings } from '@/lib/types';
import { compositeToColor, scoreToColor, type ColorDimension, type PercentileAnchors } from '@/lib/scoring';
import { NEAR_STATION_M, cellAt, cellBounds, cellInfo, type BangkokGrid, type GridDistrict } from '@/lib/bangkok-grid';

/** Fill of a cell that fails the dealbreakers (same grey as filtered districts). */
const FILTERED_RGB: readonly [number, number, number] = [229, 231, 235];

function parseRgb(css: string): [number, number, number] {
  const m = css.match(/\d+/g);
  return m ? [Number(m[0]), Number(m[1]), Number(m[2])] : [156, 163, 175];
}

/**
 * Leaflet's ImageOverlay positions and zoom-animates an <img>; this variant
 * does the same for a <canvas> (like Leaflet's own SVGOverlay does for an
 * <svg>), so the grid is repainted in place instead of re-encoded as a PNG
 * on every weight change.
 */
const CanvasOverlay = L.ImageOverlay.extend({
  _initImage(this: L.ImageOverlay & { _image: HTMLCanvasElement; _url: unknown; _zoomAnimated: boolean }) {
    const el = (this._image = this._url as HTMLCanvasElement);
    L.DomUtil.addClass(el, 'leaflet-image-layer');
    if (this._zoomAnimated) L.DomUtil.addClass(el, 'leaflet-zoom-animated');
    if (this.options.className) L.DomUtil.addClass(el, this.options.className);
    el.onselectstart = L.Util.falseFn as () => boolean;
    el.onmousemove = L.Util.falseFn as () => boolean;
  },
}) as unknown as new (canvas: HTMLCanvasElement, bounds: L.LatLngBoundsExpression, options?: L.ImageOverlayOptions) => L.ImageOverlay;

export interface GridLayerProps {
  grid: BangkokGrid;
  scores: Float32Array;
  pass: Uint8Array;
  anchors: PercentileAnchors;
  /** Single-category heatmap dimension, or null for the composite palette. */
  heatDimension: keyof StationRatings | null;
  districts: readonly GridDistrict[];
  pane: string;
  /** Paused during fly animations and on touch (no hover there). */
  hoverEnabled: boolean;
  onSelect: (index: number | null) => void;
  /** The selected cell shows its popup instead of the hover readout. */
  selectedIndex: number | null;
  /** Locale-aware display names for the hover readout. */
  names: { station: (id: string) => string; district: (slug: string) => string };
}

/** The painted 200 m grid: one canvas pixel per cell, stretched over Bangkok. */
export default function GridLayer(props: GridLayerProps) {
  const { grid, scores, pass, anchors, heatDimension, pane } = props;
  const map = useMap();
  const [canvas] = useState(() => {
    const c = document.createElement('canvas');
    c.width = grid.header.nx;
    c.height = grid.header.ny;
    return c;
  });

  useEffect(() => {
    const h = grid.header;
    const overlay = new CanvasOverlay(canvas, [[h.south, h.west], [h.north, h.east]], {
      pane,
      interactive: false,
      className: 'bkk-grid-canvas',
    });
    overlay.addTo(map);
    return () => {
      overlay.remove();
    };
  }, [map, canvas, grid, pane]);

  // Crisp 200 m squares once a cell is several screen pixels wide; smooth
  // below that, where pixelated down-scaling would alias.
  useMapEvents({
    zoomend: () => canvas.classList.toggle('bkk-grid-crisp', map.getZoom() >= 12),
  });
  useEffect(() => {
    canvas.classList.toggle('bkk-grid-crisp', map.getZoom() >= 12);
  }, [canvas, map]);

  useLayoutEffect(() => {
    const { nx, ny, scales } = grid.header;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const image = ctx.createImageData(nx, ny);
    const data = image.data;
    // Scores come in 0.1 steps and ratings are integers: tiny colour tables.
    const composite: [number, number, number][] = [];
    for (let b = 0; b <= 100; b++) composite.push(parseRgb(compositeToColor(b / 10, anchors)));
    const heat: [number, number, number][] = [];
    if (heatDimension) {
      for (let v = 0; v <= 10; v++) heat.push(parseRgb(scoreToColor(Math.max(1, v), heatDimension as ColorDimension)));
    }
    const plane = heatDimension && heatDimension !== 'rent' && heatDimension !== 'safety' ? grid.planes[heatDimension] : null;
    const districtValue =
      heatDimension === 'rent' || heatDimension === 'safety'
        ? props.districts.map((d) => d.ratings[heatDimension])
        : null;
    const weight = grid.planes.weight;
    const district = grid.planes.district;
    for (const i of grid.cells) {
      const o = i * 4;
      // Built-up cells near-opaque, empty fields and river faded: the map
      // shows where people live without hiding the basemap there.
      const w = weight[i] / scales.weight;
      let rgb: readonly [number, number, number];
      let alpha: number;
      if (!pass[i]) {
        rgb = FILTERED_RGB;
        alpha = 0.55;
      } else {
        if (plane) rgb = heat[plane[i]];
        else if (districtValue) rgb = heat[districtValue[district[i] - 1]];
        else rgb = composite[Math.max(0, Math.min(100, Math.round(scores[i] * 10)))];
        alpha = 0.3 + 0.55 * w;
      }
      data[o] = rgb[0];
      data[o + 1] = rgb[1];
      data[o + 2] = rgb[2];
      data[o + 3] = Math.round(alpha * 255);
    }
    ctx.putImageData(image, 0, 0);
  }, [canvas, grid, scores, pass, anchors, heatDimension, props.districts]);

  return <GridPointer {...props} />;
}

/** Hover outline + readout and click-to-select, kept out of the painted layer
 *  so moving the pointer re-renders only this. */
function GridPointer({ grid, scores, pass, districts, hoverEnabled, onSelect, selectedIndex, names }: GridLayerProps) {
  const t = useTranslations();
  const [hover, setHover] = useState<number | null>(null);
  const frame = useRef<number | undefined>(undefined);
  const pendingClick = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(
    () => () => {
      if (frame.current) cancelAnimationFrame(frame.current);
      clearTimeout(pendingClick.current);
    },
    [],
  );

  useMapEvents({
    mousemove: (e) => {
      if (!hoverEnabled) return;
      const { lat, lng } = e.latlng;
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        const i = cellAt(grid, lat, lng);
        setHover((prev) => (prev === (i >= 0 ? i : null) ? prev : i >= 0 ? i : null));
      });
    },
    mouseout: () => setHover(null),
    click: (e) => {
      const target = e.originalEvent?.target as HTMLElement | null;
      // Station dots, popups and markers handle their own clicks.
      if (target?.closest('.leaflet-interactive, .leaflet-marker-icon, .leaflet-popup')) return;
      const i = cellAt(grid, e.latlng.lat, e.latlng.lng);
      clearTimeout(pendingClick.current);
      // Same double-click guard as the district polygons: a dblclick zoom
      // must not select + fly.
      pendingClick.current = setTimeout(() => onSelect(i >= 0 ? i : null), 230);
    },
    dblclick: () => clearTimeout(pendingClick.current),
  });

  const info = useMemo(() => (hover !== null && hoverEnabled ? cellInfo(grid, hover, districts) : null), [
    grid,
    hover,
    hoverEnabled,
    districts,
  ]);
  if (!info || hover === null || hover === selectedIndex) return null;
  const station = info.stationId ? names.station(info.stationId) : null;
  const score = scores[hover];
  const walkMin = info.stationDistanceM !== null ? Math.max(1, Math.round((info.stationDistanceM * 1.3) / 75)) : null;
  // "Near X" only within walking range of the station; otherwise the district.
  const near = station && info.stationDistanceM !== null && info.stationDistanceM <= NEAR_STATION_M;
  const top = (Object.entries(info.ratings) as [keyof StationRatings, number][])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <Rectangle
      key={hover}
      bounds={cellBounds(grid.header, hover)}
      interactive={false}
      // Above the painted grid (the default overlay pane lies beneath it).
      pane="bkk-outlines"
      pathOptions={{ color: '#1d4ed8', weight: 2, fill: false }}
    >
      {/* `auto`: beside the cell, on the side with room — a readout above a
          cell near the map edge would be clipped. */}
      <Tooltip pane="tooltipPane" permanent direction="auto" offset={[14, 0]} opacity={1} className="grid-tooltip">
        <div style={{ minWidth: 190, maxWidth: 240 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>
                {near ? t('map.cellNear', { station }) : names.district(info.districtSlug)}
              </div>
              <div style={{ color: '#6b7280', fontSize: 11 }}>
                {near ? names.district(info.districtSlug) : t('map.cellTitle')}
              </div>
            </div>
            {!Number.isNaN(score) && <div style={{ fontWeight: 700, fontSize: 18, color: '#1e293b' }}>{score.toFixed(1)}</div>}
          </div>
          <div style={{ fontSize: 11, color: '#4b5563', marginTop: 4 }}>
            {top.map(([k, v]) => `${t(`shortLabels.${k}`)} ${v}`).join(' · ')}
          </div>
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
            {walkMin !== null && station
              ? t('map.cellWalk', { minutes: walkMin, station })
              : t('map.cellNoStation')}
            {' · '}
            {t('map.cellCommute', { minutes: info.minCommute })}
          </div>
          {info.weight < 0.3 && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{t('map.cellSparse')}</div>}
          {!pass[hover] && <div style={{ fontSize: 11, color: '#b45309', marginTop: 2 }}>{t('map.filteredOut')}</div>}
        </div>
      </Tooltip>
    </Rectangle>
  );
}
