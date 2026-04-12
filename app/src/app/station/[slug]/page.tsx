import { getStation, getStations } from '@/lib/data';
import { RATING_LABELS, RATING_TOOLTIPS, StationRatings, getGoogleMapsAreaUrl } from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  categoryDeviationColor,
  CITY_MEDIANS,
  DEFAULT_COMPOSITE_ANCHORS,
  pigmentName,
} from '@/lib/scoring';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import Link from 'next/link';
import FeedbackWidget from '@/components/FeedbackWidget';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import RadarChartWrapper from '@/components/RadarChartWrapper';
import Tooltip from '@/components/Tooltip';
import RatingBar from '@/components/RatingBar';
import ConfidenceBadge, { ConfidenceIcon, CONFIDENCE_DOT_COLORS, SOURCE_LABELS } from '@/components/ConfidenceBadge';
import ImageGallery from '@/components/ImageGallery';
import NearbyPlaces from '@/components/NearbyPlaces';
import { NaturalEnvironment } from '@/components/NaturalEnvironment';
import StatCard from '@/components/StatCard';
import HubStrip from '@/components/HubStrip';
import stationImages from '@/data/station-images-all.json';
import stationPlaces from '@/data/station-places.json';

type ImageEntry = { url: string; alt: string; attribution?: string; photographer?: string; photographer_url?: string; source?: string; license?: string; lqip?: string };
const imageData = stationImages as Record<string, ImageEntry[]>;
import type { StationPlace } from '@/lib/types';
const placesData = stationPlaces as Record<string, StationPlace[]>;

export function generateStaticParams() {
  return getStations()
    .filter((s) => s.ratings !== null)
    .map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const station = getStation(slug);
  if (!station) return { title: 'Station Not Found' };
  const desc = station.description?.atmosphere
    ? station.description.atmosphere.slice(0, 155)
    : `Neighborhood guide for ${station.name_en} station area in Tokyo.`;
  return {
    title: `${station.name_en} (${station.name_jp}) - Tokyo Neighborhood Explorer`,
    description: `${station.name_en} station area: ratings, rent prices, transit times. ${desc}`,
    openGraph: {
      title: `${station.name_en} - Tokyo Neighborhood Explorer`,
      description: desc,
      type: 'article',
    },
  };
}

