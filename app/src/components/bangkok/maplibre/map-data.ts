import type { Feature, FeatureCollection, Geometry } from 'geojson';
import geometry from '@/data/bangkok/geometry.json';
import areaGeometry from '@/data/bangkok/station-geometry.json';
import rail from '@/data/bangkok/rail.json';
import type { MapStation } from '@/lib/types';
import { cellBounds, type GridHeader } from '@/lib/bangkok-grid';

type Shape = { polygons: number[][][][] };
const districtShapes = geometry as Record<string, Shape>;
const stationShapes = areaGeometry as Record<string, Shape>;
export const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
export const collection = (features: Feature[]): FeatureCollection => ({ type: 'FeatureCollection', features });
export function areaFeature(key: string): Feature | null {
  const shape = key.startsWith('st.') ? stationShapes[key.slice(3)] : districtShapes[key];
  return shape ? { type: 'Feature', id: key, properties: { key, kind: key.startsWith('st.') ? 'station' : 'district' },
    geometry: { type: 'MultiPolygon', coordinates: shape.polygons.map((polygon) => polygon.map((ring) => ring.map(([lat, lng]) => [lng, lat]))) } } : null;
}
export function cellFeature(h: GridHeader, i: number): Feature {
  const [[s, w], [n, e]] = cellBounds(h, i);
  return { type: 'Feature', properties: { key: `cell.${i}` }, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } };
}
export const areaFeatures = collection([...Object.keys(districtShapes), ...Object.keys(stationShapes).map((s) => `st.${s}`)].map((s) => areaFeature(s)!));
export const railFeatures = collection(rail.lines.flatMap((line) => line.paths.map((path) => ({
  type: 'Feature' as const, properties: { color: line.color }, geometry: { type: 'LineString', coordinates: path.map(([lat, lng]) => [lng, lat]) } as Geometry,
}))));
const colors = new Map(rail.lines.map((line) => [line.id, line.color]));
// Connected stations such as Asok/Sukhumvit have separate physical IDs but
// share one station area. Recognize the interchange across those IDs.
const areaLines = new Map<string, Set<string>>();
export const stationIdsByArea = new Map<string, string[]>();
for (const s of rail.stations) if (s.area) {
  const lines = areaLines.get(s.area) ?? new Set<string>();
  s.lines.forEach((line) => lines.add(line)); areaLines.set(s.area, lines);
  const key = `st.${s.area}`; stationIdsByArea.set(key, [...(stationIdsByArea.get(key) ?? []), s.id]);
}
export const stationFeatures = collection(rail.stations.map((s) => ({
  type: 'Feature', id: s.id, properties: { id: s.id, key: s.area ? `st.${s.area}` : '', district: s.district ?? '', name: s.name_en, name_ja: s.name_ja || s.name_en, color: colors.get(s.lines[0]) ?? '#475569', interchange: (s.area ? areaLines.get(s.area)?.size ?? s.lines.length : s.lines.length) > 1 },
  geometry: { type: 'Point', coordinates: [s.lng, s.lat] },
})));
export function labelFeatures(areas: MapStation[], name: (a: MapStation) => string) {
  return collection(areas.map((a) => ({ type: 'Feature', id: a.slug, properties: { name: name(a), kind: a.slug.startsWith('st.') ? 'station' : 'district' }, geometry: { type: 'Point', coordinates: [a.lng, a.lat] } })));
}
