import { Station, MapStation, StationRatings, WeightConfig, RentAvg } from './types';

// Raised from ¥70k → ¥80k in formula v3. The old ¥70k floor was only reachable
// via the broken distance_estimate fallback which no longer exists. The cheapest
// real Suumo rent in Greater Tokyo is ¥83,500 (Kawagoe). MUST match
// scripts/compute-ratings.py RENT_FLOOR.
const RENT_FLOOR = 80_000;
const RENT_CEILING = 300_000;

/**
 * Color dimension for scoreToColor().
 * `'composite'` (or undefined) → diverging composite palette (via
 * `compositeToColor`, which needs percentile anchors).
 * Any rating key → per-dimension category hue palette, unchanged from
 * CRTKY-58 Phase 2 and still used for the heatmap per-dimension layer.
 */
export type ColorDimension = 'composite' | keyof StationRatings;

type RGB = readonly [number, number, number];

/**
 * Diverging palette for the composite score.
 *
 * Traditional Japanese pigments chosen for a shibui, premium feel that
 * reads well on the Carto light basemap AND carries insight: the two
 * tails are warm vs cool, so users immediately see "below median" vs
 * "above median" without needing a legend.
 *
 * Pairs with `compositeToColor(score, anchors)` which percentile-stretches
 * the score so the 5 stops always map to the actual observed distribution
 * (p5 → p50 → p95) rather than a fixed 1-10 range. This matters because
 * real composite scores in Greater Tokyo cluster tightly in p5=3.60,
 * p50=6.00, p95=7.15 — magma applied to that range collapsed into a
 * coral/red blob (CRTKY-58 prod regression, caught in CRTKY-66).
 */
const DIVERGING_STOPS: readonly RGB[] = [
  [140, 41, 38],   // #8C2926  茜 akane deep     (≤ p5, strongly below)
  [179, 87, 78],   // #B3574E  珊瑚 sango-beta  (p5..p50)
  [217, 201, 168], // #D9C9A8  生成り kinari     (p50, warm neutral pivot)
  [106, 137, 153], // #6A8999  浅葱 asagi        (p50..p95)
  [44, 74, 95],    // #2C4A5F  紺 kon            (≥ p95, strongly above)
];

/**
 * City-wide median for each rating dimension, computed from the current
 * `demo-ratings.ts` (formula v3) data. Used by `categoryDeviationColor`
 * on the station detail page's rating bars so each bar paints in the
 * diverging palette according to (value − city median).
 *
 * These are rounded integers because ratings themselves are integers 1-10.
 * Recompute when the rating dataset changes by running compute/export and
 * rereading percentiles; see scripts/compute-ratings.py.
 */
export const CITY_MEDIANS: Record<keyof StationRatings, number> = {
  food: 5,
  nightlife: 5,
  transport: 6,
  rent: 8,
  safety: 6,
  green: 5,
  gym_sports: 5,
  vibe: 5,
  crowd: 7,
};

/**
 * Category-specific 2-stop palettes for the heatmap per-dimension layer.
 * Kept intentionally from CRTKY-58 Phase 2 because that layer's job is
 * "which dimension am I viewing right now" — orientation, not insight.
 * Unchanged in CRTKY-66 per the design review.
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
 * Percentile anchors for the diverging composite palette. Computed from
 * the currently-filtered station set and weights, so as the user tweaks
 * weights, the palette always uses its full range across the actual data.
 */
export interface PercentileAnchors {
  p5: number;
  p50: number;
  p95: number;
}

/**
 * Color for a composite (weighted) score using the diverging Japanese
 * palette. The score is piecewise-linearly mapped onto the palette via the
 * percentile anchors: p5 → stop 0 (akane), p50 → middle stop (kinari),
 * p95 → last stop (kon). Scores outside [p5, p95] clamp to the tails.
 *
 * This replaces the old magma path in `scoreToColor('composite')` because
 * on real Greater Tokyo data (p5=3.6, p50=6.0, p95=7.1) magma collapsed
 * into a single coral wash — the whole indigo low-end and warm-gold
 * high-end were wasted. CRTKY-66.
 */
export function compositeToColor(
  score: number,
  anchors: PercentileAnchors,
): string {
  const { p5, p50, p95 } = anchors;
  let t: number;
  if (p5 >= p95) {
    t = 0.5;
  } else if (score <= p5) {
    t = 0;
  } else if (score >= p95) {
    t = 1;
  } else if (score <= p50) {
    t = 0.5 * ((score - p5) / (p50 - p5));
  } else {
    t = 0.5 + 0.5 * ((score - p50) / (p95 - p50));
  }
  return samplePalette(t, DIVERGING_STOPS);
}

/**
 * Color a single per-category rating bar on the station detail page
 * according to its deviation from the city median for THAT category.
 * Maps (value − median) ∈ [−5, +5] onto the diverging palette.
 *
 * This replaces the CRTKY-58 "9 hues per card" rainbow approach. The new
 * reading is instant: akane-red rows = weak for this station, kon-navy
 * rows = strong for this station, kinari cream = at city average.
 */
export function categoryDeviationColor(value: number, median: number): string {
  const dev = value - median;
  const t = Math.max(0, Math.min(1, (dev + 5) / 10));
  return samplePalette(t, DIVERGING_STOPS);
}

/**
 * Compute p5/p50/p95 composite-score anchors from a station set and
 * a weight configuration. O(n log n) sort; cheap on 1500 stations.
 *
 * Stations without ratings are skipped. Falls back to a reasonable default
 * if the set is empty.
 */
export function computeCompositeAnchors<
  T extends { ratings: StationRatings | null },
>(stations: readonly T[], weights: WeightConfig): PercentileAnchors {
  const scores: number[] = [];
  for (const s of stations) {
    if (s.ratings) scores.push(calculateWeightedScore(s.ratings, weights));
  }
  if (scores.length === 0) return { p5: 1, p50: 5.5, p95: 10 };
  scores.sort((a, b) => a - b);
  const n = scores.length;
  const pick = (pct: number) =>
    scores[Math.min(n - 1, Math.max(0, Math.floor(n * pct)))];
  return { p5: pick(0.05), p50: pick(0.5), p95: pick(0.95) };
}

/**
 * Static anchors used by pre-rendered (SSG) station detail pages where
 * weights are always the defaults at build time. Matches the
 * post-formula-v3 distribution: p5=3.60, p50=6.00, p95=7.15 across 1493
 * stations. Update this constant only if the default weights or the
 * rating dataset materially change.
 */
export const DEFAULT_COMPOSITE_ANCHORS: PercentileAnchors = {
  p5: 3.6,
  p50: 6.0,
  p95: 7.15,
};

/**
 * Thin compatibility shim: the old two-arg `scoreToColor(score, dimension)`
 * still exists for the heatmap per-dimension layer, which paints in
 * category-specific hues regardless of the dataset's distribution.
 *
 * For the composite case, callers MUST use `compositeToColor(score, anchors)`
 * with percentile anchors. The pre-CRTKY-66 behavior of scoreToColor(score)
 * falling back to magma across a 1-10 range is gone; callers passing only a
 * score here get the composite palette at t=0.5 (neutral) which is an
 * obvious visual cue to migrate.
 */
export function scoreToColor(score: number, dimension?: ColorDimension): string {
  if (dimension && dimension !== 'composite') {
    const pal = CATEGORY_PALETTES[dimension];
    if (pal) {
      const t = Math.max(0, Math.min(1, (score - 1) / 9));
      return lerpColor(pal[0], pal[1], t);
    }
  }
  return samplePalette(0.5, DIVERGING_STOPS);
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
