import type { BangkokGrid, GridDistrict } from './bangkok-grid';
import type { StationRatings } from './types';
import { compositeToColor, scoreToColor, type PercentileAnchors, type ColorDimension } from './scoring';

const rgb = (css: string): number[] => css.match(/\d+/g)?.map(Number) ?? [156, 163, 175];
const FILTERED_RGB = [229, 231, 235];

/** Identical cell colors for the Leaflet canvas and the MapLibre texture. */
export function gridPixels(grid: BangkokGrid, scores: Float32Array, pass: Uint8Array,
  anchors: PercentileAnchors, dimension: keyof StationRatings | null, districts: readonly GridDistrict[],
  target: Uint8Array | Uint8ClampedArray = new Uint8Array(grid.header.nx * grid.header.ny * 4)): Uint8Array | Uint8ClampedArray {
  target.fill(0);
  const composite = Array.from({ length: 101 }, (_, b) => rgb(compositeToColor(b / 10, anchors)));
  const heat = dimension ? Array.from({ length: 11 }, (_, v) => rgb(scoreToColor(Math.max(1, v), dimension as ColorDimension))) : [];
  const plane = dimension && dimension !== 'rent' && dimension !== 'safety' ? grid.planes[dimension] : null;
  const districtValues = dimension === 'rent' || dimension === 'safety' ? districts.map((d) => d.ratings[dimension]) : null;
  for (const i of grid.cells) {
    const color = !pass[i] ? FILTERED_RGB : plane ? heat[plane[i]]
      : districtValues ? heat[districtValues[grid.planes.district[i] - 1]]
      : composite[Math.max(0, Math.min(100, Math.round(scores[i] * 10)))];
    const o = i * 4;
    target[o] = color[0]; target[o + 1] = color[1]; target[o + 2] = color[2];
    target[o + 3] = Math.round((pass[i] ? 0.3 + 0.55 * grid.planes.weight[i] / grid.header.scales.weight : 0.55) * 255);
  }
  return target;
}
