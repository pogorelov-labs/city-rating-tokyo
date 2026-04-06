'use client';

import { useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { MapStation, WeightConfig } from '@/lib/types';
import { calculateWeightedScore, scoreToColor, ColorDimension } from '@/lib/scoring';
import { useAppStore } from '@/lib/store';
import Link from 'next/link';

function FlyToStation({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lng], 14, { duration: 0.8 });
  }, [map, lat, lng]);
  return null;
}

/**
 * Return a darker variant of an `rgb(r, g, b)` string produced by `scoreToColor`.
 * Used for the fallback gradient header so we can't accidentally produce invalid
 * CSS like `${rgbString}cc` (which would be silently dropped by the browser).
 */
function darkenRgb(rgb: string, factor = 0.7): string {
  const match = rgb.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if (!match) return rgb;
  const r = Math.round(Number(match[1]) * factor);
  const g = Math.round(Number(match[2]) * factor);
  const b = Math.round(Number(match[3]) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}

interface MapViewProps {
  stations: MapStation[];
  thumbnails?: Record<string, string>;
  snippets?: Record<string, string>;
}

export default function MapView({ stations, thumbnails = {}, snippets = {} }: MapViewProps) {
  const weights = useAppStore((s) => s.weights);
  const selectedStation = useAppStore((s) => s.selectedStation);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const hoveredStation = useAppStore((s) => s.hoveredStation);
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const compareStations = useAppStore((s) => s.compareStations);
  const addCompareStation = useAppStore((s) => s.addCompareStation);
  const removeCompareStation = useAppStore((s) => s.removeCompareStation);

  const scoredStations = useMemo(() => {
    return stations.map((s) => ({
      ...s,
      score: s.ratings ? calculateWeightedScore(s.ratings, weights) : null,
    }));
  }, [stations, weights]);

  const flyTarget = useMemo(() => {
    if (!selectedStation) return null;
    return scoredStations.find((s) => s.slug === selectedStation);
  }, [selectedStation, scoredStations]);

  // Station to highlight with halo: selected (from click/search) or hovered (from list)
  const highlightedSlug = selectedStation || hoveredStation;
  const highlightedStation = useMemo(() => {
    if (!highlightedSlug) return null;
    return scoredStations.find((s) => s.slug === highlightedSlug);
  }, [highlightedSlug, scoredStations]);

  return (
    <MapContainer
      center={[35.6762, 139.7503]}
      zoom={12}
      className="h-full w-full"
      zoomControl={false}
      attributionControl={false}
    >
      <TileLayer
        attribution=""
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      {flyTarget && <FlyToStation lat={flyTarget.lat} lng={flyTarget.lng} />}
      {scoredStations.map((station) => {
        const score = station.score;
        const thumb = thumbnails[station.slug];
        const snippet = snippets[station.slug];

        // Heatmap mode: color by selected dimension
        let displayValue: number | null = null;
        if (heatmapMode && station.ratings) {
          displayValue = heatmapDimension === 'composite'
            ? score
            : (station.ratings as unknown as Record<string, number>)[heatmapDimension] ?? null;
        }

        const color = heatmapMode
          ? (displayValue !== null
              ? scoreToColor(displayValue, heatmapDimension as ColorDimension)
              : '#9CA3AF')
          : (score !== null ? scoreToColor(score) : '#9CA3AF');
        const radius = heatmapMode
          ? (displayValue !== null ? 14 + displayValue * 1.2 : 0)
          : (score !== null ? 6 + score * 0.5 : 5);

        if (heatmapMode && displayValue === null) return null;

        const isCompared = compareStations.includes(station.slug);
        const isSelected = station.slug === selectedStation;
        const isHovered = station.slug === hoveredStation;
        const isHighlighted = isSelected || isHovered;

        // Selected/hovered stations: bigger, bolder stroke in brand blue
        const effectiveRadius = isHighlighted ? radius + 3 : radius;
        const strokeColor = isSelected
          ? '#1d4ed8'
          : isHovered
            ? '#2563eb'
            : isCompared
              ? '#7c3aed'
              : heatmapMode
                ? color
                : '#374151';
        const strokeWeight = isSelected
          ? 3.5
          : isHovered
            ? 2.5
            : isCompared
              ? 3
              : heatmapMode
                ? 0
                : 1;

        return (
          <CircleMarker
            key={station.slug}
            center={[station.lat, station.lng]}
            radius={effectiveRadius}
            pathOptions={{
              fillColor: color,
              color: strokeColor,
              weight: strokeWeight,
              opacity: heatmapMode && !isHighlighted && !isCompared ? 0 : 0.9,
              fillOpacity: isHighlighted ? 1 : (heatmapMode ? 0.45 : 0.85),
            }}
            eventHandlers={{
              click: () => {
                setSelectedStation(station.slug);
                window.umami?.track('map-click', { station: station.slug });
              },
            }}
          >
            {/* Rich hover tooltip */}
            <Tooltip
              direction="top"
              offset={[0, -10]}
              opacity={1}
              className="station-tooltip"
            >
              <div style={{ width: 260 }}>
                {thumb ? (
                  <img
                    src={thumb}
                    alt={station.name_en}
                    loading="lazy"
                    onError={() => window.umami?.track('error', { category: 'image', station: station.slug, context: 'tooltip' })}
                    style={{
                      width: '100%',
                      height: 100,
                      objectFit: 'cover',
                      borderRadius: '6px 6px 0 0',
                      display: 'block',
                    }}
                  />
                ) : (
                  <div
                    aria-hidden
                    style={{
                      width: '100%',
                      height: 60,
                      backgroundImage: score !== null
                        ? `linear-gradient(135deg, ${color}, ${darkenRgb(color)})`
                        : 'linear-gradient(135deg, #e5e7eb, #9ca3af)',
                      borderRadius: '6px 6px 0 0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontFamily: 'serif',
                      fontWeight: 700,
                      fontSize: 26,
                      letterSpacing: 2,
                      textShadow: '0 1px 3px rgba(0,0,0,0.25)',
                    }}
                  >
                    {station.name_jp}
                  </div>
                )}
                <div style={{ padding: '8px 10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{station.name_en}</div>
                      <div style={{ color: '#6b7280', fontSize: 12 }}>{station.name_jp}</div>
                    </div>
                    {score !== null && (
                      <div style={{ fontWeight: 700, fontSize: 18, color }}>
                        {score.toFixed(1)}
                      </div>
                    )}
                  </div>
                  {snippet && (
                    <div style={{
                      fontSize: 11,
                      color: '#4b5563',
                      marginTop: 6,
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {snippet}
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
                    {station.line_count} lines
                    {station.rent_1k && (
                      <> · ~¥{(station.rent_1k / 1000).toFixed(0)}k/mo</>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: '#2563eb', marginTop: 4 }}>
                    Click for details →
                  </div>
                </div>
              </div>
            </Tooltip>

            {/* Click popup */}
            <Popup>
              <div className="min-w-[180px]">
                <div className="font-bold text-base">
                  {station.name_en}
                </div>
                <div className="text-gray-500 text-sm mb-1">
                  {station.name_jp}
                </div>
                {score !== null ? (
                  <>
                    <div className="text-lg font-bold" style={{ color }}>
                      {score.toFixed(1)} / 10
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      {station.line_count} lines
                    </div>
                    {station.rent_1k && (
                      <div className="text-xs">
                        Rent: ~&yen;{(station.rent_1k / 1000).toFixed(0)}k/mo
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <Link
                        href={`/station/${station.slug}`}
                        className="text-blue-600 text-xs hover:underline"
                        data-umami-event="view-details"
                        data-umami-event-station={station.slug}
                      >
                        View details &rarr;
                      </Link>
                      {isCompared ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); removeCompareStation(station.slug); }}
                          className="text-red-500 text-xs hover:underline"
                        >
                          Remove compare
                        </button>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); addCompareStation(station.slug); }}
                          className="text-purple-600 text-xs hover:underline disabled:opacity-40"
                          disabled={compareStations.length >= 3}
                        >
                          + Compare
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-gray-400">
                    {station.line_count} lines &middot; Data coming soon
                  </div>
                )}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
      {/* Pulsating halo ring under the currently selected/hovered station.
          `className` must be a top-level prop — react-leaflet forwards top-level
          props to Leaflet's CircleMarker constructor, but className inside
          `pathOptions` gets dropped by Leaflet's setStyle() which only updates
          stroke/fill attributes. With className set at the constructor level,
          Leaflet's _initPath applies it to the SVG path and the CSS keyframes
          animation can run. */}
      {highlightedStation && (
        <CircleMarker
          key={`halo-${highlightedStation.slug}`}
          center={[highlightedStation.lat, highlightedStation.lng]}
          radius={18}
          interactive={false}
          className="station-halo"
          pathOptions={{
            color: '#2563eb',
            weight: 2,
            fillColor: '#2563eb',
            fillOpacity: 0.15,
          }}
        />
      )}
    </MapContainer>
  );
}
