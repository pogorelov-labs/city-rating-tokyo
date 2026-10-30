'use client';

import CompactAreaCard from '@/components/area/CompactAreaCard';
import { useDelayedHover } from '@/lib/use-delayed-hover';

import { useEffect, useRef } from 'react';
import { Pane, Polygon, Tooltip } from 'react-leaflet';
import { useTranslations } from 'next-intl';
import type { MapStation, WeightConfig } from '@/lib/types';

type LatLng = [number, number];
export interface AreaShape {
  polygons: LatLng[][][];
  bbox: [LatLng, LatLng];
}

export type ScoredArea = MapStation & { score: number | null };

interface Props {
  areas: ScoredArea[];
  weights: WeightConfig;
  thumbnails: Record<string, { thumb: string; lqip: string }>;
  snippets: Record<string, string>;
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
  weights, thumbnails, snippets,
  shapes,
  passing,
  colorFor,
  filteredFill,
  selected,
  hovered,
  heatmapMode,
  isTouch,
  reasonsFor,
  onSelect,
  onHover,
}: Props) {
  const t = useTranslations();
  const hoverClear = useDelayedHover();
  const pendingClick = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(
    () => () => {
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
                hoverClear.cancel();
                onHover(a.slug);
              },
              mouseout: () => {
                hoverClear.schedule(() => onHover(null));
              },
            }}
          >
            {!isTouch && !isSel && (
              // Explicit pane, or react-leaflet puts it under this pane's polygons.
              <Tooltip pane="tooltipPane" sticky direction="top" offset={[0, -12]} opacity={1} className="station-tooltip">
                <div>
                  <CompactAreaCard area={a} city="bangkok" score={a.score} weights={weights}
                    thumbnail={thumbnails[a.slug]} snippet={snippets[a.slug]} variant="hover" />
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
