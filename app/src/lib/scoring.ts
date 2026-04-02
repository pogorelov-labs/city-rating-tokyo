import { Station, StationRatings, WeightConfig } from './types';

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

export function scoreToColor(score: number): string {
  // 1-10 scale: red -> yellow -> green
  const t = Math.max(0, Math.min(1, (score - 1) / 9));
  if (t < 0.5) {
    // red to yellow
    const r = 220;
    const g = Math.round(60 + t * 2 * 180);
    return `rgb(${r}, ${g}, 50)`;
  }
  // yellow to green
  const r = Math.round(220 - (t - 0.5) * 2 * 170);
  const g = Math.round(200 + (t - 0.5) * 2 * 40);
  return `rgb(${r}, ${g}, 50)`;
}

export function getAxisValue(station: Station, axis: string): number | null {
  if (axis === 'rent_1k') return station.rent_avg?.['1k_1ldk'] ?? null;
  if (axis === 'min_transit') {
    if (!station.transit_minutes) return null;
    const vals = Object.values(station.transit_minutes).filter((v) => v > 0);
    return vals.length > 0 ? Math.min(...vals) : null;
  }
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
