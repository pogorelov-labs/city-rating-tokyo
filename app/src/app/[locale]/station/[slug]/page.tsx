import { getTranslations, setRequestLocale } from 'next-intl/server';
import { getStation, getStations } from '@/lib/data';
import { RATING_LABELS, StationRatings, getGoogleMapsAreaUrl } from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  categoryDeviationColor,
  CITY_MEDIANS,
  DEFAULT_COMPOSITE_ANCHORS,
  pigmentName,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import { Link } from '@/i18n/navigation';
import FeedbackWidget from '@/components/FeedbackWidget';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import Tooltip from '@/components/Tooltip';
import RatingBar from '@/components/RatingBar';
import ConfidenceBadge, { ConfidenceIcon } from '@/components/ConfidenceBadge';
import ImageGallery from '@/components/ImageGallery';
import NearbyPlaces from '@/components/NearbyPlaces';
import { NaturalEnvironment } from '@/components/NaturalEnvironment';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import stationImages from '@/data/station-images-all.json';
import stationPlaces from '@/data/station-places.json';
import { routing, Locale } from '@/i18n/routing';
import { stationDisplayName } from '@/lib/station-name';
import LocaleSwitcher from '@/components/LocaleSwitcher';

type ImageEntry = { url: string; alt: string; attribution?: string; photographer?: string; photographer_url?: string; source?: string; license?: string; lqip?: string };
const imageData = stationImages as Record<string, ImageEntry[]>;
import type { StationPlace } from '@/lib/types';
const placesData = stationPlaces as Record<string, StationPlace[]>;

