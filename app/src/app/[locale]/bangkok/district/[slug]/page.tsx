import RatingsBreakdown from '@/components/RatingsBreakdown';
import { FactsGrid, WikiLinks } from '@/components/DetailFacts';
import { InstitutionFacts } from '@/components/InstitutionFacts';
import { getInstitutions } from '@/lib/institutions';
import { hasLocale } from 'next-intl';
import AirPanel from '@/components/AirPanel';
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
  getBangkokSlugs,
  getRailLine,
  getRailStation,
} from '@/lib/bangkok-data';
import {
  calculateWeightedScore,
  compositeToColor,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS, getGoogleMapsAreaUrl } from '@/lib/types';
import { stationDisplayName } from '@/lib/station-name';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import RentNote from '@/components/bangkok/RentNote';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import FeedbackWidget from '@/components/FeedbackWidget';
import DetailHeader from '@/components/DetailHeader';

const CITY = CITIES.bangkok;

export function generateStaticParams() {
  const slugs = getBangkokSlugs();
  return routing.locales.flatMap((locale) => slugs.map((slug) => ({ locale, slug })));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const district = getBangkokDistrict(slug);
  const t = await getTranslations({ locale, namespace: 'bangkok.district' });
  if (!district) return { title: t('notFound') };
  const { primary } = stationDisplayName(district, locale as Locale);
  const atmosphere = district.description?.[locale as Locale]?.atmosphere;
  const desc = atmosphere ? atmosphere.slice(0, 155) : t('metaDescriptionFallback', { name: primary });
  return {
    title: t('metaTitle', { name: primary, nameTh: district.name_th }),
    description: desc,
    openGraph: {
      title: `${primary} (${district.name_th})`,
      description: desc,
      type: 'article',
      ...(district.image && { images: [{ url: district.image.hero }] }),
    },
  };
}

