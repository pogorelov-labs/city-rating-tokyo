import type { ConfidenceLevel, StationRatings, WeightConfig } from '@/lib/types';

export type RatingKey = keyof StationRatings;
export type Point = [number, number];
export type AreaGroup = 'tokyo-station' | 'bangkok-station' | 'bangkok-district';

export interface CardArea {
  id: string;
  slug: string;
  group: AreaGroup;
  city: 'tokyo' | 'bangkok';
  kind: 'station' | 'district';
  name: string;
  localName: string;
  location: string;
  summary: string;
  strengths: string[];
  tradeoffs: string[];
  ratings: StationRatings;
  medians: StationRatings;
  confidence: Partial<Record<RatingKey, ConfidenceLevel>>;
  sources: Partial<Record<RatingKey, string[]>>;
  peerCount: number;
  dataDate: string | null;
  photo: { url: string; alt: string; credit: string; license: string; href: string } | null;
  rent: {
    values: { label: string; value: number | null }[];
    label: string;
    date: string | null;
    detail: string;
    limitations: string[];
    samples: string | null;
    skewed: boolean;
    sources: { label: string; href: string }[];
  };
  commute: Record<string, number>;
  commuteNote: string;
  lastTrain: string | null;
  lines: { name: string; color?: string }[];
  stationCount: number;
  facts: { label: string; value: number; unit?: string }[];
  factsNote: string;
  map: {
    center: Point;
    bbox: [Point, Point];
    polygons: Point[][][] | null;
    scope: string;
    stationIds: string[];
    stations: { id: string; name: string; lat: number; lng: number }[];
    lineIds: string[];
  };
  noise: { day: number; night: number; date: string; transferred: boolean } | null;
  context: { title: string; text: string; href?: string }[];
  detailHref: string;
  mapHref: string;
  methodologyHref: string;
}

export const CATEGORIES: { key: RatingKey; label: string; explanation: string }[] = [
  { key: 'transport', label: 'Transport', explanation: 'Rail access and the city’s existing connectivity model.' },
  { key: 'rent', label: 'Affordability', explanation: 'Higher means a lower reference rent. Read the apartment type and source beside the rent figures.' },
  { key: 'daily_essentials', label: 'Daily essentials', explanation: 'Access to everyday shops and services. Mapped coverage varies.' },
  { key: 'safety', label: 'Safety', explanation: 'A relative category score, not a probability of crime. Tokyo uses police-data inputs; Bangkok uses editorial district assessments.' },
  { key: 'food', label: 'Food & dining', explanation: 'The availability of places to eat, based on the city’s mapped-place and dining sources.' },
  { key: 'green', label: 'Parks & greenery', explanation: 'Mapped green-space signals; this does not measure the quality of every park or the walk from a home.' },
  { key: 'gym_sports', label: 'Fitness', explanation: 'Mapped gyms and sports facilities.' },
  { key: 'vibe', label: 'Local character', explanation: 'Cultural and pedestrian signals, with editorial assessments where recorded.' },
  { key: 'nightlife', label: 'Nightlife', explanation: 'More evening options produce a higher score. Whether that suits you depends on your priorities.' },
  { key: 'crowd', label: 'Less crowding', explanation: 'The existing Quietness ranking uses crowd or place-density proxies. It is separate from the outdoor-noise estimates below.' },
];

export const HUB_NAMES: Record<string, string> = {
  shibuya: 'Shibuya', shinjuku: 'Shinjuku', tokyo: 'Tokyo', ikebukuro: 'Ikebukuro', shinagawa: 'Shinagawa',
  siam: 'Siam', asok: 'Asok', silom: 'Silom', rama9: 'Rama 9', mochit: 'Mo Chit',
};

export const GROUP_NAMES: Record<AreaGroup, string> = {
  'tokyo-station': 'Tokyo · stations',
  'bangkok-station': 'Bangkok · station areas',
  'bangkok-district': 'Bangkok · districts',
};

export function peerLabel(area: CardArea): string {
  return `${area.city === 'tokyo' ? 'Tokyo' : 'Bangkok'} ${area.kind === 'district' ? 'districts' : 'station areas'}`;
}

export function money(area: CardArea, value: number | null): string {
  return value == null ? 'Unavailable' : `${area.city === 'tokyo' ? '¥' : '฿'}${value.toLocaleString('en-US')}`;
}

export function evidenceLabel(level?: ConfidenceLevel): string {
  if (!level) return 'Source detail unavailable';
  return ({ strong: 'Data-backed', moderate: 'Partial data', estimate: 'Model / proxy', editorial: 'Editorial' } as const)[level];
}

export function sourceLabel(source: string): string {
  const names: Record<string, string> = {
    osm: 'OpenStreetMap', overture: 'Overture Maps', hotpepper: 'Hot Pepper', suumo: 'SUUMO', estat: 'e-Stat',
    ai_research: 'Editorial research', listing_research: 'Editorial rent research', dooasset: 'DooAsset',
    worldpop_2020: 'WorldPop 2020', transit_model: 'Commute model', osm_rail: 'OpenStreetMap rail',
    mlit: 'MLIT', mlit_s12: 'MLIT passenger data', police: 'Police open data',
  };
  return names[source] ?? source.replaceAll('_', ' ');
}

export interface PriorityProfile { id: string; name: string; weights: WeightConfig }
