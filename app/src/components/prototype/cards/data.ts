// Prototype adapter: preserve published values and provenance; presentation copy
// below edits the existing neighborhood descriptions without changing the data.
import { getStation, getStations } from '@/lib/data';
import { getBangkokDistrict, getBangkokDistricts, getBangkokStationArea, getBangkokStationAreas, getRailLine, getRailStation } from '@/lib/bangkok-data';
import { CITIES } from '@/lib/cities';
import { isStationLevelRent } from '@/lib/scoring';
import { getQuietness } from '@/lib/quietness';
import images from '@/data/station-images-all.json';
import districtGeometry from '@/data/bangkok/geometry.json';
import stationGeometry from '@/data/bangkok/station-geometry.json';
import type { CardArea, Point } from './model';

type Shape = { polygons: Point[][][]; bbox: [Point, Point] };
type Story = Pick<CardArea, 'summary' | 'strengths' | 'tradeoffs'>;

const STORIES: Record<string, Story> = {
  kichijoji: {
    summary: 'Park walks, busy shopping streets and late-night dining on Tokyo’s west side. A lively base around Inokashira Park and Harmonica Yokocho.',
    strengths: ['Inokashira Park and neighborhood shopping streets.', 'A broad choice of cafés, restaurants and evening spots.'],
    tradeoffs: ['The station area stays busy into the evening.', 'Check the rent and your actual commute before choosing a home.'],
  },
  nakano: {
    summary: 'Shopping arcades, small dining streets and pop culture around Nakano Broadway. A dense neighborhood on the Chuo line, with redevelopment around the station.',
    strengths: ['Nakano Broadway, Sun Mall and Shiki no Mori Park.', 'A substantial local dining and izakaya scene.'],
    tradeoffs: ['Crowded streets around the station and arcades.', 'The station core and surrounding residential lanes have different characters.'],
  },
  shinjuku: {
    summary: 'A major interchange surrounded by offices, shopping and a large evening economy. West-side towers, Shinjuku Gyoen and Kabukicho offer very different settings.',
    strengths: ['Extensive rail connections and everyday services.', 'A wide choice of dining and late-night venues.'],
    tradeoffs: ['Heavy foot traffic and busy entertainment streets.', 'The area-level safety score does not describe every street or time of day.'],
  },
  asok: {
    summary: 'An interchange between Asok on the BTS and Sukhumvit on the MRT. The mapped area has a dense mix of restaurants, cafés and evening venues.',
    strengths: ['Connections to both the BTS Sukhumvit and MRT Blue lines.', 'Many mapped dining and everyday-service options.'],
    tradeoffs: ['The area scores low for the crowding-based ranking.', 'Published rents cover mixed apartment sizes from one provider.'],
  },
  ari: {
    summary: 'A station area on the BTS Sukhumvit line, with a substantial mapped café and dining scene. Its rent figure is an estimate inherited from the district.',
    strengths: ['Cafés and restaurants within the mapped area.', 'BTS Sukhumvit service toward Siam and Mo Chit.'],
    tradeoffs: ['One rail line; destination matters for the commute.', 'Rent and safety use district-level editorial estimates.'],
  },
  'phrom-phong': {
    summary: 'A BTS Sukhumvit station area with a dense mix of dining, fitness and evening options. The source’s asking-rent sample is skewed toward larger or luxury units.',
    strengths: ['A large mapped selection of restaurants and sports facilities.', 'A direct connection along the BTS Sukhumvit line.'],
    tradeoffs: ['The rent proxy is not a typical fixed-size apartment rent.', 'Busy surroundings and a low crowding-based ranking.'],
  },
  'pathum-wan': {
    summary: 'Bangkok’s central shopping district, with extensive rail connections, major malls and Lumphini Park. High rents and busy streets are the main trade-offs.',
    strengths: ['Rail connections across Siam, Chit Lom and Sam Yan.', 'Parks, shopping, dining and cultural venues across the district.'],
    tradeoffs: ['One of the highest reference rents among Bangkok districts.', 'A district average can hide large differences between streets.'],
  },
  sathon: {
    summary: 'Office towers and hotels along Sathorn Road, with quieter lanes in Suan Phlu and Yen Akat. Rail access and the feel of daily life vary across the district.',
    strengths: ['Office-lunch options, markets and established dining streets.', 'BTS connections along Sathorn Road, with MRT access near the edges.'],
    tradeoffs: ['The district-wide commute is not a prediction for every address.', 'Rent and safety remain editorial district estimates.'],
  },
  'bang-na': {
    summary: 'Bangkok’s southeastern stretch of Sukhumvit, with condos near the BTS and residential streets around La Salle and Udom Suk. More affordable reference rents, with longer trips to central hubs.',
    strengths: ['A lower reference rent than central Bangkok districts.', 'Shopping, markets and dining around Udom Suk and La Salle.'],
    tradeoffs: ['Longer modeled trips to the central hubs.', 'Limited mapped park space across a large district.'],
  },
};

