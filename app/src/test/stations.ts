import type { MapStation } from '@/lib/types';

export function station(slug: string, overrides: Partial<MapStation> = {}): MapStation {
  return {
    slug, name_en: slug, name_jp: `駅 ${slug}`, lat: 35.7, lng: 139.7,
    line_count: 2, rent_1k: 100000, min_transit: 20, elevation_m: 10,
    seismic_risk_tier: 'low',
    ratings: { transport: 7, rent: 7, daily_essentials: 7, safety: 7, food: 7,
      green: 7, gym_sports: 7, vibe: 7, nightlife: 7, crowd: 7 },
    ...overrides,
  };
}
