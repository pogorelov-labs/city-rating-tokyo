'use client';

import { useEffect, useRef } from 'react';
import { Pane, Polygon, Tooltip } from 'react-leaflet';
import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import { useCity } from '@/lib/city-context';
import { useAppStore, useCityActions } from '@/lib/store';
import { formatRentShort } from '@/lib/cities';
import { stationDisplayName } from '@/lib/station-name';
import { useDelayedHover } from '@/lib/use-delayed-hover';
import RentNote from './RentNote';
import type { ScoredArea } from './StationAreaLayer';

type LatLng = [number, number];
type Shape = { polygons: LatLng[][][] };

export default function DistrictLayer({ isDistrictLevel, scored, shapes, passing, selected, hovered, heatmapMode, isTouch, thumbnails, colorFor, reasonsFor }: {
  isDistrictLevel: boolean; scored: ScoredArea[]; shapes: Record<string, Shape>; passing: Set<string>;
  selected: string | null; hovered: string | null; heatmapMode: boolean; isTouch: boolean;
  thumbnails: Record<string, { thumb: string; lqip: string }>;
  colorFor: (area: ScoredArea) => string; reasonsFor: (area: ScoredArea) => string[];
}) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const { setSelectedStation, setHoveredStation } = useCityActions();
  const hoverClear = useDelayedHover(120);
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
                          {d.rent_provenance && <RentNote rent={d.rent_provenance} compact />}
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

  </>;
}
