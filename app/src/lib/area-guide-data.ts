// Server-side adapter. Full data and geometry never enter homepage card payloads.
import { getTranslations } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import { getStation, getStations } from './data';
import { getBangkokDistrict, getBangkokDistricts, getBangkokStationArea, getBangkokStationAreas, getRailLine, getRailStation } from './bangkok-data';
import { areaPath, type CityId } from './cities';
import { stationDisplayName } from './station-name';
import { stationAreaKey } from './area-key';
import { getQuietness } from './quietness';
import { isStationLevelRent } from './scoring';
import { getGoogleMapsAreaUrl } from './types';
import { GUIDE_CATEGORIES, type AreaGuideData, type GuideKind, type GuidePeer, type MapPoint } from './area-guide';
import type { StationRatings } from './types';
import imageData from '@/data/station-images-all.json';
import districtGeometry from '@/data/bangkok/geometry.json';
import stationGeometry from '@/data/bangkok/station-geometry.json';
import presentationCopy from '@/data/area-guide-copy.json';

interface Shape { polygons: MapPoint[][][]; bbox: [MapPoint, MapPoint] }
interface Photo { url: string; alt: string; photographer?: string; attribution?: string; license?: string; flickr_url?: string; photographer_url?: string }
const photos = imageData as Record<string, Photo[]>;
const copy = presentationCopy as Record<string, Record<Locale, string>>;
const nearbyCache = new Map<string, string[]>();
const medianCache = new Map<string, StationRatings>();

/** Compute the reference from the same rated records that form the cohort. */
function cohortMedians(key: string, ratings: StationRatings[]): StationRatings {
  const cached = medianCache.get(key);
  if (cached) return cached;
  const medians = Object.fromEntries(GUIDE_CATEGORIES.map(category => {
    const values = ratings.map(row => row[category]).sort((a, b) => a - b);
    const middle = Math.floor(values.length / 2);
    return [category, values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2];
  })) as unknown as StationRatings;
  medianCache.set(key, medians);
  return medians;
}

function overviewSentence(text: string | undefined): string | undefined {
  if (!text) return undefined;
  // Keep the locality-setting lead. Longer editorial judgments and numerical
  // claims remain in the full notes, beside their category/source context.
  return (text.match(/^[\s\S]*?(?:[。！？]|[.!?](?=\s|$))/u)?.[0] ?? text).trim();
}

function nearbyTokyo(slug: string, lat: number, lng: number): string[] {
  const cached = nearbyCache.get(slug);
  if (cached) return cached;
  const longitudeScale = Math.cos(lat * Math.PI / 180);
  const nearby = getStations().filter(s => s.slug !== slug && s.ratings)
    .map(s => ({ slug: s.slug, distance: (s.lat - lat) ** 2 + ((s.lng - lng) * longitudeScale) ** 2 }))
    .sort((a, b) => a.distance - b.distance).slice(0, 5).map(s => s.slug);
  nearbyCache.set(slug, nearby);
  return nearby;
}

function outdoorNoise(city: CityId, slug: string): AreaGuideData['noise'] {
  const fact = getQuietness(city, slug);
  if (fact?.status !== 'available' || fact.day == null || fact.night == null) return null;
  return { day: fact.day, night: fact.night, date: fact.data_date, transferred: fact.calibration === 'uncalibrated_transfer' };
}

function tokyoPhoto(slug: string, name: string, localName: string): AreaGuideData['photo'] {
  const list = photos[slug] ?? [];
  const approved: Record<string, number> = { kichijoji: 2, nakano: 7, shinjuku: 0 };
  const photo = list[approved[slug]] ?? list.find(p => p.alt.includes(localName) || p.alt.toLowerCase().includes(name.toLowerCase()))
    ?? list.find(p => !/portrait|selfie|sleep|baby|美女/i.test(p.alt));
  return photo ? { url: photo.url, alt: photo.alt, credit: photo.photographer ?? photo.attribution ?? '', license: photo.license ?? '', href: photo.flickr_url ?? photo.photographer_url ?? photo.url } : null;
}

