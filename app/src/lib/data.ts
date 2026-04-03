import rawStations from '@/data/stations.json';
import { DEMO_RATINGS } from '@/data/demo-ratings';
import rentData from '@/data/rent-averages.json';
import stationImagesData from '@/data/station-images.json';
import { Station, MapStation, RentAvg } from './types';

const suumoRent = rentData as Record<string, { '1k_1ldk': number | null; '2ldk': number | null; source: string; updated: string }>;
const imageData = stationImagesData as Record<string, { url: string; alt: string }[]>;

export function getStations(): Station[] {
  return (rawStations as Station[]).map((s) => {
    const demo = DEMO_RATINGS[s.slug];
    const rent = suumoRent[s.slug];

    // Suumo real data takes priority over AI estimates
    const rentAvg: RentAvg | null = rent
      ? { '1k_1ldk': rent['1k_1ldk'], '2ldk': rent['2ldk'], source: 'suumo', updated: rent.updated }
      : demo?.rent_avg || null;

    if (demo) {
      return {
        ...s,
        ratings: demo.ratings,
        transit_minutes: demo.transit_minutes,
        rent_avg: rentAvg,
        description: demo.description || null,
      };
    }
    return { ...s, rent_avg: rentAvg };
  });
}

/** Lightweight station list for homepage — drops description, transit, lines, prefecture */
export function getMapStations(): MapStation[] {
  return getStations().map((s) => ({
    slug: s.slug,
    name_en: s.name_en,
    name_jp: s.name_jp,
    lat: s.lat,
    lng: s.lng,
    line_count: s.line_count,
    ratings: s.ratings,
    rent_1k: s.rent_avg?.['1k_1ldk'] ?? null,
  }));
}

/** Pre-computed thumbnail URL per station (first wikimedia image) */
export function getThumbnails(): Record<string, string> {
  const thumbnails: Record<string, string> = {};
  for (const [slug, imgs] of Object.entries(imageData)) {
    if (imgs?.[0]) thumbnails[slug] = imgs[0].url;
  }
  return thumbnails;
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
