import rawStations from '@/data/stations.json';
import { DEMO_RATINGS } from '@/data/demo-ratings';
import rentData from '@/data/rent-averages.json';
import { Station, RentAvg } from './types';

const suumoRent = rentData as Record<string, { '1k_1ldk': number | null; '2ldk': number | null; source: string; updated: string }>;

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

export function getStation(slug: string): Station | undefined {
  return getStations().find((s) => s.slug === slug);
}

export function getAllSlugs(): string[] {
  return getStations().map((s) => s.slug);
}