export default async function StationPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const station = getStation(slug);
  if (!station) notFound();

  const score = station.ratings
    ? calculateWeightedScore(station.ratings, DEFAULT_WEIGHTS)
    : null;

  const mapsUrl = getGoogleMapsAreaUrl(station.lat, station.lng);
  const images = imageData[slug] || [];
  const places = placesData[slug] || [];

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: `${station.name_en} Station Area`,
    alternateName: station.name_jp,
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
            &larr; Map
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-bold text-lg">{station.name_en}</span>
          <span className="text-gray-400">{station.name_jp}</span>
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
            Maps
          </a>
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
          {/* Transit card — lines + express placeholder */}
          <StatCard label="Transit" sub="train lines">
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold">{station.line_count}</span>
              <span className="text-sm text-gray-500">{station.line_count === 1 ? 'line' : 'lines'}</span>
            </div>
          </StatCard>

          {/* Merged rent card */}
          {station.rent_avg?.['1k_1ldk'] ? (
            <StatCard label="Rent">
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
                {station.rent_avg?.['2ldk'] ? '1K–1LDK → 2LDK / mo' : '1K–1LDK / mo'}
              </div>
            </StatCard>
          ) : (
            <StatCard label="Rent" value="—" sub="no data yet" />
          )}

          {/* Avg to Center */}
          {station.transit_minutes ? (
            <StatCard
              label="Avg to Center"
              value={`${Math.round(Object.values(station.transit_minutes).reduce((a, b) => a + b, 0) / Object.values(station.transit_minutes).length)} min`}
              sub="to 5 major hubs"
            />
          ) : (
            <StatCard label="Avg to Center" value="—" sub="no data yet" />
          )}

          {/* Last Train — placeholder for Wave 4 */}
          <StatCard label="Last Train" value="—" sub="coming soon" />
        </div>

        {/* Hub breakdown strip */}
        {station.transit_minutes && (
          <HubStrip transitMinutes={station.transit_minutes} mapsUrl={mapsUrl} />
        )}

        {/* Radar chart + Ratings breakdown */}
        {station.ratings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">Overview</h2>
              <RadarChartWrapper ratings={station.ratings} />
            </section>
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">Ratings</h2>
              <p className="text-[11px] text-gray-500 leading-relaxed mb-3 max-w-xl">
                Bar fill compares this station to the Tokyo median for that row
                — hover the bar for pigment detail, the category name for what
                it measures.
                {station.confidence ? (
                  <>
                    {' '}
                    Where a colored dot appears, it shows how firm that score is
                    (hover for sources); hues match the key below.
                  </>
                ) : null}
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

                  // Microcopy: three lines for the bar tooltip.
                  const devPhrase = dev === 0
                    ? `Tokyo norm is ${median} — this station is exactly average.`
                    : `Tokyo norm is ${median} — this station is ${Math.abs(dev)} ${dev > 0 ? 'above' : 'below'} norm.`;
                  // Unsigned number + directional word, so the phrase doesn't
                  // double-negate as "−3 below norm".
                  const labelDevSummary = dev === 0
                    ? 'exactly average'
                    : `${Math.abs(dev)} ${dev > 0 ? 'above' : 'below'} norm`;

                  return (
                    <div key={key} className="flex items-center gap-3">
                      {/* Fixed-width column: rows without confidence keep bars aligned */}
                      <div className="w-6 shrink-0 flex justify-center items-center">
                        {conf ? (
                          <ConfidenceBadge level={conf} sources={srcs} />
                        ) : null}
                      </div>

                      {/* Category help: hover label text only (no ?); separate from dot + bar tooltips */}
                      <Tooltip
                        showHelpIcon={false}
                        content={
                          <>
                            <span>{RATING_TOOLTIPS[key]}</span>
                            {srcs && srcs.length > 0 && (
                              <span className="block mt-1.5 text-gray-400">
                                Sources: {srcs.map(s => SOURCE_LABELS[s] || s).join(', ')}
                              </span>
                            )}
                            <span className="block mt-1.5 pt-1.5 border-t border-gray-600/40 tabular-nums">
                              Tokyo median: {median}
                              <br />
                              This station: {val} ({labelDevSummary})
                            </span>
                            {station.data_date && (
                              <span className="block mt-1 text-gray-500 text-[10px]">
                                Data: {station.data_date}
                              </span>
                            )}
                          </>
                        }
                      >
                        <span className="text-sm w-32 text-gray-600 cursor-help">
                          {RATING_LABELS[key]}
                        </span>
                      </Tooltip>

                      <Tooltip
                        wrapper="div"
                        showHelpIcon={false}
                        className="flex-1"
                        content={
                          <>
                            <span className="font-semibold">
                              {RATING_LABELS[key]}: {val} / 10
                            </span>
                            <span className="block mt-1">{devPhrase}</span>
                            <span className="block mt-1 italic text-gray-400">
                              Painted in {pigment.jp} {pigment.en} ({pigment.tone}).
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
                      ['Measured', 'strong'] as const,
                      ['Partial', 'moderate'] as const,
                      ['Estimate', 'estimate'] as const,
                      ['Curated', 'editorial'] as const,
                    ] as const
                  ).map(([label, level]) => (
                    <span
                      key={label}
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5"
                    >
                      <ConfidenceIcon level={level} size={10} />
                      {label}
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
        <FeedbackWidget stationSlug={slug} stationName={station.name_en} source="station_page" />

        {/* Image gallery */}
        {images.length > 0 && (
          <ImageGallery images={images} stationName={station.name_en} />
        )}


        {/* Nearby Places */}
        <NearbyPlaces
          places={places}
          lat={station.lat}
          lng={station.lng}
          stationName={station.name_en}
        />

        {/* Description */}
        {station.description ? (
          <section className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="font-bold text-lg">About this area</h2>
            {station.description.atmosphere && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  Atmosphere
                </h3>
                <p className="text-gray-700">{station.description.atmosphere}</p>
              </div>
            )}
            {station.description.landmarks && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  Landmarks & Walks
                </h3>
                <p className="text-gray-700">{station.description.landmarks}</p>
              </div>
            )}
            {station.description.food && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  Food & Cafes
                </h3>
                <p className="text-gray-700">{station.description.food}</p>
              </div>
            )}
            {station.description.nightlife && (
              <div>
                <h3 className="font-medium text-sm text-gray-500 mb-1">
                  Bars & Nightlife
                </h3>
                <p className="text-gray-700">
                  {station.description.nightlife}
                </p>
              </div>
            )}
          </section>
        ) : (
          <section className="bg-white rounded-lg border border-gray-200 p-5 text-center text-gray-400">
            <p>Detailed description coming soon.</p>
            <p className="text-sm mt-1">
              AI research for this station is in progress.
            </p>
          </section>
        )}

      </main>
    </div>
  );
}

