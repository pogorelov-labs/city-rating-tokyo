'use client';

import { Pane, Polygon, Rectangle } from 'react-leaflet';
import { cellBounds, type BangkokGrid } from '@/lib/bangkok-grid';
import type { AreaLevel, MapStation } from '@/lib/types';

type LatLng = [number, number];
type Shape = LatLng[][][];
type Geometry = Record<string, { polygons: Shape }>;

export default function BangkokOutlines({ districts, geometry, level, isDistrictLevel, heatmapMode, isFlying, topDistricts, topAreas, selected, hovered, shapeFor, hoveredShape, hoveredCell, selectedCell, grid, compareStations }: {
  districts: MapStation[]; geometry: Geometry; level: AreaLevel; isDistrictLevel: boolean; heatmapMode: boolean; isFlying: boolean;
  topDistricts: Set<string>; topAreas: Set<string>; selected: string | null; hovered: string | null; shapeFor: (key: string) => Shape | undefined;
  hoveredShape: Shape | undefined; hoveredCell: number | null; selectedCell: number | null; grid: BangkokGrid | null; compareStations: string[];
}) {
  return <>
        {/* Outline overlays: district context lines, top-5 pulse, hovered,
            selected, compared (non-interactive). */}
        <Pane name="bkk-outlines" style={{ zIndex: 420, pointerEvents: 'none' }}>
          {!isDistrictLevel &&
            districts.map((d) =>
              geometry[d.slug] ? (
                <Polygon
                  key={`ctx-${d.slug}`}
                  positions={geometry[d.slug].polygons}
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

  </>;
}