export async function buildAreaGuide(city: CityId, kind: GuideKind, slug: string, locale: Locale): Promise<AreaGuideData | null> {
  const t = await getTranslations({ locale, namespace: 'areaGuide' });
  if (city === 'tokyo') {
    const station = getStation(slug);
    if (!station) return null;
    const names = stationDisplayName(station, locale);
    const rent = station.rent_avg;
    const localRent = isStationLevelRent(rent);
    const nearby = nearbyTokyo(slug, station.lat, station.lng);
    const peers: GuidePeer[] = nearby.flatMap(key => {
      const peer = getStation(key);
      return peer?.ratings ? [{ key, name: stationDisplayName(peer, locale).primary, href: areaPath(city, key), ratings: peer.ratings }] : [];
    });
    const environment = station.environment;
    return {
      city, kind: 'station', key: slug, slug, locale,
      name: names.primary, localName: names.secondary,
      summary: copy[`tokyo:station:${slug}`]?.[locale] ?? t('summary.tokyo', { name: names.primary, count: station.line_count }),
      ratings: station.ratings, medians: cohortMedians('tokyo:station', getStations().flatMap(s => s.ratings ? [s.ratings] : [])),
      confidence: station.confidence ?? {}, sources: station.sources ?? {},
      peerCount: getStations().filter(s => s.ratings).length, peers, date: station.data_date ?? null,
      photo: tokyoPhoto(slug, station.name_en, station.name_jp),
      rent: {
        values: [{ layout: 'smallTokyo', value: rent?.['1k_1ldk'] ?? null }, { layout: 'largeTokyo', value: rent?.['2ldk'] ?? null }],
        provenance: localRent ? 'stationAverage' : rent?.source === 'estat' ? 'municipalAverage' : 'estimate',
        date: rent?.updated ?? null, samples: null, skewed: false,
        sources: rent ? [{ label: localRent ? 'SUUMO' : rent.source === 'estat' ? 'e-Stat' : t('methodology'), href: localRent ? 'https://suumo.jp/' : rent.source === 'estat' ? 'https://www.e-stat.go.jp/' : '/methodology' }] : [],
      },
      commute: station.transit_minutes ?? {}, lastTrain: station.last_train?.weekday ?? null,
      lines: station.lines.map(line => ({ name: locale === 'ja' ? line.name_ja : line.name_en, color: line.color })),
      stationCount: 1,
      facts: [{ key: 'services', value: station.line_count }, ...(environment?.elevation_m != null ? [{ key: 'elevation' as const, value: environment.elevation_m, unit: 'm' as const }] : [])],
      areaKm2: null,
      map: {
        center: [station.lat, station.lng],
        bbox: [[station.lat - 0.009, station.lng - 0.012], [station.lat + 0.009, station.lng + 0.012]],
        polygons: null, lineIds: [],
        stations: [station, ...nearby.slice(0, 4).map(getStation).filter(s => s !== undefined)].map(s => ({ id: s.slug, name: stationDisplayName(s, locale).primary, lat: s.lat, lng: s.lng, selected: s.slug === slug })),
      },
      noise: outdoorNoise(city, slug), mapHref: `/?s=${encodeURIComponent(slug)}`,
      mapsHref: getGoogleMapsAreaUrl(station.lat, station.lng), methodologyHref: '/methodology',
    };
  }

  const district = kind === 'district' ? getBangkokDistrict(slug) : undefined;
  const station = kind === 'station' ? getBangkokStationArea(slug) : undefined;
  const area = district ?? station;
  if (!area) return null;
  const names = stationDisplayName(area, locale);
  const key = kind === 'station' ? stationAreaKey(slug) : slug;
  const shapes = (kind === 'district' ? districtGeometry : stationGeometry) as unknown as Record<string, Shape>;
  const shape = shapes[slug];
  const rent = area.rent;
  const peerAreas = kind === 'district'
    ? area.neighbors.map(getBangkokDistrict).filter(d => d !== undefined)
    : area.neighbors.map(getBangkokStationArea).filter(d => d !== undefined);
  const peers = peerAreas.slice(0, 6).map(peer => {
    const peerKey = 'id' in peer ? stationAreaKey(peer.id) : peer.slug;
    return { key: peerKey, name: stationDisplayName(peer, locale).primary, href: areaPath(city, peerKey), ratings: peer.ratings };
  });
  const stations = [...new Set([...area.station_ids, ...(district?.nearby_station_ids ?? [])])].map(getRailStation).filter(s => s !== undefined);
  const f = area.facts;
  const facts: AreaGuideData['facts'] = [
    { key: 'food', value: f.food }, { key: 'essentials', value: f.essentials },
    { key: 'sports', value: f.sports }, { key: 'green', value: f.park_ha, unit: 'ha' },
    ...('cafes' in f ? [{ key: 'cafes' as const, value: f.cafes }] : []),
    { key: 'markets', value: f.markets }, { key: 'culture', value: f.culture },
    { key: 'temples', value: f.temples }, { key: 'piers', value: f.piers },
    { key: 'nightlife', value: f.nightlife }, { key: 'area', value: f.area_km2, unit: 'km2' },
  ];
  return {
    city, kind, key, slug, locale, name: names.primary, localName: names.secondary,
    summary: copy[`bangkok:${kind}:${slug}`]?.[locale] ?? (overviewSentence(district?.description?.[locale]?.atmosphere) || t(`summary.${kind}`, { name: names.primary, count: area.line_ids.length })),
    ratings: area.ratings, medians: cohortMedians(`bangkok:${kind}`, (kind === 'district' ? getBangkokDistricts() : getBangkokStationAreas()).map(a => a.ratings)), confidence: area.confidence, sources: area.sources,
    peerCount: kind === 'district' ? getBangkokDistricts().length : getBangkokStationAreas().length,
    peers, date: area.data_date,
    photo: area.image ? { url: area.image.hero, alt: `${names.primary} · ${t('cities.bangkok')}`, credit: area.image.artist, license: area.image.license, href: area.image.page } : null,
    rent: {
      values: [{ layout: 'oneBedroom', value: rent.one_bed }, { layout: 'twoBedroom', value: rent.two_bed }],
      provenance: rent.metric === 'median_asking_by_bedroom' ? 'bedroomMedian' : rent.provenance === 'district_blend' ? 'districtBlend' : 'estimate',
      date: rent.as_of, samples: rent.sample_size ? { one: rent.sample_size.one_bed, two: rent.sample_size.two_bed } : null,
      skewed: rent.composition_skew === true,
      sources: rent.sources.length ? rent.sources.map(source => ({ label: source.publisher, href: source.url })) : [{ label: t('methodology'), href: '/methodology#bangkok' }],
    },
    commute: area.transit_minutes, lastTrain: null,
    lines: area.line_ids.map(getRailLine).filter(line => line !== undefined).map(line => ({ name: locale === 'ja' ? line.name_ja : locale === 'ru' ? line.name_ru : line.name_en, color: line.color })),
    stationCount: area.station_ids.length, facts, areaKm2: f.area_km2,
    map: {
      center: [area.lat, area.lng],
      bbox: shape?.bbox ?? [[area.lat - 0.009, area.lng - 0.012], [area.lat + 0.009, area.lng + 0.012]],
      polygons: shape?.polygons ?? null, lineIds: area.line_ids,
      stations: stations.map(s => ({ id: s.id, name: locale === 'ja' && s.name_ja ? s.name_ja : s.name_en, lat: s.lat, lng: s.lng, selected: area.station_ids.includes(s.id) })),
    },
    noise: kind === 'station' ? outdoorNoise(city, slug) : null,
    mapHref: `/bangkok?lv=${kind}&s=${encodeURIComponent(key)}`,
    mapsHref: getGoogleMapsAreaUrl(area.lat, area.lng), methodologyHref: '/methodology#bangkok',
  };
}
