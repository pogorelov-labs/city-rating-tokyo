import RatingsBreakdown from '@/components/RatingsBreakdown';
import { InstitutionFacts } from '@/components/InstitutionFacts';
import { getInstitutions } from '@/lib/institutions';
import { hasLocale } from 'next-intl';
import AirPanel from '@/components/AirPanel';
import { QuietnessFacts } from '@/components/QuietnessFacts';
import { getQuietness } from '@/lib/quietness';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { getStation, getStations } from '@/lib/data';
import { getGoogleMapsAreaUrl } from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  CITY_MEDIANS,
  DEFAULT_COMPOSITE_ANCHORS,
  isStationLevelRent,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import FeedbackWidget from '@/components/FeedbackWidget';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import Tooltip from '@/components/Tooltip';
import ImageGallery from '@/components/ImageGallery';
import NearbyPlaces from '@/components/NearbyPlaces';
import { NaturalEnvironment } from '@/components/NaturalEnvironment';
import TransportLines from '@/components/TransportLines';
import LiveCameras from '@/components/LiveCameras';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import stationImages from '@/data/station-images-all.json';
import stationPlaces from '@/data/station-places.json';
import { routing, Locale } from '@/i18n/routing';
import { stationDisplayName } from '@/lib/station-name';
import { isEditorialStation } from '@/lib/editorial';
import DetailHeader from '@/components/DetailHeader';

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
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: 'station' });
  const station = getStation(slug);
  if (!station) {
    const errors = await getTranslations({ locale, namespace: 'error' });
    return { title: errors('stationNotFound') };
  }
  const { primary, secondary } = stationDisplayName(station, locale as Locale);
  const atmosphere = station.description?.[locale as Locale]?.atmosphere;
  const desc = atmosphere
    ? atmosphere.slice(0, 155)
    : t('metaDescriptionFallback', { name: primary });
  return {
    title: t('metaTitle', { name: primary, secondary }),
    description: t('metaDescription', { name: primary, description: desc }),
    openGraph: {
      title: `${primary} (${secondary})`,
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
  if (!hasLocale(routing.locales, locale)) notFound();
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
  const isEditorial = isEditorialStation(station);

  // The editorial score is a computed weighted value, not an aggregate of
  // human ratings, so we intentionally do NOT emit schema.org AggregateRating
  // (which would trigger Search Console warnings for missing ratingCount and
  // misrepresent the score's semantics).
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
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <DetailHeader homeHref="/" backLabel={t('nav.backToMap')} primary={displayName} secondary={secondaryName}
        mapsUrl={mapsUrl} mapsTitle={t('station.mapsTooltip')} mapsLabel={t('station.mapsLink')} areaKey={slug}
        score={score} scoreColor={score === null ? '' : compositeToColor(score, DEFAULT_COMPOSITE_ANCHORS)} tokyo
        badge={isEditorial ? (
            <span
              className="inline-flex items-center gap-1 text-[10px] font-medium text-white px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: '#8B6DB0' }}
              title={t('station.editorialBadge.tooltip')}
            >
              <svg className="w-2 h-2" viewBox="0 0 10 10" aria-hidden>
                <rect x="2" y="2" width="6" height="6" fill="currentColor" transform="rotate(45 5 5)" />
              </svg>
              {t('station.editorialBadge.label')}
            </span>
          ) : null} />

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
              {/* Area-level figures must not read as this station's rent (CRTKY-43). */}
              {!isStationLevelRent(station.rent_avg) && (
                <div className="text-xs text-gray-500">
                  {station.rent_avg.source === 'estat' ? t('station.rentMunicipalAvg') : t('station.rentEstimate')}
                </div>
              )}
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

          {station.last_train?.weekday ? (
            <Tooltip
              wrapper="div"
              showHelpIcon={false}
              content={
                <div className="text-xs space-y-0.5">
                  <div>
                    <span className="text-gray-300">{t('station.weekdayFull')}: </span>
                    <span className="font-medium">{station.last_train.weekday}</span>
                  </div>
                  {station.last_train.holiday && (
                    <div>
                      <span className="text-gray-300">{t('station.holidayFull')}: </span>
                      <span className="font-medium">{station.last_train.holiday}</span>
                    </div>
                  )}
                  <div className="text-gray-400 pt-1 border-t border-gray-700 mt-1 leading-snug">
                    {t('station.lastTrainCaveat')}
                  </div>
                </div>
              }
            >
              <StatCard
                label={t('station.lastTrain')}
                value={station.last_train.weekday}
                sub={t('station.weekday')}
              />
            </Tooltip>
          ) : (
            <StatCard label={t('station.lastTrain')} value="—" sub={t('station.noDataYet')} />
          )}
        </div>

        {/* Hub breakdown strip */}
        {station.transit_minutes && (
          <HubStrip transitMinutes={station.transit_minutes} mapsUrl={mapsUrl} />
        )}

        {/* Transport lines + ward/city */}
        <TransportLines
          lines={station.lines}
          ward={station.ward ?? null}
          locale={loc}
        />

        {/* Radar chart + Ratings breakdown */}
        {station.ratings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">{t('station.overview')}</h2>
              <RadarChartWrapper ratings={station.ratings} />
            </section>
            <RatingsBreakdown kind="tokyo" ratings={station.ratings} medians={CITY_MEDIANS} confidence={station.confidence} sources={station.sources} dataDate={station.data_date} />
          </div>
        )}

        <AirPanel city="tokyo" />
        <InstitutionFacts fact={getInstitutions('tokyo', 'station', station.slug)} />
        <QuietnessFacts fact={getQuietness('tokyo', station.slug)} />

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

        {/* Live camera feeds (if any match within 300m) */}
        {station.livecams && station.livecams.length > 0 && (
          <LiveCameras livecams={station.livecams} locale={loc} />
        )}

        {/* Nearby Places */}
        <NearbyPlaces
          places={places}
          lat={station.lat}
          lng={station.lng}
          stationName={displayName}
        />

        {/* Description — multilingual via CRTKY-109 pipeline (EN/JA/RU × 4 fields per station) */}
        {(() => {
          const desc = station.description?.[loc];
          if (!desc) {
            return (
              <section className="bg-white rounded-lg border border-gray-200 p-5 text-center text-gray-400">
                <p>{t('station.descriptionComingSoon')}</p>
                <p className="text-sm mt-1">
                  {t('station.descriptionInProgress')}
                </p>
              </section>
            );
          }
          return (
            <section className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
              <h2 className="font-bold text-lg">{t('station.aboutArea')}</h2>
              {desc.atmosphere && (
                <div>
                  <h3 className="font-medium text-sm text-gray-500 mb-1">
                    {t('station.atmosphere')}
                  </h3>
                  <p className="text-gray-700">{desc.atmosphere}</p>
                </div>
              )}
              {desc.landmarks && (
                <div>
                  <h3 className="font-medium text-sm text-gray-500 mb-1">
                    {t('station.landmarks')}
                  </h3>
                  <p className="text-gray-700">{desc.landmarks}</p>
                </div>
              )}
              {desc.food && (
                <div>
                  <h3 className="font-medium text-sm text-gray-500 mb-1">
                    {t('station.foodAndCafes')}
                  </h3>
                  <p className="text-gray-700">{desc.food}</p>
                </div>
              )}
              {desc.nightlife && (
                <div>
                  <h3 className="font-medium text-sm text-gray-500 mb-1">
                    {t('station.barsAndNightlife')}
                  </h3>
                  <p className="text-gray-700">{desc.nightlife}</p>
                </div>
              )}
            </section>
          );
        })()}

      </main>
    </div>
  );
}