export function generateStaticParams() {
  const slugs = getStations()
    .filter((s) => s.ratings !== null)
    .map((s) => s.slug);
  return routing.locales.flatMap((locale) =>
    slugs.map((slug) => ({ locale, slug }))
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const t = await getTranslations({ locale, namespace: 'station' });
  const station = getStation(slug);
  if (!station) return { title: 'Station Not Found' };
  const { primary } = stationDisplayName(station, locale as Locale);
  const desc = station.description?.atmosphere && locale === 'ru'
    ? station.description.atmosphere.slice(0, 155)
    : t('metaDescriptionFallback', { name: primary });
  return {
    title: t('metaTitle', { name: primary, nameJp: station.name_jp }),
    description: t('metaDescription', { name: primary, description: desc }),
    openGraph: {
      title: `${primary} (${station.name_jp})`,
      description: desc,
      type: 'article',
    },
  };
}

export default async function StationPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const t = await getTranslations();
  const loc = locale as Locale;

  const station = getStation(slug);
  if (!station) notFound();

  const { primary: displayName, secondary: secondaryName } = stationDisplayName(station, loc);
  const score = station.ratings
    ? calculateWeightedScore(station.ratings, DEFAULT_WEIGHTS)
    : null;

  const mapsUrl = getGoogleMapsAreaUrl(station.lat, station.lng);
  const images = imageData[slug] || [];
  const places = placesData[slug] || [];

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: `${displayName} Station Area`,
    alternateName: secondaryName,
    inLanguage: locale,
    geo: {
      '@type': 'GeoCoordinates',
      latitude: station.lat,
      longitude: station.lng,
    },
    ...(score !== null && {
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: score,
        bestRating: 10,
        worstRating: 1,
      },
    }),
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
            data-umami-event="back-to-map"
          >
            &larr; {t('nav.backToMap')}
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-bold text-lg">{displayName}</span>
          <span className="text-gray-400">{secondaryName}</span>
          <a
            href={mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
            title="Open in Google Maps"
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
          {score !== null && (
            <span
              className="ml-auto text-2xl font-bold"
              style={{ color: compositeToColor(score, DEFAULT_COMPOSITE_ANCHORS) }}
            >
              {score.toFixed(1)}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Quick stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label={t('station.transit')} sub={t('station.trainLines')}>
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold">{station.line_count}</span>
              <span className="text-sm text-gray-500">
                {station.line_count === 1 ? t('station.linesSingular') : t('station.linesPlural')}
              </span>
            </div>
          </StatCard>

          {station.rent_avg?.['1k_1ldk'] ? (
            <StatCard label={t('station.rentLabel')}>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">¥{(station.rent_avg['1k_1ldk'] / 1000).toFixed(0)}k</span>
                {station.rent_avg?.['2ldk'] && (
                  <>
                    <span className="text-xs text-gray-400">–</span>
                    <span className="text-xl font-bold">{(station.rent_avg['2ldk'] / 1000).toFixed(0)}k</span>
                  </>
                )}
              </div>
              <div className="text-xs text-gray-400">
                {station.rent_avg?.['2ldk'] ? t('station.rentRange') : t('station.rentSingle')}
              </div>
            </StatCard>
          ) : (
            <StatCard label={t('station.rentLabel')} value="—" sub={t('station.noDataYet')} />
          )}

          {station.transit_minutes ? (
            <StatCard
              label={t('station.avgToCenter')}
              value={`${Math.round(Object.values(station.transit_minutes).reduce((a, b) => a + b, 0) / Object.values(station.transit_minutes).length)} min`}
              sub={t('station.toMajorHubs')}
            />
          ) : (
            <StatCard label={t('station.avgToCenter')} value="—" sub={t('station.noDataYet')} />
          )}

          <StatCard label={t('station.lastTrain')} value="—" sub={t('station.comingSoon')} />
        </div>

        {/* Hub breakdown strip */}
        {station.transit_minutes && (
          <HubStrip transitMinutes={station.transit_minutes} mapsUrl={mapsUrl} />
        )}

        {/* Radar chart + Ratings breakdown */}
        {station.ratings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">{t('station.overview')}</h2>
              <RadarChartWrapper ratings={station.ratings} />
            </section>
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">{t('station.ratingsTitle')}</h2>
              <p className="text-[11px] text-gray-500 leading-relaxed mb-3 max-w-xl">
                {t('station.ratingsCaption')}
                {station.confidence ? t('station.ratingsCaptionWithConfidence') : null}
              </p>
              <div className="space-y-3">
                {(
                  Object.entries(station.ratings) as [
                    keyof StationRatings,
                    number,
                  ][]
                ).map(([key, val]) => {
                  const conf = station.confidence?.[key];
                  const srcs = station.sources?.[key];
                  const median = CITY_MEDIANS[key];
                  const dev = val - median;
                  const barColor = categoryDeviationColor(val, median);
                  const pigment = pigmentName(dev);

                  const devPhrase = dev === 0
                    ? t('station.barTooltipDevExact', { median })
                    : t('station.barTooltipDev', { median, dev: Math.abs(dev), direction: dev > 0 ? t('station.devAbove') : t('station.devBelow') });

                  const labelDevSummary = dev === 0
                    ? t('station.labelDevExact')
                    : dev > 0
                      ? t('station.labelDevAbove', { dev: Math.abs(dev) })
                      : t('station.labelDevBelow', { dev: Math.abs(dev) });

                  return (
                    <div key={key} className="flex items-center gap-3">
                      <div className="w-6 shrink-0 flex justify-center items-center">
                        {conf ? (
                          <ConfidenceBadge level={conf} sources={srcs} />
                        ) : null}
                      </div>

                      <Tooltip
                        showHelpIcon={false}
                        content={
                          <>
                            <span>{t(`ratingTooltips.${key}`)}</span>
                            {srcs && srcs.length > 0 && (
                              <span className="block mt-1.5 text-gray-400">
                                Sources: {srcs.map(s => t.has(`sources.${s}`) ? t(`sources.${s}`) : s).join(', ')}
                              </span>
                            )}
                            <span className="block mt-1.5 pt-1.5 border-t border-gray-600/40 tabular-nums">
                              {t('station.tokyoMedian', { value: median })}
                              <br />
                              {t('station.thisStation', { value: val })} ({labelDevSummary})
                            </span>
                            {station.data_date && (
                              <span className="block mt-1 text-gray-500 text-[10px]">
                                {t('station.dataDate', { date: station.data_date })}
                              </span>
                            )}
                          </>
                        }
                      >
                        <span className="text-sm w-32 text-gray-600 cursor-help">
                          {t(`ratings.${key}`)}
                        </span>
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

                      <span className="text-sm font-bold tabular-nums w-6 text-right">
                        {val}
                      </span>

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
              {station.confidence && (
                <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2 text-[10px] text-gray-600">
                  {(
                    [
                      ['strong', 'strong'] as const,
                      ['moderate', 'moderate'] as const,
                      ['estimate', 'estimate'] as const,
                      ['editorial', 'editorial'] as const,
                    ] as const
                  ).map(([levelKey, level]) => (
                    <span
                      key={levelKey}
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5"
                    >
                      <ConfidenceIcon level={level} size={10} />
                      {t(`confidence.${levelKey}.label`)}
                    </span>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {/* Natural Environment (elevation + seismic risk) */}
        {station.environment && (
          <NaturalEnvironment environment={station.environment} />
        )}

        {/* Feedback */}
        <FeedbackWidget stationSlug={slug} stationName={displayName} source="station_page" />

        {/* Image gallery */}
        {images.length > 0 && (
          <ImageGallery images={images} stationName={displayName} />
        )}

        {/* Nearby Places */}
        <NearbyPlaces
          places={places}
          lat={station.lat}
          lng={station.lng}
          stationName={displayName}
        />

        {/* Description — currently Russian-only; gate to RU locale until CRTKY-109 provides multilingual */}
        {station.description && loc === 'ru' ? (
          <section className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="font-bold text-lg">{t('station.aboutArea')}</h2>
            {station.description.atmosphere && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  {t('station.atmosphere')}
                </h3>
                <p className="text-gray-700">{station.description.atmosphere}</p>
              </div>
            )}
            {station.description.landmarks && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  {t('station.landmarks')}
                </h3>
                <p className="text-gray-700">{station.description.landmarks}</p>
              </div>
            )}
            {station.description.food && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  {t('station.foodAndCafes')}
                </h3>
                <p className="text-gray-700">{station.description.food}</p>
              </div>
            )}
            {station.description.nightlife && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  {t('station.barsAndNightlife')}
                </h3>
                <p className="text-gray-700">
                  {station.description.nightlife}
                </p>
              </div>
            )}
          </section>
        ) : (
          <section className="bg-white rounded-lg border border-gray-200 p-5 text-center text-gray-400">
            <p>{t('station.descriptionComingSoon')}</p>
            <p className="text-sm mt-1">
              {t('station.descriptionInProgress')}
            </p>
          </section>
        )}

      </main>
    </div>
  );
}
