'use client';

import { useMemo } from 'react';
import { CircleMarker, Pane, Polyline, Tooltip } from 'react-leaflet';
import type { Locale } from '@/i18n/routing';
import type { RailLine, RailStation } from '@/lib/types';
import { stationAreaKey } from '@/lib/area-key';

type LatLng = [number, number];
type RailData = { lines: (RailLine & { paths: LatLng[][] })[]; stations: RailStation[] };

export default function BangkokRailLayer({ rail, showRail, zoom, isDistrictLevel, isTouch, stationRadius, locale, lineChip, setSelectedStation }: {
  rail: RailData; showRail: boolean; zoom: number; isDistrictLevel: boolean; isTouch: boolean; stationRadius: number;
  locale: Locale; lineChip: (id: string) => { name: string; color: string } | null;
  setSelectedStation: (key: string | null) => void;
}) {
  const lineById = useMemo(() => new Map(rail.lines.map((line) => [line.id, line])), [rail]);
  return <>
        {showRail && (
          <Pane name="bkk-rail" style={{ zIndex: 430, pointerEvents: 'none' }}>
            {rail.lines.map((line) =>
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
            {rail.stations.map((s) => {
              const interchange = s.lines.length > 1;
              const color = lineById.get(s.lines[0])?.color ?? '#374151';
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
                        {locale === 'ja' && s.name_ja ? s.name_ja : s.name_en}{' '}
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

  </>;
}
