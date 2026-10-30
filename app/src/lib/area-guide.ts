import type { Locale } from '@/i18n/routing';
import { areaPath, type CityId } from './cities';
import { DEFAULT_WEIGHTS, type ConfidenceLevel, type StationRatings, type WeightConfig } from './types';

export type RatingKey = keyof StationRatings;
export type GuideTraitKey = Exclude<RatingKey, 'safety'>;
export type GuideKind = 'station' | 'district';
export type MapPoint = [number, number];
export const GUIDE_CATEGORIES = Object.keys(DEFAULT_WEIGHTS) as RatingKey[];

export interface GuidePeer {
  key: string;
  name: string;
  href: string;
  ratings: StationRatings;
}

export interface AreaGuideData {
  city: CityId;
  kind: GuideKind;
  key: string;
  slug: string;
  locale: Locale;
  name: string;
  localName: string;
  summary: string;
  ratings: StationRatings | null;
  medians: StationRatings;
  confidence: Partial<Record<RatingKey, ConfidenceLevel>>;
  sources: Partial<Record<RatingKey, string[]>>;
  peerCount: number;
  peers: GuidePeer[];
  date: string | null;
  photo: { url: string; alt: string; credit: string; license: string; href: string } | null;
  rent: {
    values: { layout: 'smallTokyo' | 'largeTokyo' | 'oneBedroom' | 'twoBedroom'; value: number | null }[];
    provenance: 'stationAverage' | 'municipalAverage' | 'estimate' | 'districtBlend' | 'bedroomMedian' | 'unavailable';
    date: string | null;
    samples: { one: number; two: number } | null;
    skewed: boolean;
    sources: { label: string; href: string }[];
  };
  commute: Record<string, number>;
  lastTrain: string | null;
  lines: { name: string; color: string }[];
  stationCount: number;
  facts: { key: 'food' | 'essentials' | 'sports' | 'green' | 'services' | 'elevation' | 'cafes' | 'markets' | 'culture' | 'temples' | 'piers' | 'nightlife' | 'area' | 'population' | 'hotels' | 'attractions'; value: number; unit?: 'ha' | 'm' | 'km2' }[];
  areaKm2: number | null;
  map: {
    center: MapPoint;
    bbox: [MapPoint, MapPoint];
    polygons: MapPoint[][][] | null;
    stations: { id: string; name: string; lat: number; lng: number; selected: boolean }[];
    lineIds: string[];
  };
  noise: { day: number; night: number; date: string; transferred: boolean } | null;
  mapHref: string;
  mapsHref: string;
  methodologyHref: string;
}

/** The generic estimate definition describes Bangkok's units, not Tokyo's. */
export function rentDefinitionKey(city: CityId, provenance: AreaGuideData['rent']['provenance']): `rent.definition.${AreaGuideData['rent']['provenance'] | 'tokyoEstimate'}` {
  return `rent.definition.${city === 'tokyo' && provenance === 'estimate' ? 'tokyoEstimate' : provenance}`;
}

/** Include non-default preferences in ordinary, reloadable detail/map links. */
export function withGuideWeights(href: string, weights: WeightConfig): string {
  const url = new URL(href, 'https://city-rating.invalid');
  const values = GUIDE_CATEGORIES.map(key => weights[key]);
  if (GUIDE_CATEGORIES.every(key => weights[key] === DEFAULT_WEIGHTS[key])) url.searchParams.delete('w');
  else url.searchParams.set('w', values.join(','));
  return url.pathname + url.search + url.hash;
}

export function guideDetailHref(city: CityId, key: string, weights: WeightConfig): string {
  return withGuideWeights(areaPath(city, key), weights);
}

export function guideMoney(city: CityId, value: number | null, locale: Locale): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return `${city === 'tokyo' ? '¥' : '฿'}${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}`;
}

/** Describe differences in the ranking without treating safety as a street-level claim. */
export function guideTraits(ratings: StationRatings | null, medians: StationRatings) {
  if (!ratings) return { strengths: [] as GuideTraitKey[], tradeoffs: [] as GuideTraitKey[] };
  const candidates = GUIDE_CATEGORIES.filter((key): key is GuideTraitKey => key !== 'safety');
  const ordered = candidates.map(key => ({ key, difference: ratings[key] - medians[key] }));
  return {
    strengths: ordered.filter(row => row.difference > 0).sort((a, b) => b.difference - a.difference).slice(0, 2).map(row => row.key),
    tradeoffs: ordered.filter(row => row.difference < 0).sort((a, b) => a.difference - b.difference).slice(0, 2).map(row => row.key),
  };
}
