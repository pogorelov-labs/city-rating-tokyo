export interface StationRatings {
  food: number;
  nightlife: number;
  transport: number;
  rent: number;
  safety: number;
  green: number;
  gym_sports: number;
  vibe: number;
  crowd: number;
  daily_essentials: number; // Added in 10th-category sprint; default 5 until pipeline runs
}

export interface RentAvg {
  '1k_1ldk': number | null;
  '2ldk': number | null;
  source: string;
  updated: string;
}

export interface TransitMinutes {
  shibuya: number;
  shinjuku: number;
  tokyo: number;
  ikebukuro: number;
  shinagawa: number;
}

export interface StationDescription {
  atmosphere: string;
  landmarks: string;
  food: string;
  nightlife: string;
}

export type ConfidenceLevel = 'strong' | 'moderate' | 'estimate' | 'editorial';

export interface StationConfidence {
  food: ConfidenceLevel;
  nightlife: ConfidenceLevel;
  transport: ConfidenceLevel;
  rent: ConfidenceLevel;
  safety: ConfidenceLevel;
  green: ConfidenceLevel;
  gym_sports: ConfidenceLevel;
  vibe: ConfidenceLevel;
  crowd: ConfidenceLevel;
  daily_essentials?: ConfidenceLevel; // optional until pipeline regenerates all entries
}

export interface StationSources {
  food: string[];
  nightlife: string[];
  transport: string[];
  rent: string[];
  safety: string[];
  green: string[];
  gym_sports: string[];
  vibe: string[];
  crowd: string[];
  daily_essentials?: string[]; // optional until pipeline regenerates all entries
}

export type PlaceCategory = 'gym' | 'mall' | 'park' | 'landmark' | 'cafe' | 'restaurant' | 'bar';

export interface StationPlace {
  name: string;
  category: PlaceCategory;
  google_maps_url: string;
}

export type SeismicRiskTier = 'low' | 'moderate' | 'high' | 'very_high' | 'unknown';
export type ElevationTier = 'very_low' | 'low' | 'moderate' | 'elevated' | 'high' | 'mountain' | 'unknown';

export interface EnvironmentData {
  elevation_m?: number;
  elevation_tier?: ElevationTier;
  seismic_prob_i60?: number;
  seismic_prob_i55?: number;
  seismic_risk_tier?: SeismicRiskTier;
}

export interface Station {
  slug: string;
  name_en: string;
  name_jp: string;
  name_ru?: string;
  lat: number;
  lng: number;
  lines: string[];
  line_count: number;
  prefecture: string;
  ratings: StationRatings | null;
  rent_avg: RentAvg | null;
  transit_minutes: TransitMinutes | null;
  description?: StationDescription | null;
  confidence?: StationConfidence | null;
  sources?: StationSources | null;
  data_date?: string | null;
  environment?: EnvironmentData | null;
}

/** Lightweight station data for the homepage map & filter panel */
export interface MapStation {
  slug: string;
  name_en: string;
  name_jp: string;
  name_ru?: string;
  lat: number;
  lng: number;
  line_count: number;
  ratings: StationRatings | null;
  rent_1k: number | null;
  min_transit: number | null;
  elevation_m: number | null;
  seismic_risk_tier: SeismicRiskTier | null;
  // confidence is NOT included here on purpose: it was ~226 KB of the RSC
  // payload with 1493 stations and is only needed on the station detail page
  // (which uses the full Station type via getStation). If compare-panel
  // badges are needed again, lazy-load them from a separate data file.
}

export interface WeightConfig {
  food: number;
  nightlife: number;
  transport: number;
  rent: number;
  safety: number;
  green: number;
  gym_sports: number;
  vibe: number;
  crowd: number;
  daily_essentials: number;
}

export interface FilterState {
  minRent: number;
  maxRent: number;
  minCommute: number;
  maxCommute: number;
  categoryMins: Partial<Record<keyof StationRatings, number>>;
}

export const DEFAULT_FILTERS: FilterState = {
  minRent: 80000,
  maxRent: 300000,
  minCommute: 10,
  maxCommute: 60,
  categoryMins: {},
};

export const DEFAULT_WEIGHTS: WeightConfig = {
  food: 12,
  nightlife: 8,
  transport: 18,
  rent: 18,
  safety: 10,
  green: 8,
  gym_sports: 4,
  vibe: 4,
  crowd: 4,
  daily_essentials: 14,
};

export const RATING_LABELS: Record<keyof StationRatings, string> = {
  food: 'Food & Dining',
  nightlife: 'Nightlife',
  transport: 'Transport',
  rent: 'Affordability',
  safety: 'Safety',
  green: 'Parks & Green',
  gym_sports: 'Gym & Sports',
  vibe: 'Vibe & Atmosphere',
  crowd: 'Quietness',
  daily_essentials: 'Daily Essentials',
};

