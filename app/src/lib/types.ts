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

export type ConfidenceLevel = 'strong' | 'moderate' | 'estimate';

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
}

export type PlaceCategory = 'gym' | 'mall' | 'park' | 'landmark' | 'cafe' | 'restaurant' | 'bar';

export interface StationPlace {
  name: string;
  category: PlaceCategory;
  google_maps_url: string;
}

export interface Station {
  slug: string;
  name_en: string;
  name_jp: string;
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
}

/** Lightweight station data for the homepage map & filter panel */
export interface MapStation {
  slug: string;
  name_en: string;
  name_jp: string;
  lat: number;
  lng: number;
  line_count: number;
  ratings: StationRatings | null;
  rent_1k: number | null;
  min_transit: number | null;
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
}

export const DEFAULT_WEIGHTS: WeightConfig = {
  food: 15,
  nightlife: 10,
  transport: 20,
  rent: 20,
  safety: 10,
  green: 10,
  gym_sports: 5,
  vibe: 5,
  crowd: 5,
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
  crowd: 'Low Crowds',
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
}

export const PRESET_PROFILES: PresetProfile[] = [
  {
    id: 'young-pro',
    label: 'Young Pro',
    icon: '💼',
    weights: { food: 15, nightlife: 20, transport: 30, rent: 20, safety: 0, green: 0, gym_sports: 0, vibe: 15, crowd: 0 },
  },
  {
    id: 'family',
    label: 'Family',
    icon: '👨‍👩‍👧',
    weights: { food: 0, nightlife: 0, transport: 15, rent: 10, safety: 30, green: 25, gym_sports: 0, vibe: 0, crowd: 20 },
  },
  {
    id: 'foodie-budget',
    label: 'Foodie Budget',
    icon: '🍜',
    weights: { food: 35, nightlife: 15, transport: 0, rent: 35, safety: 0, green: 0, gym_sports: 0, vibe: 15, crowd: 0 },
  },
  {
    id: 'digital-nomad',
    label: 'Digital Nomad',
    icon: '💻',
    weights: { food: 20, nightlife: 0, transport: 10, rent: 20, safety: 0, green: 0, gym_sports: 10, vibe: 25, crowd: 15 },
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