function required<T>(value: T | undefined, label: string): T {
  if (value === undefined) throw new Error(`Missing prototype data: ${label}`);
  return value;
}

function noise(city: 'tokyo' | 'bangkok', slug: string): CardArea['noise'] {
  const fact = getQuietness(city, slug);
  return fact?.status === 'available' && fact.day != null && fact.night != null
    ? { day: fact.day, night: fact.night, date: fact.data_date, transferred: fact.calibration === 'uncalibrated_transfer' }
    : null;
}

function tokyo(slug: string): CardArea {
  const station = required(getStation(slug), slug);
  const ratings = required(station.ratings ?? undefined, `${slug} ratings`);
  const photoIndex: Record<string, number> = { kichijoji: 2, nakano: 7, shinjuku: 0 };
  const photo = (images as Record<string, { url: string; alt: string; photographer?: string; attribution?: string; license?: string; flickr_url?: string }[]>)[slug]?.[photoIndex[slug] ?? 0];
  const center: Point = [station.lat, station.lng];
  const rent = station.rent_avg;
  const stationRent = isStationLevelRent(rent);
  const nearby = getStations().filter(s => Math.abs(s.lat - station.lat) < 0.022 && Math.abs(s.lng - station.lng) < 0.027);
  const env = station.environment;
  const context: CardArea['context'] = [];
  if (env?.seismic_prob_i60 != null) context.push({
    title: 'Earthquake context',
    text: `${(env.seismic_prob_i60 * 100).toFixed(1)}% modeled probability of JMA intensity ≥6 in 30 years. This describes shaking at the mapped point, not the resilience of a building.`,
    href: '/methodology',
  });
  if (env?.flood_depth_m != null && env.flood_depth_m >= 0.5) context.push({
    title: 'Flood context', text: `${env.flood_depth_m} m expected inundation depth in the source’s official flood-zone scenario. Check the address and building.`, href: '/methodology',
  });
  return {
    id: `tokyo-${slug}`, slug, group: 'tokyo-station', city: 'tokyo', kind: 'station',
    name: station.name_en, localName: station.name_jp, location: 'Greater Tokyo · station area',
    ...STORIES[slug], ratings, medians: CITIES.tokyo.medians,
    confidence: station.confidence ?? {}, sources: station.sources ?? {},
    peerCount: getStations().filter(s => s.ratings).length, dataDate: station.data_date ?? null,
    photo: photo ? { url: photo.url, alt: photo.alt, credit: photo.photographer ?? photo.attribution ?? 'Flickr contributor', license: photo.license ?? '', href: photo.flickr_url ?? photo.url } : null,
    rent: {
      values: [{ label: '1K–1LDK', value: rent?.['1k_1ldk'] ?? null }, { label: '2LDK', value: rent?.['2ldk'] ?? null }],
      label: stationRent ? 'Station listing average' : rent?.source === 'estat' ? 'Municipal average' : 'Editorial estimate',
      date: rent?.updated ?? null,
      detail: stationRent ? 'Existing station-level asking-rent averages. The two figures describe different apartment layouts, not a price range.' : 'An area-level average or editorial estimate, rather than observed asking rents for this station alone.',
      limitations: ['Apartment sizes, building age and listing mix are not standardized in these headline averages.', 'Asking rents are not signed leases. The reference is a guide, not a quotation for a home.'],
      samples: null, skewed: false,
      sources: [{ label: stationRent ? 'SUUMO' : rent?.source === 'estat' ? 'e-Stat' : 'Methodology', href: stationRent ? 'https://suumo.jp/' : rent?.source === 'estat' ? 'https://www.e-stat.go.jp/' : '/methodology' }],
    },
    commute: station.transit_minutes ?? {},
    commuteNote: 'Existing hub estimates: researched entries may use authored values; computed entries use a calibrated model. These are not live timetable routes.',
    lastTrain: station.last_train?.weekday ?? null,
    lines: station.lines.map(l => ({ name: l.name_en, color: l.color })), stationCount: 1,
    facts: [{ label: 'Rail services', value: station.line_count }, ...(env?.elevation_m != null ? [{ label: 'Elevation', value: env.elevation_m, unit: 'm' }] : [])],
    factsNote: 'Tokyo input catchments vary by category. The map’s 800 m circle is a reference radius, not a common boundary for every score.',
    map: { center, bbox: [[station.lat - 0.009, station.lng - 0.012], [station.lat + 0.009, station.lng + 0.012]], polygons: null,
      scope: '800 m reference radius · straight-line distance', stationIds: [slug],
      stations: nearby.map(s => ({ id: s.slug, name: s.name_en, lat: s.lat, lng: s.lng })), lineIds: [] },
    noise: noise('tokyo', slug), context,
    detailHref: `/station/${slug}`, mapHref: `/?s=${slug}`, methodologyHref: '/methodology',
  };
}

