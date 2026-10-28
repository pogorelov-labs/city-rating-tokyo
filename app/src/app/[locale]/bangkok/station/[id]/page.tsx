import RatingsBreakdown from '@/components/RatingsBreakdown';
import { FactsGrid, WikiLinks } from '@/components/DetailFacts';
import { InstitutionFacts } from '@/components/InstitutionFacts';
import { getInstitutions } from '@/lib/institutions';
import { hasLocale } from 'next-intl';
import AirPanel from '@/components/AirPanel';
import { QuietnessFacts } from '@/components/QuietnessFacts';
import { getQuietness } from '@/lib/quietness';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import { routing, type Locale } from '@/i18n/routing';
import { CityProvider } from '@/lib/city-context';
import { CITIES, areaPath, formatRentShort } from '@/lib/cities';
import {
  getBangkokDistrict,
  getBangkokMapDistricts,
  getBangkokStationArea,
  getBangkokStationAreaIds,
  getRailLine,
  getRailStation,
} from '@/lib/bangkok-data';
import { stationAreaKey } from '@/lib/area-key';
import {
  calculateWeightedScore,
  compositeToColor,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS, getGoogleMapsAreaUrl } from '@/lib/types';
import { stationDisplayName, stationPrimaryName } from '@/lib/station-name';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import RentNote from '@/components/bangkok/RentNote';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import FeedbackWidget from '@/components/FeedbackWidget';
import DetailHeader from '@/components/DetailHeader';

const CITY = CITIES.bangkok;
const STATS = CITY.levelStats.station!;

export function generateStaticParams() {
  const ids = getBangkokStationAreaIds();
  return routing.locales.flatMap((locale) => ids.map((id) => ({ locale, id })));
}

/** JA pages lead with the katakana name, every other locale with the Latin
 *  name on the station signs; Thai is always the secondary line. */
function areaNames(id: string, locale: Locale) {
  const a = getBangkokStationArea(id)!;
  return stationDisplayName({ name_en: a.name_en, name_jp: a.name_jp, name_th: a.name_th }, locale);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const area = getBangkokStationArea(id);
  const t = await getTranslations({ locale, namespace: 'bangkok.station' });
  if (!area) return { title: t('notFound') };
  const { primary } = areaNames(id, locale as Locale);
  const district = getBangkokDistrict(area.district);
  const districtName = district ? stationPrimaryName(district, locale as Locale) : area.district;
  const desc = t('metaDescription', { name: primary, district: districtName });
  return {
    title: t('metaTitle', { name: primary, nameTh: area.name_th }),
    description: desc,
    openGraph: {
      title: `${primary} (${area.name_th})`,
      description: desc,
      type: 'article',
      ...(area.image && { images: [{ url: area.image.hero }] }),
    },
  };
}

