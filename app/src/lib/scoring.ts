import { Station, MapStation, StationRatings, WeightConfig, RentAvg } from './types';

const RENT_FLOOR = 70_000;
const RENT_CEILING = 300_000;

/**
 * Color dimension for scoreToColor().
 * `'composite'` (or undefined) = weighted overall score → magma scale.
 * Any rating key (e.g. `'food'`, `'nightlife'`) = category-specific hue.
 */
export type ColorDimension = 'composite' | keyof StationRatings;

type RGB = readonly [number, number, number];

/**
 * Magma-inspired scale for the default composite score.
 * Perceptually uniform, colorblind-safe, reads well on the Carto light
 * basemap. Goes deep indigo → violet → magenta → coral → warm gold.
 * Tuned so the high end stays visible (doesn't fade to pale yellow).
 */
const MAGMA_STOPS: readonly RGB[] = [
  [44, 17, 95],    // #2c115f deep indigo  (score 1)
  [114, 31, 129],  // #721f81 violet
  [183, 55, 121],  // #b73779 magenta
  [229, 89, 100],  // #e55964 coral
  [240, 125, 64],  // #f07d40 burnt orange
  [242, 165, 38],  // #f2a526 warm gold    (score 10)
];

/**
 * Category-specific 2-stop palettes for heatmap dimensions and per-category
 * UI accents. Each goes low-saturation → high-saturation so 1 → 10 moves
 * from washed-out to vivid in the dimension's signature hue.
 */
const CATEGORY_PALETTES: Record<keyof StationRatings, readonly [RGB, RGB]> = {
  food:       [[254, 243, 199], [234, 88, 12]],    // amber → orange
  nightlife:  [[233, 213, 255], [126, 34, 206]],   // lavender → deep purple
  transport:  [[219, 234, 254], [29, 78, 216]],    // light blue → royal blue
  rent:       [[254, 249, 195], [202, 138, 4]],    // pale yellow → darker amber
  safety:     [[204, 251, 241], [15, 118, 110]],   // light teal → deep teal
  green:      [[220, 252, 231], [21, 128, 61]],    // light green → forest
  gym_sports: [[254, 205, 211], [190, 18, 60]],    // rose → crimson
  vibe:       [[252, 231, 243], [190, 24, 93]],    // pink → magenta
  crowd:      [[226, 232, 240], [30, 41, 59]],     // slate → dark slate
};

function lerpColor(a: RGB, b: RGB, t: number): string {
  const r = Math.round(a[0] + (b[0] - a[0]) * t);
  const g = Math.round(a[1] + (b[1] - a[1]) * t);
  const bl = Math.round(a[2] + (b[2] - a[2]) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}

function samplePalette(t: number, stops: readonly RGB[]): string {
  const clamped = Math.max(0, Math.min(1, t));
  const n = stops.length - 1;
  const seg = clamped * n;
  const i = Math.min(Math.floor(seg), n - 1);
  return lerpColor(stops[i], stops[i + 1], seg - i);
}

/**
 * Derive Affordability score (1-10) from actual rent data.
 * Inverted scale: cheapest → 10, most expensive → 1.
 * Uses 1K-1LDK as primary, falls back to 2LDK.
 */
export function rentToAffordability(rentAvg: RentAvg): number | null {
  const rent = rentAvg['1k_1ldk'] ?? rentAvg['2ldk'];
  if (rent == null) return null;
  const t = Math.max(0, Math.min(1, (rent - RENT_FLOOR) / (RENT_CEILING - RENT_FLOOR)));
  return Math.round(10 - 9 * t);
}

export function calculateWeightedScore(
  ratings: StationRatings,
  weights: WeightConfig
): number {
  const keys = Object.keys(weights) as (keyof WeightConfig)[];
  let totalWeight = 0;
  let weightedSum = 0;

  for (const key of keys) {
    const weight = weights[key];
    if (weight <= 0) continue;
    totalWeight += weight;
    weightedSum += ratings[key] * weight;
  }

  if (totalWeight === 0) return 0;
  return Math.round((weightedSum / totalWeight) * 10) / 10;
}

/**
 * Map a 1–10 rating to an RGB color string.
 *
 * @param score      The value, typically 1–10 (clamped internally).
 * @param dimension  Optional category key. If `'composite'` or omitted,
 *                   uses the magma scale. Otherwise uses the
 *                   category-specific 2-stop hue palette.
 *
 * Use cases:
 * - Composite map markers, ranked list, scatter, compare score row: no arg
 * - Heatmap mode with a specific dimension: pass `heatmapDimension`
 * - Per-category bars on the station detail page: pass the rating key
 */
export function scoreToColor(score: number, dimension?: ColorDimension): string {
  const t = Math.max(0, Math.min(1, (score - 1) / 9));
  if (!dimension || dimension === 'composite') {
    return samplePalette(t, MAGMA_STOPS);
  }
  const pal = CATEGORY_PALETTES[dimension];
  if (!pal) return samplePalette(t, MAGMA_STOPS);
  return lerpColor(pal[0], pal[1], t);
}

export function getAxisValue(station: MapStation, axis: string): number | null {
  if (axis === 'rent_1k') return station.rent_1k;
  if (axis === 'min_transit') return station.min_transit;
  return (station.ratings as Record<string, number> | null)?.[axis] ?? null;
}

export function filterStations(
  stations: Station[],
  weights: WeightConfig,
  filters: {
    maxRent?: number;
    maxCommute?: number;
    minScore?: number;
  }
): (Station & { score: number })[] {
  return stations
    .filter((s) => s.ratings !== null)
    .map((s) => ({
      ...s,
      score: calculateWeightedScore(s.ratings!, weights),
    }))
    .filter((s) => {
      if (filters.minScore && s.score < filters.minScore) return false;
      if (filters.maxRent && s.rent_avg) {
        const rent = s.rent_avg['1k_1ldk'] ?? s.rent_avg['2ldk'];
        if (rent && rent > filters.maxRent) return false;
      }
      if (filters.maxCommute && s.transit_minutes) {
        const minTransit = Math.min(
          ...Object.values(s.transit_minutes).filter((v) => v > 0)
        );
        if (minTransit > filters.maxCommute) return false;
      }
      return true;
    })
    .sort((a, b) => b.score - a.score);
}