export default async function DistrictPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const loc = locale as Locale;
  const t = await getTranslations();

  const d = getBangkokDistrict(slug);
  if (!d) notFound();

  const { primary: displayName, secondary: thaiName } = stationDisplayName(d, loc);
  const score = calculateWeightedScore(d.ratings, DEFAULT_WEIGHTS);
  const mapsUrl = getGoogleMapsAreaUrl(d.lat, d.lng);
  const stations = d.station_ids.map(getRailStation).filter((s) => s !== undefined);
  const nearby = d.nearby_station_ids.map(getRailStation).filter((s) => s !== undefined);
  const lines = d.line_ids.map(getRailLine).filter((l) => l !== undefined);
  const hubValues = Object.values(d.transit_minutes);
  const avgHub = Math.round(hubValues.reduce((a, b) => a + b, 0) / hubValues.length);
  const desc = d.description?.[loc];
  const mapDistricts = getBangkokMapDistricts();
  const neighbors = d.neighbors
    .map((n) => mapDistricts.find((m) => m.slug === n))
    .filter((n) => n !== undefined)
    .map((n) => ({ ...n, score: calculateWeightedScore(n.ratings!, DEFAULT_WEIGHTS) }))
    .sort((a, b) => b.score - a.score);
  const wikiOrder: ('en' | 'ja' | 'ru' | 'th')[] = [loc, 'th', ...(['en', 'ja', 'ru'] as const).filter((l) => l !== loc)];
  const wikiLinks = wikiOrder.filter((l) => d.wikipedia[l]).map((l) => ({ lang: l, url: d.wikipedia[l]! }));
  const f = d.facts;
  const nf = new Intl.NumberFormat(loc === 'en' ? 'en-US' : loc);

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'AdministrativeArea',
    name: `${displayName} District, Bangkok`,
    alternateName: [d.name_th, d.name_en].filter((n) => n !== displayName),
    inLanguage: locale,
    containedInPlace: { '@type': 'City', name: 'Bangkok' },
    geo: { '@type': 'GeoCoordinates', latitude: d.lat, longitude: d.lng },
    ...(d.wikipedia.en && { sameAs: d.wikipedia.en }),
  };

  return (
    <CityProvider city="bangkok">
      <div className="min-h-screen bg-gray-50">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

        {/* Header */}
        <DetailHeader homeHref={CITY.homePath} backLabel={t('bangkok.district.backToMap')} primary={displayName} secondary={thaiName}
        mapsUrl={mapsUrl} mapsTitle={t('station.mapsTooltip')} mapsLabel={t('station.mapsLink')} areaKey={slug}
        score={score} scoreColor={compositeToColor(score, CITY.defaultAnchors)} scoreTitle={t('bangkok.district.scoreTooltip')} />

        <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          <AirPanel city="bangkok" />
        <InstitutionFacts fact={getInstitutions('bangkok', 'district', d.slug)} />
          {/* Hero image (Wikimedia Commons, hot-linked with attribution) */}
          {d.image && (
            <figure className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={d.image.hero}
                alt={t('bangkok.district.imageAlt', { name: displayName })}
                className="w-full h-48 md:h-64 object-cover"
                loading="eager"
              />
              <figcaption className="px-3 py-1.5 text-[10px] text-gray-400 truncate">
                <a href={d.image.page} target="_blank" rel="noopener noreferrer" className="hover:text-gray-600">
                  {t('bangkok.district.imageCredit', { artist: d.image.artist, license: d.image.license })}
                </a>
              </figcaption>
            </figure>
          )}

          {/* Quick stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label={t('bangkok.district.rail')}
              sub={
                stations.length > 0
                  ? t('filter.lines', { count: lines.length })
                  : t('bangkok.district.nearbyCount', { count: nearby.length })
              }
            >
              <div className="text-xl font-bold">
                {stations.length > 0 ? t('filter.stations', { count: stations.length }) : t('bangkok.district.noRail')}
              </div>
            </StatCard>
            <StatCard label={t('bangkok.district.rentLabel')} sub={t('bangkok.district.rentSub')}>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">{formatRentShort('bangkok', d.rent.one_bed ?? 0)}</span>
                {d.rent.two_bed && (
                  <>
                    <span className="text-xs text-gray-400">–</span>
                    <span className="text-xl font-bold">{formatRentShort('bangkok', d.rent.two_bed)}</span>
                  </>
                )}
              </div>
              <RentNote rent={d.rent} />
            </StatCard>
            <StatCard
              label={t('station.avgToCenter')}
              value={`${avgHub} min`}
              sub={t('bangkok.district.toHubsSub')}
            />
            <StatCard
              label={t('bangkok.district.density')}
              value={f.density ? `${nf.format(f.density)}/km²` : '—'}
              sub={
                f.population
                  ? t('bangkok.district.populationSub', { population: nf.format(f.population), year: f.population_year ?? '' })
                  : t('station.noDataYet')
              }
            />
          </div>

          <HubStrip transitMinutes={d.transit_minutes} mapsUrl={mapsUrl} />

          {/* Rail stations */}
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-1">{t('bangkok.district.railTitle')}</h2>
            <p className="text-[11px] text-gray-500 mb-3">{t('bangkok.district.railCaption')}</p>
            {lines.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {lines.map((l) => (
                  <span
                    key={l.id}
                    className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-700"
                  >
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} aria-hidden />
                    {loc === 'ja' ? l.name_ja : loc === 'ru' ? l.name_ru : l.name_en}
                  </span>
                ))}
              </div>
            )}
            {stations.length > 0 ? (
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                {stations.map((s) => (
                  <li key={s.id} className="flex items-center gap-2 text-sm">
                    <span className="flex gap-0.5 shrink-0" aria-hidden>
                      {s.lines.map((lid) => (
                        <span key={lid} className="h-2 w-2 rounded-full" style={{ backgroundColor: getRailLine(lid)?.color }} />
                      ))}
                    </span>
                    <span className="font-medium">{s.name_en}</span>
                    <span className="text-gray-400 text-xs">{s.name_th}</span>
                    {s.district && s.district !== d.slug && (
                      <span className="text-[10px] text-gray-400 ml-auto">{t('bangkok.district.onBorder')}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-600">
                {t(nearby.length > 0 ? 'bangkok.district.noRailNearbyText' : 'bangkok.district.noRailText')}
              </p>
            )}
            {nearby.length > 0 && (
              <p className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-500">
                <span className="text-gray-400">{t('bangkok.district.nearbyStations')}: </span>
                {nearby.map((s) => s.name_en).join(' · ')}
              </p>
            )}
          </section>

          {/* Radar + Ratings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">{t('station.overview')}</h2>
              <RadarChartWrapper
                ratings={d.ratings}
                medians={CITY.medians}
                medianLabel={t('bangkok.district.radarMedianLabel')}
                areaLabel={t('bangkok.district.radarDistrictLabel')}
              />
            </section>
            <RatingsBreakdown kind="district" ratings={d.ratings} medians={CITY.medians} confidence={d.confidence} sources={d.sources} dataDate={d.data_date} rent={d.rent} />
          </div>

          {/* Description */}
          {desc ? (
            <section className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
              <h2 className="font-bold text-lg">{t('bangkok.district.aboutDistrict')}</h2>
              {(
                [
                  ['atmosphere', 'station.atmosphere'],
                  ['landmarks', 'station.landmarks'],
                  ['food', 'station.foodAndCafes'],
                  ['nightlife', 'station.barsAndNightlife'],
                ] as const
              ).map(([field, label]) =>
                desc[field] ? (
                  <div key={field}>
                    <h3 className="font-medium text-sm text-gray-500 mb-1">{t(label)}</h3>
                    <p className="text-gray-700">{desc[field]}</p>
                  </div>
                ) : null,
              )}
            </section>
          ) : (
            <section className="bg-white rounded-lg border border-gray-200 p-5 text-center text-gray-400">
              <p>{t('station.descriptionComingSoon')}</p>
            </section>
          )}

          {/* By the numbers */}
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-3">{t('bangkok.district.factsTitle')}</h2>
            <FactsGrid>
              {(
                [
                  ['factFood', f.food],
                  ['factNightlife', f.nightlife],
                  ['factConvenience', f.convenience],
                  ['factEssentials', f.essentials],
                  ['factMarkets', f.markets],
                  ['factSports', f.sports],
                  ['factCulture', f.culture],
                  ['factTemples', f.temples],
                  ['factPiers', f.piers],
                ] as const
              ).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs text-gray-500">{t(`bangkok.district.${key}`)}</dt>
                  <dd className="font-semibold tabular-nums">{nf.format(value)}</dd>
                </div>
              ))}
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factParks')}</dt>
                <dd className="font-semibold tabular-nums">
                  {nf.format(f.park_ha)} ha <span className="text-gray-400 font-normal">({f.park_share}%)</span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factArea')}</dt>
                <dd className="font-semibold tabular-nums">{nf.format(f.area_km2)} km²</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">{t('bangkok.district.factPopulation')}</dt>
                <dd className="font-semibold tabular-nums">{f.population ? nf.format(f.population) : '—'}</dd>
              </div>
            </FactsGrid>
            <p className="mt-3 pt-2 border-t border-gray-100 text-[10px] text-gray-400 leading-relaxed">
              {t('bangkok.district.factsSource')}
            </p>
          </section>

          {/* Neighbouring districts */}
          {neighbors.length > 0 && (
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-3">{t('bangkok.district.neighbors')}</h2>
              <div className="flex flex-wrap gap-2">
                {neighbors.map((n) => (
                  <Link
                    key={n.slug}
                    href={areaPath('bangkok', n.slug)}
                    className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 text-sm hover:bg-gray-50"
                    data-umami-event="neighbor-district"
                    data-umami-event-station={n.slug}
                  >
                    <span className="font-medium">{stationDisplayName(n, loc).primary}</span>
                    <span
                      className="font-bold tabular-nums text-xs"
                      style={{ color: compositeToColor(n.score, CITY.defaultAnchors) }}
                    >
                      {n.score.toFixed(1)}
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Wikipedia */}
          <WikiLinks links={wikiLinks} label={t('bangkok.district.readMore')} />

          <FeedbackWidget stationSlug={slug} stationName={displayName} source="station_page" />
        </main>
      </div>
    </CityProvider>
  );
}