function bangkok(slug: string, kind: 'station' | 'district'): CardArea {
  const district = kind === 'district' ? required(getBangkokDistrict(slug), slug) : null;
  const station = kind === 'station' ? required(getBangkokStationArea(slug), slug) : null;
  const area = required(district ?? station ?? undefined, slug);
  const rent = area.rent;
  const shapes = (kind === 'district' ? districtGeometry : stationGeometry) as unknown as Record<string, Shape>;
  const shape = required(shapes[slug], `${slug} geometry`);
  const registry = CITIES.bangkok.levelStats[kind]!;
  const proxy = rent.metric === 'median_asking_by_bedroom';
  const allStations = [...new Set([...area.station_ids, ...(district?.nearby_station_ids ?? [])])].map(getRailStation).filter(s => s !== undefined);
  const bbox = shape.bbox;
  const f = area.facts;
  return {
    id: `bangkok-${kind}-${slug}`, slug, group: kind === 'district' ? 'bangkok-district' : 'bangkok-station', city: 'bangkok', kind,
    name: area.name_en, localName: area.name_th, location: `Bangkok · ${kind === 'district' ? 'district' : 'station area'}`,
    ...STORIES[slug], ratings: area.ratings, medians: registry.medians,
    confidence: area.confidence, sources: area.sources,
    peerCount: kind === 'district' ? getBangkokDistricts().length : getBangkokStationAreas().length,
    dataDate: area.data_date,
    photo: area.image ? { url: area.image.hero, alt: `${area.name_en}, Bangkok`, credit: area.image.artist, license: area.image.license, href: area.image.page } : null,
    rent: {
      values: [{ label: '1 bedroom', value: rent.one_bed }, { label: '2 bedrooms', value: rent.two_bed }],
      label: proxy ? 'Asking-rent median · mixed sizes' : 'Editorial rent estimate', date: rent.as_of,
      detail: proxy ? 'Published bedroom medians from one provider’s station-radius inventory. All floor areas; the source radius differs from this map’s catchment.' : `Researcher estimates for a 30–35 m² 1BR or 60–70 m² 2BR condo.${rent.provenance === 'district_blend' ? ' Blended from district estimates by resident share.' : ''} These are not statistical medians.`,
      limitations: proxy ? ['One provider’s available inventory, not signed leases or a representative market sample.', 'Floor area, lease duration and serviced-apartment mix are not controlled.'] : ['District-level estimates do not describe every street, building or apartment.', 'The reference excludes serviced apartments and short stays.'],
      samples: rent.sample_size ? `1BR: ${rent.sample_size.one_bed} listings · 2BR: ${rent.sample_size.two_bed} listings` : null,
      skewed: rent.composition_skew === true,
      sources: rent.sources.length ? rent.sources.map(s => ({ label: s.publisher, href: s.url })) : [{ label: 'Rent methodology', href: '/methodology#bangkok' }],
    },
    commute: area.transit_minutes,
    commuteNote: kind === 'district' ? 'Modeled peak-hour, door-to-hub minutes for the median resident. Conditions vary within the district; these are not live routes.' : 'Modeled peak-hour minutes from the station to each hub. Your walk to the station is additional; these are not live routes.',
    lastTrain: null,
    lines: area.line_ids.map(getRailLine).filter(l => l !== undefined).map(l => ({ name: l.name_en, color: l.color })),
    stationCount: area.station_ids.length,
    facts: [{ label: 'Places to eat & drink', value: f.food }, { label: 'Everyday services', value: f.essentials }, { label: 'Gyms & sports', value: f.sports }, { label: 'Mapped green space', value: f.park_ha, unit: 'ha' }],
    factsNote: `Approximate counts inside the ${kind === 'district' ? 'district boundary' : 'station catchment'} (${f.area_km2} km²). They describe mapped supply, not the walk from a particular home. Places: Overture Maps; parks: OpenStreetMap.`,
    map: { center: [area.lat, area.lng], bbox, polygons: shape.polygons,
      scope: kind === 'district' ? 'Published district boundary' : 'Nearest-station catchment · up to 800 m',
      stationIds: area.station_ids, stations: allStations.map(s => ({ id: s.id, name: s.name_en, lat: s.lat, lng: s.lng })), lineIds: area.line_ids },
    noise: kind === 'station' ? noise('bangkok', slug) : null,
    context: district?.flood ? [{ title: 'Reported street flooding', text: `${district.flood.episodes_total} reported episodes in 2021–2026 across the district. Reporting coverage varies; this is not an address-level flood probability.`, href: '/methodology#bangkok' }] : [],
    detailHref: `/bangkok/${kind}/${slug}`, mapHref: `/bangkok?lv=${kind}&s=${kind === 'station' ? 'st.' : ''}${slug}`,
    methodologyHref: '/methodology#bangkok',
  };
}

export function getPrototypeAreas(): CardArea[] {
  return [tokyo('kichijoji'), tokyo('nakano'), tokyo('shinjuku'), bangkok('asok', 'station'), bangkok('ari', 'station'), bangkok('phrom-phong', 'station'), bangkok('pathum-wan', 'district'), bangkok('sathon', 'district'), bangkok('bang-na', 'district')];
}
