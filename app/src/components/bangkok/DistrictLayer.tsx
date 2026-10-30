'use client';

import { useEffect, useRef } from 'react';
import { Pane, Polygon, Tooltip } from 'react-leaflet';
import { useTranslations } from 'next-intl';
import { useCity } from '@/lib/city-context';
import { useAppStore, useCityActions } from '@/lib/store';
import { useDelayedHover } from '@/lib/use-delayed-hover';
import CompactAreaCard from '@/components/area/CompactAreaCard';
import type { WeightConfig } from '@/lib/types';
import type { ScoredArea } from './StationAreaLayer';

type LatLng = [number, number];
type Shape = { polygons: LatLng[][][] };

export default function DistrictLayer({ isDistrictLevel, scored, shapes, passing, selected, hovered, heatmapMode, isTouch, thumbnails, snippets, weights, colorFor, reasonsFor }: {
  isDistrictLevel: boolean; scored: ScoredArea[]; shapes: Record<string, Shape>; passing: Set<string>;
  selected: string | null; hovered: string | null; heatmapMode: boolean; isTouch: boolean;
  thumbnails: Record<string, { thumb: string; lqip: string }>;
  snippets: Record<string, string>; weights: WeightConfig;
  colorFor: (area: ScoredArea) => string; reasonsFor: (area: ScoredArea) => string[];
}) {
  const t = useTranslations();
  const city = useCity();
  const { setSelectedStation, setHoveredStation } = useCityActions();
  const hoverClear = useDelayedHover();
  const pendingClick = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(pendingClick.current), []);
  const FILTERED_FILL = '#E5E7EB';
  return <>
        {/* ── districts: the choropleth on their level, context outlines otherwise ── */}
        <Pane name="bkk-districts" style={{ zIndex: 410 }}>
          {isDistrictLevel &&
            scored.map((d) => {
              const shape = shapes[d.slug];
              if (!shape) return null;
              const pass = passing.has(d.slug);
              const isSel = d.slug === selected;
              const isHov = d.slug === hovered;
              const fill = pass ? colorFor(d) : FILTERED_FILL;
              const reasons = pass ? [] : reasonsFor(d);
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
                      hoverClear.cancel();
                      setHoveredStation(d.slug);
                      const thumb = thumbnails[d.slug]?.thumb;
                      if (thumb) {
                        const img = new Image();
                        img.src = thumb;
                      }
                    },
                    mouseout: () => {
                      hoverClear.schedule(() => {
                        if (useAppStore.getState().cities[city.id].hoveredStation === d.slug) setHoveredStation(null);
                      });
                    },
                  }}
                >
                  {!isTouch && !isSel && (
                    // Explicit pane: inside a custom <Pane> react-leaflet would put
                    // the tooltip in that pane, under its own polygons.
                    <Tooltip pane="tooltipPane" sticky direction="top" offset={[0, -12]} opacity={1} className="station-tooltip">
                      <div>
                        <CompactAreaCard area={d} city="bangkok" score={d.score} weights={weights}
                          thumbnail={thumbnails[d.slug]} snippet={snippets[d.slug]} variant="hover" />
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

  </>;
}