export default async function StationAreaPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const loc = locale as Locale;
  const t = await getTranslations();

  const a = getBangkokStationArea(id);
  if (!a) notFound();

  const { primary: displayName, secondary: thaiName } = areaNames(id, loc);
  const score = calculateWeightedScore(a.ratings, DEFAULT_WEIGHTS);
  const mapsUrl = getGoogleMapsAreaUrl(a.lat, a.lng);
  const members = a.station_ids.map(getRailStation).filter((s) => s !== undefined);
  const lines = a.line_ids.map(getRailLine).filter((l) => l !== undefined);
  const lineName = (l: { name_en: string; name_ja: string; name_ru: string }) =>
    loc === 'ja' ? l.name_ja : loc === 'ru' ? l.name_ru : l.name_en;
  const stationName = (s: { name_en: string; name_ja?: string | null }) =>
    loc === 'ja' && s.name_ja ? s.name_ja : s.name_en;
  const hubValues = Object.values(a.transit_minutes);
  const avgHub = Math.round(hubValues.reduce((x, y) => x + y, 0) / hubValues.length);
  const residentValues = Object.values(a.resident_minutes);
  const residentMin = Math.min(...residentValues);
  const mapDistricts = getBangkokMapDistricts();
  const districtBySlug = new Map(mapDistricts.map((d) => [d.slug, d]));
  const neighbors = a.neighbors
    .map((n) => getBangkokStationArea(n))
    .filter((n) => n !== undefined)
    .map((n) => ({ ...n, score: calculateWeightedScore(n.ratings, DEFAULT_WEIGHTS) }))
    .sort((x, y) => y.score - x.score);
  const wikiOrder: ('en' | 'ja' | 'ru' | 'th')[] = [loc, 'th', ...(['en', 'ja', 'ru'] as const).filter((l) => l !== loc)];
  const wikiLinks = wikiOrder.filter((l) => a.wikipedia[l]).map((l) => ({ lang: l, url: a.wikipedia[l]! }));
  const f = a.facts;
  const nf = new Intl.NumberFormat(loc === 'en' ? 'en-US' : loc);
  const mapHref = { pathname: CITY.homePath, query: { lv: 'station', s: stationAreaKey(a.id) } };
  const gridHref = { pathname: CITY.homePath, query: { lv: 'grid', s: stationAreaKey(a.id) } };

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: `${displayName} station area, Bangkok`,
    alternateName: [a.name_th, a.name_en].filter((n) => n !== displayName),
    inLanguage: locale,
    containedInPlace: { '@type': 'City', name: 'Bangkok' },
    geo: { '@type': 'GeoCoordinates', latitude: a.lat, longitude: a.lng },
    ...(a.wikipedia.en && { sameAs: a.wikipedia.en }),
  };

  return (
    <CityProvider city="bangkok">
      <div className="min-h-screen bg-gray-50">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

        <DetailHeader homeHref={mapHref} backLabel={t('bangkok.station.backToMap')} primary={displayName} secondary={thaiName}
        mapsUrl={mapsUrl} mapsTitle={t('station.mapsTooltip')} mapsLabel={t('station.mapsLink')} areaKey={stationAreaKey(a.id)}
        score={score} scoreColor={compositeToColor(score, STATS.defaultAnchors)} scoreTitle={t('bangkok.station.scoreTooltip')} />

        <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          {a.image && (
            <figure className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={a.image.hero}
                alt={t('bangkok.station.imageAlt', { name: displayName })}
                className="w-full h-48 md:h-64 object-cover"
                loading="eager"
              />
              <figcaption className="px-3 py-1.5 text-[10px] text-gray-400 truncate">
                <a href={a.image.page} target="_blank" rel="noopener noreferrer" className="hover:text-gray-600">
                  {t('bangkok.district.imageCredit', { artist: a.image.artist, license: a.image.license })}
                </a>
              </figcaption>
            </figure>
          )}

          {/* Quick stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label={t('bangkok.station.linesLabel')} sub={t('filter.stations', { count: members.length })}>
              <div className="text-xl font-bold">{t('filter.lines', { count: lines.length })}</div>
            </StatCard>
            <StatCard label={t('bangkok.district.rentLabel')} sub={t('bangkok.station.rentSub')}>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">{formatRentShort('bangkok', a.rent.one_bed ?? 0)}</span>
                {a.rent.two_bed && (
                  <>
                    <span className="text-xs text-gray-400">–</span>
                    <span className="text-xl font-bold">{formatRentShort('bangkok', a.rent.two_bed)}</span>
                  </>
                )}
              </div>
              <RentNote rent={a.rent} />
            </StatCard>
            <StatCard label={t('bangkok.station.fromStation')} value={`${avgHub} min`} sub={t('bangkok.station.fromStationSub')} />
            <StatCard
              label={t('bangkok.station.residentLabel')}
              value={`${residentMin} min`}
              sub={t('bangkok.station.residentSub')}
            />
          </div>

          <HubStrip transitMinutes={a.transit_minutes} mapsUrl={mapsUrl} />

          {/* Stations & lines */}
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-1">{t('bangkok.station.stationsTitle')}</h2>
            <p className="text-[11px] text-gray-500 mb-3">
              {t(members.length > 1 ? 'bangkok.station.interchangeCaption' : 'bangkok.station.stationsCaption')}
            </p>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {lines.map((l) => (
                <span
                  key={l.id}
                  className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-700"
                >
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} aria-hidden />
                  {lineName(l)}
                </span>
              ))}
            </div>
            <ul className="space-y-1.5">
              {members.map((s) => (
                <li key={s.id} className="flex items-center gap-2 text-sm">
                  <span className="flex gap-0.5 shrink-0" aria-hidden>
                    {s.lines.map((lid) => (
                      <span key={lid} className="h-2 w-2 rounded-full" style={{ backgroundColor: getRailLine(lid)?.color }} />
                    ))}
                  </span>
                  <span className="font-medium">{stationName(s)}</span>
                  <span className="text-gray-400 text-xs">{s.name_th}</span>
                </li>
              ))}
            </ul>
            {neighbors.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="text-xs text-gray-500 mb-2">{t('bangkok.station.nextStops')}</div>
                <div className="flex flex-wrap gap-2">
                  {neighbors.map((n) => (
                    <Link
                      key={n.id}
                      href={areaPath('bangkok', stationAreaKey(n.id))}
                      className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 text-sm hover:bg-gray-50"
                      data-umami-event="neighbor-station-area"
                      data-umami-event-station={n.id}
                    >
                      <span className="font-medium">
                        {stationPrimaryName({ name_en: n.name_en, name_jp: n.name_jp, name_th: n.name_th }, loc)}
                      </span>
                      <span className="font-bold tabular-nums text-xs" style={{ color: compositeToColor(n.score, STATS.defaultAnchors) }}>
                        {n.score.toFixed(1)}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Radar + Ratings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">{t('station.overview')}</h2>
              <RadarChartWrapper
                ratings={a.ratings}
                medians={STATS.medians}
                medianLabel={t('bangkok.station.radarMedianLabel')}
                areaLabel={t('bangkok.station.radarAreaLabel')}
              />
            </section>
            <RatingsBreakdown kind="station" ratings={a.ratings} medians={STATS.medians} confidence={a.confidence} sources={a.sources} dataDate={a.data_date} rent={a.rent} />
          </div>

          <AirPanel city="bangkok" />
        <InstitutionFacts fact={getInstitutions('bangkok', 'station', a.id)} />
          <QuietnessFacts fact={getQuietness('bangkok', a.id)} />

          {/* By the numbers */}
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-3">{t('bangkok.station.factsTitle')}</h2>
            <FactsGrid>
              {(
                [
                  ['factFood', f.food],
                  ['factCafes', f.cafes],
                  ['factNightlife', f.nightlife],
                  ['factConvenience', f.convenience],
                  ['factEssentials', f.essentials],
                  ['factMarkets', f.markets],
                  ['factSports', f.sports],
                  ['factCulture', f.culture],
                  ['factTemples', f.temples],
                ] as const
              ).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs text-gray-500">
                    {t(key === 'factCafes' ? 'bangkok.station.factCafes' : `bangkok.district.${key}`)}
                  </dt>
                  <dd className="font-semibold tabular-nums">{nf.format(value)}</dd>
                </div>
              ))}
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factParks')}</dt>
                <dd className="font-semibold tabular-nums">{nf.format(f.park_ha)} ha</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factArea')}</dt>
                <dd className="font-semibold tabular-nums">{nf.format(f.area_km2)} km²</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factPiers')}</dt>
                <dd className="font-semibold tabular-nums">{nf.format(f.piers)}</dd>
              </div>
              {a.hotels_800m != null && (
                <div>
                  <dt className="text-xs text-gray-500">{t('bangkok.station.factHotels')}</dt>
                  <dd className="font-semibold tabular-nums">
                    {nf.format(a.hotels_800m)}
                    {a.tourist_badge && (
                      <span className="ml-1.5 inline-flex items-center rounded-full bg-sky-50 border border-sky-200 px-1.5 py-0.5 text-[10px] font-medium text-sky-700">
                        {t('station.touristLoad')}
                      </span>
                    )}
                  </dd>
                </div>
              )}
              {a.attractions_800m != null && (
                <div>
                  <dt className="text-xs text-gray-500">{t('bangkok.station.factAttractions')}</dt>
                  <dd className="font-semibold tabular-nums">{nf.format(a.attractions_800m)}</dd>
                </div>
              )}
            </FactsGrid>
            <p className="mt-3 pt-2 border-t border-gray-100 text-[10px] text-gray-400 leading-relaxed">
              {t('bangkok.station.factsSource')}
            </p>
          </section>

          {/* Districts covered */}
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-1">{t('bangkok.station.districtsTitle')}</h2>
            <p className="text-[11px] text-gray-500 mb-3">{t('bangkok.station.districtsCaption')}</p>
            <div className="flex flex-wrap gap-2">
              {a.districts.map(({ slug, share }) => {
                const d = districtBySlug.get(slug);
                if (!d) return null;
                const dScore = calculateWeightedScore(d.ratings!, DEFAULT_WEIGHTS);
                return (
                  <Link
                    key={slug}
                    href={areaPath('bangkok', slug)}
                    className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 text-sm hover:bg-gray-50"
                    data-umami-event="station-area-district"
                    data-umami-event-station={slug}
                  >
                    <span className="font-medium">{stationPrimaryName(d, loc)}</span>
                    <span className="text-xs text-gray-400 tabular-nums">{Math.round(share * 100)}%</span>
                    <span className="font-bold tabular-nums text-xs" style={{ color: compositeToColor(dScore, CITY.defaultAnchors) }}>
                      {dScore.toFixed(1)}
                    </span>
                  </Link>
                );
              })}
            </div>
            <Link
              href={gridHref}
              className="mt-3 inline-block text-xs text-blue-600 hover:underline"
              data-umami-event="station-area-grid"
              data-umami-event-station={a.id}
            >
              {t('bangkok.station.viewGrid')}
            </Link>
          </section>

          <WikiLinks links={wikiLinks} label={t('bangkok.district.readMore')} />

          <FeedbackWidget stationSlug={stationAreaKey(a.id)} stationName={displayName} source="station_page" />
        </main>
      </div>
    </CityProvider>
  );
}
