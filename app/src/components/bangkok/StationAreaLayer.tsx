'use client';

import { useEffect, useRef } from 'react';
import { Pane, Polygon, Tooltip } from 'react-leaflet';
import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import type { MapStation } from '@/lib/types';
import { formatRentShort } from '@/lib/cities';
import { stationDisplayName } from '@/lib/station-name';

type LatLng = [number, number];
export interface AreaShape {
  polygons: LatLng[][][];
  bbox: [LatLng, LatLng];
}

export type ScoredArea = MapStation & { score: number | null };

interface Props {
  areas: ScoredArea[];
  shapes: Record<string, AreaShape>;
  passing: Set<string>;
  colorFor: (a: ScoredArea) => string;
  filteredFill: string;
  selected: string | null;
  hovered: string | null;
  heatmapMode: boolean;
  isTouch: boolean;
  /** Filtered-out explanation for the tooltip (empty when the area passes). */
  reasonsFor: (a: ScoredArea) => string[];
  lineChip: (lineId: string) => { name: string; color: string } | null;
  districtName: (slug: string) => string;
  onSelect: (key: string | null) => void;
  onHover: (key: string | null) => void;
}

/**
 * Station-area choropleth: the walkable neighbourhood (≤ 800 m, nearest
 * station) of every rail station inside Bangkok. Land farther than 800 m
 * from any station is deliberately left unpainted.
 */
export default function StationAreaLayer({
  areas,
  shapes,
  passing,
  colorFor,
  filteredFill,
  selected,
  hovered,
  heatmapMode,
  isTouch,
  reasonsFor,
  lineChip,
  districtName,
  onSelect,
  onHover,
}: Props) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const hoverClear = useRef<ReturnType<typeof setTimeout>>(undefined);
  const pendingClick = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(
    () => () => {
      clearTimeout(hoverClear.current);
      clearTimeout(pendingClick.current);
    },
    [],
  );

  return (
    <Pane name="bkk-areas" style={{ zIndex: 412 }}>
      {areas.map((a) => {
        const shape = shapes[a.slug.slice(3)];
        if (!shape) return null;
        const pass = passing.has(a.slug);
        const isSel = a.slug === selected;
        const isHov = a.slug === hovered;
        const names = stationDisplayName(a, locale);
        const reasons = pass ? [] : reasonsFor(a);
        return (
          <Polygon
            key={a.slug}
            positions={shape.polygons}
            pathOptions={{
              color: '#ffffff',
              weight: 1,
              opacity: 0.9,
              fillColor: pass ? colorFor(a) : filteredFill,
              fillOpacity: isSel || isHov ? 0.85 : pass ? (heatmapMode ? 0.68 : 0.62) : 0.45,
              dashArray: pass ? undefined : '3 3',
            }}
            eventHandlers={{
              click: () => {
                clearTimeout(pendingClick.current);
                pendingClick.current = setTimeout(() => {
                  onSelect(isSel ? null : a.slug);
                  window.umami?.track('map-click', { station: a.slug, city: 'bangkok' });
                }, 230);
              },
              dblclick: () => clearTimeout(pendingClick.current),
              mouseover: () => {
                clearTimeout(hoverClear.current);
                onHover(a.slug);
              },
              mouseout: () => {
                hoverClear.current = setTimeout(() => onHover(null), 120);
              },
            }}
          >
            {!isTouch && !isSel && (
              // Explicit pane, or react-leaflet puts it under this pane's polygons.
              <Tooltip pane="tooltipPane" sticky direction="top" offset={[0, -12]} opacity={1} className="district-tooltip">
                <div style={{ minWidth: 190, maxWidth: 250 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{names.primary}</div>
                      <div style={{ color: '#6b7280', fontSize: 12 }}>{names.secondary}</div>
                    </div>
                    {a.score !== null && (
                      <div style={{ fontWeight: 700, fontSize: 18, color: '#1e293b' }}>{a.score.toFixed(1)}</div>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {(a.line_ids ?? []).map((lid) => {
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
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
                    {a.district && districtName(a.district)}
                    {a.rent_1k != null && <> · ~{formatRentShort('bangkok', a.rent_1k)}/mo</>}
                    {a.min_transit != null && <> · {t('map.cellCommute', { minutes: a.min_transit })}</>}
                  </div>
                  {reasons.length > 0 && (
                    <div style={{ fontSize: 11, color: '#b45309', marginTop: 4 }}>
                      {t('map.filteredOut')}: {reasons.join(', ')}
                    </div>
                  )}
                </div>
              </Tooltip>
            )}
          </Polygon>
        );
      })}
    </Pane>
  );
}