export const HUB_LABELS: Record<keyof TransitMinutes, string> = {
  shibuya: 'Shibuya',
  shinjuku: 'Shinjuku',
  tokyo: 'Tokyo',
  ikebukuro: 'Ikebukuro',
  shinagawa: 'Shinagawa',
};

export interface PresetProfile {
  id: string;
  label: string;
  icon: string;
  weights: WeightConfig;
  filters?: Partial<FilterState>;
}

export const PRESET_PROFILES: PresetProfile[] = [
  {
    id: 'young-pro',
    label: 'Young Pro',
    icon: '💼',
    weights: { food: 12, nightlife: 18, transport: 28, rent: 18, safety: 0, green: 0, gym_sports: 0, vibe: 12, crowd: 0, daily_essentials: 12 },
    filters: { maxRent: 150000, maxCommute: 30 },
  },
  {
    id: 'family',
    label: 'Family',
    icon: '👨‍👩‍👧',
    weights: { food: 0, nightlife: 0, transport: 12, rent: 8, safety: 25, green: 20, gym_sports: 0, vibe: 0, crowd: 15, daily_essentials: 20 },
    filters: { maxCommute: 40, categoryMins: { safety: 7 } },
  },
  {
    id: 'foodie-budget',
    label: 'Foodie Budget',
    icon: '🍜',
    weights: { food: 30, nightlife: 13, transport: 0, rent: 30, safety: 0, green: 0, gym_sports: 0, vibe: 13, crowd: 0, daily_essentials: 14 },
    filters: { maxRent: 120000 },
  },
  {
    id: 'digital-nomad',
    label: 'Digital Nomad',
    icon: '💻',
    weights: { food: 17, nightlife: 0, transport: 8, rent: 17, safety: 0, green: 0, gym_sports: 8, vibe: 22, crowd: 13, daily_essentials: 15 },
    filters: { maxRent: 130000 },
  },
];

export const SCATTER_AXIS_OPTIONS: { key: string; label: string }[] = [
  ...Object.entries(RATING_LABELS).map(([key, label]) => ({ key, label })),
  { key: 'rent_1k', label: 'Rent (1K-1LDK, yen)' },
  { key: 'min_transit', label: 'Min Transit (min)' },
];

export const RATING_TOOLTIPS: Record<keyof StationRatings, string> = {
  food: 'Variety and quality of restaurants, cafes, street food, and specialty dining within 10-15 min walk',
  nightlife: 'Bars, izakaya, clubs, live music venues, and late-night entertainment options',
  transport: 'Number of train lines, frequency, connections to major hubs, and overall commute convenience',
  rent: 'Affordability based on actual rent data (1K-1LDK). 10 = cheapest (~\u00a570k/mo), 1 = most expensive (~\u00a5300k+)',
  safety: 'Overall neighborhood safety: crime rates, street lighting, family-friendliness, late-night comfort',
  green: 'Parks, gardens, riverside walks, green spaces, and nature within 15 min walk',
  gym_sports: 'Fitness centers, gyms, sports facilities, running paths, and athletic amenities nearby',
  vibe: 'Overall character and charm: cultural identity, street life, local community, architectural interest',
  crowd: 'Quietness level (inverted: 10 = very peaceful and uncrowded, 1 = extremely busy and packed)',
  daily_essentials: 'Supermarkets, pharmacies, clinics, banks, laundry, dentists, and other daily necessities within walking distance',
};

export const PLACE_CATEGORY_LABELS: Record<PlaceCategory, string> = {
  gym: 'Gyms & Fitness',
  mall: 'Shopping Malls',
  park: 'Parks & Gardens',
  landmark: 'Landmarks',
  cafe: 'Cafes',
  restaurant: 'Restaurants',
  bar: 'Bars & Izakaya',
};

export const PLACE_CATEGORY_SEARCH_TERMS: Record<PlaceCategory, string> = {
  gym: 'gym fitness',
  mall: 'shopping mall',
  park: 'park garden',
  landmark: 'tourist attraction landmark',
  cafe: 'cafe coffee',
  restaurant: 'restaurant',
  bar: 'bar izakaya',
};

export function getGoogleMapsUrl(lat: number, lng: number, name: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}&query_place_id=${encodeURIComponent(name + ' Station')}`;
}

export function getGoogleMapsAreaUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/@${lat},${lng},16z`;
}

export function getGoogleMapsSearchUrl(lat: number, lng: number, category: PlaceCategory): string {
  const term = PLACE_CATEGORY_SEARCH_TERMS[category];
  return `https://www.google.com/maps/search/${encodeURIComponent(term)}/@${lat},${lng},15z`;
}
