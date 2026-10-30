import type { Map as LibreMap, StyleSpecification, ExpressionSpecification } from 'maplibre-gl';
import { areaFeatures, EMPTY, railFeatures, stationFeatures } from './map-data';
import { MAP_COLORS } from './map-colors';

export const RAIL_LAYERS = ['bkk-rail-casing', 'bkk-rail', 'bkk-station-focus', 'bkk-stations', 'bkk-station-cores', 'bkk-station-labels'];
const selected: ExpressionSpecification = ['boolean', ['feature-state', 'selected'], false];
const hovered: ExpressionSpecification = ['boolean', ['feature-state', 'hover'], false];
const compared: ExpressionSpecification = ['boolean', ['feature-state', 'compared'], false];

/** Geometry is installed once. Score/selection changes only update paint state. */
export function installMapLayers(map: LibreMap, style: StyleSpecification) {
  const before = style.layers.find((l) => l.type === 'line')?.id ?? style.layers.find((l) => l.type === 'symbol')?.id;
  const vectorSource = Object.entries(style.sources).find(([, s]) => s.type === 'vector')?.[0];
  // Tile feature IDs are numeric unless promoted from properties. Our typed
  // string keys must survive worker tiling for paint/selection state to apply.
  map.addSource('bkk-areas', { type: 'geojson', data: areaFeatures, promoteId: 'key' });
  map.addLayer({ id: 'bkk-area-fill', type: 'fill', source: 'bkk-areas', paint: {
    'fill-color': ['coalesce', ['feature-state', 'color'], '#cbd5e1'],
    'fill-opacity': ['interpolate', ['linear'], ['zoom'], 10, ['coalesce', ['feature-state', 'opacity'], .55], 15, ['*', ['coalesce', ['feature-state', 'opacity'], .55], .5], 18, .16],
  } }, before);
  map.addLayer({ id: 'bkk-area-outline', type: 'line', source: 'bkk-areas', paint: {
    'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 10, .6, 14, 1.4], 'line-opacity': .8,
  } }, before);
  map.addLayer({ id: 'bkk-area-context', type: 'line', source: 'bkk-areas', filter: ['==', ['get', 'kind'], 'district'], paint: {
    'line-color': '#64748b', 'line-width': .8, 'line-opacity': .35, 'line-dasharray': [3, 3],
  } }, before);
  // Ordinary city parks are grass landcover, not protected-area `park` data.
  // Reuse the basemap tiles and keep physical greenery/water above score tint.
  if (vectorSource) map.addLayer({ id: 'bkk-landcover', type: 'fill', source: vectorSource, 'source-layer': 'landcover', minzoom: 10,
    filter: ['match', ['get', 'class'], ['grass', 'wetland'], true, false], paint: {
      'fill-color': ['match', ['get', 'class'], 'wetland', MAP_COLORS.wetland, MAP_COLORS.grass], 'fill-opacity': 1,
    } }, before);
  for (const id of ['park', 'landcover_wood', 'water']) if (map.getLayer(id)) map.moveLayer(id, before);
  for (const id of ['bkk-area-outline', 'bkk-area-context']) map.moveLayer(id, before);
  map.addLayer({ id: 'bkk-area-focus-fill', type: 'fill', source: 'bkk-areas', layout: { visibility: 'none' }, paint: {
    'fill-color': ['case', selected, MAP_COLORS.selected, compared, MAP_COLORS.compared, MAP_COLORS.selected],
    'fill-opacity': ['case', selected, .14, compared, .08, hovered, .06, 0], 'fill-opacity-transition': { duration: 0 },
  } }, before);
  map.addSource('bkk-labels', { type: 'geojson', data: EMPTY });
  map.addLayer({ id: 'bkk-labels', type: 'symbol', source: 'bkk-labels', maxzoom: 15, filter: ['==', ['get', 'kind'], 'district'], layout: {
    'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 10, 11, 13, 15],
    'text-max-width': 11, 'text-padding': 14, 'text-letter-spacing': .04,
  }, paint: { 'text-color': '#334155', 'text-halo-color': '#ffffff', 'text-halo-width': 2 } });
  if (vectorSource) map.addLayer({ id: 'bkk-park-labels', type: 'symbol', source: vectorSource, 'source-layer': 'poi', minzoom: 12,
    filter: ['==', ['get', 'class'], 'park'], layout: {
      'text-field': ['coalesce', ['get', 'name:en'], ['get', 'name_en'], ['get', 'name'], ''],
      'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 12, 11, 16, 13],
      'text-max-width': 12, 'text-padding': 12, 'symbol-sort-key': ['coalesce', ['get', 'rank'], 100],
    }, paint: { 'text-color': MAP_COLORS.parkLabel, 'text-halo-color': MAP_COLORS.paper, 'text-halo-width': 1.5 } });
  map.addSource('bkk-rail', { type: 'geojson', data: railFeatures });
  map.addLayer({ id: 'bkk-rail-casing', type: 'line', source: 'bkk-rail', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: {
    'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 3.5, 15, 6.5], 'line-opacity': .9,
  } });
  map.addLayer({ id: 'bkk-rail', type: 'line', source: 'bkk-rail', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: {
    'line-color': ['get', 'color'], 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 15, 3.5],
  } });
  map.addSource('bkk-stations', { type: 'geojson', data: stationFeatures, promoteId: 'id' });
  map.addLayer({ id: 'bkk-station-focus', type: 'circle', source: 'bkk-stations', minzoom: 10, paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 7, 15, 12], 'circle-color': '#ffffff',
    'circle-stroke-color': ['case', selected, MAP_COLORS.selected, compared, MAP_COLORS.compared, MAP_COLORS.selected], 'circle-stroke-width': 2,
    'circle-opacity': ['case', ['any', selected, compared, hovered], .9, 0], 'circle-stroke-opacity': ['case', ['any', selected, compared, hovered], 1, 0],
    'circle-pitch-alignment': 'viewport',
  } });
  map.addLayer({ id: 'bkk-stations', type: 'circle', source: 'bkk-stations', minzoom: 10, paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 2.5, 14, ['case', ['get', 'interchange'], 7, 5]],
    'circle-color': '#ffffff', 'circle-stroke-width': ['case', ['get', 'interchange'], 2.5, 2], 'circle-stroke-color': ['get', 'color'], 'circle-pitch-alignment': 'viewport',
  } });
  map.addLayer({ id: 'bkk-station-cores', type: 'circle', source: 'bkk-stations', minzoom: 12, filter: ['==', ['get', 'interchange'], true], paint: {
    'circle-radius': 2, 'circle-color': '#334155', 'circle-pitch-alignment': 'viewport',
  } });
  map.addLayer({ id: 'bkk-station-labels', type: 'symbol', source: 'bkk-stations', minzoom: 12, layout: {
    'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 12, 11, 15, 13],
    'text-variable-anchor': ['left', 'right', 'top', 'bottom'], 'text-radial-offset': .9, 'text-justify': 'auto', 'text-padding': 8,
    'symbol-sort-key': ['case', ['get', 'interchange'], 0, 1],
  }, paint: { 'text-color': '#334155', 'text-halo-color': '#ffffff', 'text-halo-width': 2 } });
  map.addLayer({ id: 'bkk-area-focus-halo', type: 'line', source: 'bkk-areas', paint: {
    'line-color': '#ffffff', 'line-width': ['case', selected, 6, compared, 5, 3.5], 'line-opacity': ['case', ['any', selected, compared, hovered], .9, 0],
  } });
  map.addLayer({ id: 'bkk-area-focus', type: 'line', source: 'bkk-areas', paint: {
    'line-color': MAP_COLORS.selected, 'line-width': ['case', selected, 3, 1.5], 'line-opacity': ['case', selected, 1, ['all', hovered, ['!', compared]], .9, 0],
  } });
  map.addLayer({ id: 'bkk-area-compare', type: 'line', source: 'bkk-areas', paint: {
    'line-color': MAP_COLORS.compared, 'line-width': 2.5, 'line-opacity': ['case', ['all', compared, ['!', selected]], 1, 0], 'line-dasharray': [2, 2],
  } });
  for (const id of ['bkk-hover', 'bkk-selected']) {
    map.addSource(id, { type: 'geojson', data: EMPTY });
    map.addLayer({ id: `${id}-fill`, type: 'fill', source: id, paint: { 'fill-color': ['case', ['==', ['get', 'role'], 'compared'], MAP_COLORS.compared, MAP_COLORS.selected], 'fill-opacity': id === 'bkk-selected' ? .14 : .06 } }, before);
    map.addLayer({ id: `${id}-halo`, type: 'line', source: id, paint: { 'line-color': '#ffffff', 'line-width': id === 'bkk-selected' ? 6 : 3.5, 'line-opacity': .9 } });
    map.addLayer({ id, type: 'line', source: id, filter: ['!=', ['get', 'role'], 'compared'], paint: { 'line-color': MAP_COLORS.selected, 'line-width': id === 'bkk-selected' ? 3 : 1.5 } });
  }
  map.addLayer({ id: 'bkk-cell-compare', type: 'line', source: 'bkk-selected', filter: ['==', ['get', 'role'], 'compared'], paint: { 'line-color': MAP_COLORS.compared, 'line-width': 2.5, 'line-dasharray': [2, 2] } });
  map.addSource('bkk-spots', { type: 'geojson', data: EMPTY });
  map.addLayer({ id: 'bkk-spots', type: 'circle', source: 'bkk-spots', paint: { 'circle-radius': 11, 'circle-color': '#1e293b', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } });
  map.addLayer({ id: 'bkk-spot-numbers', type: 'symbol', source: 'bkk-spots', layout: { 'text-field': ['get', 'rank'], 'text-font': ['Noto Sans Regular'], 'text-size': 12, 'text-allow-overlap': true }, paint: { 'text-color': '#ffffff' } });
  if (vectorSource) map.addLayer({ id: 'bkk-buildings', type: 'fill-extrusion', source: vectorSource, 'source-layer': 'building', minzoom: 14,
    filter: ['!=', ['get', 'hide_3d'], true], paint: { 'fill-extrusion-color': MAP_COLORS.building, 'fill-extrusion-opacity': 1,
      'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, ['coalesce', ['get', 'render_height'], 0]],
      'fill-extrusion-base': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, ['coalesce', ['get', 'render_min_height'], 0]] } }, 'bkk-labels');
}
