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
  categoryDeviationColor,
  compositeToColor,
  pigmentName,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS, RATING_LABELS, getGoogleMapsAreaUrl, type StationRatings } from '@/lib/types';
import { stationDisplayName } from '@/lib/station-name';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import Tooltip from '@/components/Tooltip';
import RatingBar from '@/components/RatingBar';
import ConfidenceBadge, { ConfidenceIcon } from '@/components/ConfidenceBadge';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import FeedbackWidget from '@/components/FeedbackWidget';
import LocaleSwitcher from '@/components/LocaleSwitcher';

const CITY = CITIES.bangkok;
const RATING_KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];

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
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-1">
            <Link
              href={CITY.homePath}
              className="text-sm text-blue-600 hover:underline flex items-center gap-1"
              data-umami-event="back-to-map"
            >
              &larr; {t('bangkok.district.backToMap')}
            </Link>
            <span className="text-gray-300">|</span>
            <h1 className="font-bold text-lg">{displayName}</h1>
            <span className="text-gray-400">{thaiName}</span>
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              title={t('station.mapsTooltip')}
              data-umami-event="open-google-maps"
              data-umami-event-station={slug}
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              {t('station.mapsLink')}
            </a>
            <LocaleSwitcher />
            <span
              className="ml-auto text-2xl font-bold"
              style={{ color: compositeToColor(score, CITY.defaultAnchors) }}
              title={t('bangkok.district.scoreTooltip')}
            >
              {score.toFixed(1)}
            </span>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
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
                medianLabelKey="bangkok.district.radarMedianLabel"
                areaLabelKey="bangkok.district.radarDistrictLabel"
              />
            </section>
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <div className="flex items-baseline justify-between gap-2 mb-2">
                <h2 className="font-bold text-lg">{t('station.ratingsTitle')}</h2>
                <span className="text-xs text-gray-500 shrink-0">
                  {t('station.dataFreshness.label', { date: d.data_date })}
                </span>
              </div>
              <p className="text-[11px] text-gray-500 leading-relaxed mb-3 max-w-xl">
                {t('bangkok.district.ratingsCaption')}
              </p>
              <div className="space-y-3">
                {RATING_KEYS.map((key) => {
                  const val = d.ratings[key];
                  const conf = d.confidence[key];
                  const srcs = d.sources[key];
                  const median = CITY.medians[key];
                  const dev = val - median;
                  const barColor = categoryDeviationColor(val, median);
                  const pigment = pigmentName(dev);
                  const devPhrase =
                    dev === 0
                      ? t('bangkok.district.barTooltipDevExact', { median })
                      : t('bangkok.district.barTooltipDev', {
                          median,
                          dev: Math.abs(dev),
                          direction: dev > 0 ? t('station.devAbove') : t('station.devBelow'),
                        });
                  const labelDevSummary =
                    dev === 0
                      ? t('station.labelDevExact')
                      : dev > 0
                        ? t('station.labelDevAbove', { dev: Math.abs(dev) })
                        : t('station.labelDevBelow', { dev: Math.abs(dev) });
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <div className="w-6 shrink-0 flex justify-center items-center">
                        {conf && (
                          <ConfidenceBadge
                            level={conf}
                            sources={srcs}
                            descriptionKey={conf === 'editorial' ? 'confidence.editorial.descriptionResearch' : undefined}
                          />
                        )}
                      </div>
                      <Tooltip
                        showHelpIcon={false}
                        content={
                          <>
                            <span>{t(key === 'rent' ? 'bangkok.district.rentTooltip' : `ratingTooltips.${key}`)}</span>
                            {srcs && srcs.length > 0 && (
                              <span className="block mt-1.5 text-gray-400">
                                Sources: {srcs.map((s) => (t.has(`sources.${s}`) ? t(`sources.${s}`) : s)).join(', ')}
                              </span>
                            )}
                            <span className="block mt-1.5 pt-1.5 border-t border-gray-600/40 tabular-nums">
                              {t('bangkok.district.bangkokMedian', { value: median })}
                              <br />
                              {t('bangkok.district.thisDistrict', { value: val })} ({labelDevSummary})
                            </span>
                          </>
                        }
                      >
                        <span className="text-sm w-32 text-gray-600 cursor-help">{t(`ratings.${key}`)}</span>
                      </Tooltip>
                      <Tooltip
                        wrapper="div"
                        showHelpIcon={false}
                        className="flex-1"
                        content={
                          <>
                            <span className="font-semibold">
                              {t('station.barTooltipScore', { label: t(`ratings.${key}`), value: val })}
                            </span>
                            <span className="block mt-1">{devPhrase}</span>
                            <span className="block mt-1 italic text-gray-400">
                              {t('station.barTooltipPigment', { jp: pigment.jp, en: pigment.en, tone: pigment.tone })}
                            </span>
                          </>
                        }
                      >
                        <RatingBar value={val} median={median} fillColor={barColor} />
                      </Tooltip>
                      <span className="text-sm font-bold tabular-nums w-6 text-right">{val}</span>
                      <span
                        className="w-3 text-center text-sm font-medium leading-none tabular-nums"
                        style={{ color: barColor, opacity: 0.65 }}
                        aria-hidden
                      >
                        {dev > 0 ? '↑' : dev < 0 ? '↓' : '−'}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2 text-[10px] text-gray-600">
                {(['strong', 'moderate', 'estimate', 'editorial'] as const).map((level) => (
                  <span
                    key={level}
                    className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5"
                  >
                    <ConfidenceIcon level={level} size={10} />
                    {t(`confidence.${level}.label`)}
                  </span>
                ))}
              </div>
              <details className="group mt-3">
                <summary className="flex items-center gap-1.5 cursor-pointer text-[11px] text-gray-600 hover:text-gray-800 select-none marker:hidden list-none">
                  <svg
                    className="w-3 h-3 text-gray-400 transition-transform group-open:rotate-90 shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                  {t('station.howRatingsWork.title')}
                </summary>
                <div className="mt-2 pl-5 text-[11px] text-gray-600 leading-relaxed space-y-1.5">
                  <p>{t('bangkok.district.howRatingsWork')}</p>
                  <p>{t('bangkok.district.relativeNote')}</p>
                  <Link href="/methodology#bangkok" className="inline-block text-blue-600 hover:underline font-medium">
                    {t('station.howRatingsWork.learnMore')}
                  </Link>
                </div>
              </details>
            </section>
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
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
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
            </dl>
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
          {wikiLinks.length > 0 && (
            <p className="text-xs text-gray-500">
              {t('bangkok.district.readMore')}{' '}
              {wikiLinks.map((w, i) => (
                <span key={w.lang}>
                  {i > 0 && ' · '}
                  <a href={w.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    Wikipedia ({w.lang.toUpperCase()})
                  </a>
                </span>
              ))}
            </p>
          )}

          <FeedbackWidget stationSlug={slug} stationName={displayName} source="station_page" />
        </main>
      </div>
    </CityProvider>
  );
}
