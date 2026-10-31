import type { StyleSpecification } from 'maplibre-gl';

export const MAP_COLORS = {
  paper: '#f5f4ef',
  park: '#c9d6c1', grass: '#d5dfcb', wood: '#b4c7b0', wetland: '#c5d8cf',
  water: '#bdd2d8', waterLine: '#92b6c2',
  building: '#e4e2dc', buildingEdge: '#cecac0',
  selected: '#1d4ed8', compared: '#7c3aed', parkLabel: '#35533d',
} as const;

/** Keep geographic context quiet; analytical hues come from the shared scorer. */
export function analyticalCityStyle(style: StyleSpecification): StyleSpecification {
  return { ...style, layers: style.layers
    // These provider shield filters compare missing route numbers.
    .filter((l) => !['highway-shield-non-us', 'highway-shield-us-interstate', 'road_shield_us'].includes(l.id))
    .map((layer) => {
      if (layer.type === 'background') return { ...layer, paint: { ...layer.paint, 'background-color': MAP_COLORS.paper } };
      if (layer.type === 'fill') {
        const color = ({ park: MAP_COLORS.park, water: MAP_COLORS.water, landcover_wood: MAP_COLORS.wood,
          building: MAP_COLORS.building, landuse_residential: '#eeece5' } as Record<string, string>)[layer.id];
        if (color) return { ...layer, paint: { ...layer.paint, 'fill-color': color,
          ...(layer.id === 'building' ? { 'fill-outline-color': MAP_COLORS.buildingEdge } : {}) } };
      }
      if (layer.id === 'waterway' && layer.type === 'line') return { ...layer, paint: { ...layer.paint, 'line-color': MAP_COLORS.waterLine } };
      if (layer.id.startsWith('water') && layer.type === 'symbol') return { ...layer,
        layout: { ...layer.layout, 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 11, 10, 16, 12, 18, 13] },
        paint: { ...layer.paint, 'text-color': '#3d5964', 'text-halo-color': MAP_COLORS.paper, 'text-halo-width': 1.5 } };
      return layer;
    }) };
}

export const gridTintOpacity = (zoom: number) => Math.max(.32, Math.min(.92, .92 - (zoom - 11) * .0925));
