import rawStations from '@/data/stations.json';
import { DEMO_RATINGS } from '@/data/demo-ratings';
import rentData from '@/data/rent-averages.json';
import stationThumbData from '@/data/station-thumbnails.json';
import environmentData from '@/data/environment-data.json';
import lineNamesData from '@/data/line-names.json';
import wardData from '@/data/ward-data.json';
import lastTrainsData from '@/data/last-trains.json';
import { Station, MapStation, RentAvg, EnvironmentData, LineInfo, WardInfo, LastTrainInfo } from './types';
import { rentToAffordability } from './scoring';

const suumoRent = rentData as Record<string, { '1k_1ldk': number | null; '2ldk': number | null; source: string; updated: string }>;
const thumbData = stationThumbData as Record<string, { thumb: string; lqip: string }>;
const envData = environmentData as Record<string, EnvironmentData>;
const lineNames = lineNamesData as Record<string, Omit<LineInfo, 'id'>>;
const wards = wardData as Record<string, WardInfo>;
const lastTrains = lastTrainsData as Record<string, LastTrainInfo>;

export function getStations(): Station[] {
  return (rawStations as unknown as Array<Omit<Station, 'lines' | 'ward'> & { lines: string[] }>).map((s) => {
    const demo = DEMO_RATINGS[s.slug];
    const rent = suumoRent[s.slug];

    // Resolve line IDs to LineInfo objects
    const resolvedLines: LineInfo[] = s.lines
      .map((id) => {
        const info = lineNames[id];
        return info ? { id, ...info } : null;
      })
      .filter((l): l is LineInfo => l !== null);

    const ward = wards[s.slug] || null;
    const last_train = lastTrains[s.slug] || null;

    // Suumo real data takes priority over AI estimates
    const rentAvg: RentAvg | null = rent
      ? { '1k_1ldk': rent['1k_1ldk'], '2ldk': rent['2ldk'], source: 'suumo', updated: rent.updated }
      : demo?.rent_avg || null;

    // Derive affordability score from real rent data when available
    const computedRent = rentAvg ? rentToAffordability(rentAvg) : null;

    const env = envData[s.slug] || null;

    if (demo) {
      const baseRatings = { ...demo.ratings, daily_essentials: demo.ratings.daily_essentials ?? 5 };
      const ratings = computedRent != null
        ? { ...baseRatings, rent: computedRent }
        : baseRatings;
      return {
        ...s,
        lines: resolvedLines,
        ward,
        last_train,
        ratings,
        transit_minutes: demo.transit_minutes,
        rent_avg: rentAvg,
        description: demo.description || null,
        confidence: demo.confidence
          ? { ...demo.confidence, daily_essentials: demo.confidence.daily_essentials ?? 'estimate' as const }
          : null,
        sources: demo.sources
          ? { ...demo.sources, daily_essentials: demo.sources.daily_essentials ?? [] }
          : null,
        data_date: demo.data_date || null,
        environment: env,
      };
    }
    return { ...s, lines: resolvedLines, ward, last_train, rent_avg: rentAvg, environment: env };
  });
}

/** Lightweight station list for homepage — drops description, transit, lines, prefecture, confidence */
export function getMapStations(): MapStation[] {
  return getStations().map((s) => {
    let minTransit: number | null = null;
    if (s.transit_minutes) {
      const vals = Object.values(s.transit_minutes).filter((v) => v > 0);
      if (vals.length > 0) minTransit = Math.min(...vals);
    }
    return {
      slug: s.slug,
      name_en: s.name_en,
      name_jp: s.name_jp,
      ...(s.name_ru && { name_ru: s.name_ru }),
      lat: s.lat,
      lng: s.lng,
      line_count: s.line_count,
      ratings: s.ratings,
      rent_1k: s.rent_avg?.['1k_1ldk'] ?? null,
      min_transit: minTransit,
      elevation_m: s.environment?.elevation_m ?? null,
      seismic_risk_tier: s.environment?.seismic_risk_tier ?? null,
    };
  });
}

/** Pre-computed thumbnail URL + LQIP base64 per station */
export function getThumbnails(): Record<string, { thumb: string; lqip: string }> {
  return thumbData;
}

/** Pre-computed short atmosphere snippets */
export function getSnippets(): Record<string, string> {
  const snippets: Record<string, string> = {};
  for (const [slug, demo] of Object.entries(DEMO_RATINGS)) {
    const atmo = demo.description?.atmosphere;
    if (atmo) {
      snippets[slug] = atmo.length > 120 ? atmo.slice(0, 120) + '...' : atmo;
    }
  }
  return snippets;
}

export function getStation(slug: string): Station | undefined {
  return getStations().find((s) => s.slug === slug);
}

export function getAllSlugs(): string[] {
  return getStations().map((s) => s.slug);
}
