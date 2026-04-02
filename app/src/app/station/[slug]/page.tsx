import { getStation, getStations } from '@/lib/data';
import { RATING_LABELS, HUB_LABELS, StationRatings } from '@/lib/types';
import { calculateWeightedScore, scoreToColor } from '@/lib/scoring';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import StationRadarChart from '@/components/RadarChart';

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
          >
            &larr; Map
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-bold text-lg">{station.name_en}</span>
          <span className="text-gray-400">{station.name_jp}</span>
          {score !== null && (
            <span
              className="ml-auto text-2xl font-bold"
              style={{ color: scoreToColor(score) }}
            >
              {score.toFixed(1)}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Quick stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Lines"
            value={`${station.line_count}`}
            sub="train lines"
          />
          {station.rent_avg?.['1k_1ldk'] && (
            <StatCard
              label="Rent (1K-1LDK)"
              value={`\u00a5${(station.rent_avg['1k_1ldk'] / 1000).toFixed(0)}k`}
              sub="per month"
            />
          )}
          {station.rent_avg?.['2ldk'] && (
            <StatCard
              label="Rent (2LDK)"
              value={`\u00a5${(station.rent_avg['2ldk']! / 1000).toFixed(0)}k`}
              sub="per month"
            />
          )}
          {station.transit_minutes && (
            <StatCard
              label="To Shinjuku"
              value={`${station.transit_minutes.shinjuku} min`}
              sub="by train"
            />
          )}
        </div>

        {/* Radar chart + Ratings breakdown */}
        {station.ratings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-2">Overview</h2>
              <StationRadarChart ratings={station.ratings} />
            </section>
            <section className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="font-bold text-lg mb-4">Ratings</h2>
              <div className="space-y-3">
              {(
                Object.entries(station.ratings) as [
                  keyof StationRatings,
                  number,
                ][]
              ).map(([key, val]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-sm w-36 text-gray-600">
                    {RATING_LABELS[key]}
                  </span>
                  <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${val * 10}%`,
                        backgroundColor: scoreToColor(val),
                      }}
                    />
                  </div>
                  <span className="text-sm font-bold tabular-nums w-8 text-right">
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </section>
          </div>
        )}

        {/* Transit times */}
        {station.transit_minutes && (
          <section className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-bold text-lg mb-4">Transit Times</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {(
                Object.entries(station.transit_minutes) as [
                  keyof typeof station.transit_minutes,
                  number,
                ][]
              ).map(([hub, minutes]) => (
                <div
                  key={hub}
                  className="text-center p-3 bg-gray-50 rounded-lg"
                >
                  <div className="text-2xl font-bold">{minutes}</div>
                  <div className="text-xs text-gray-500">min</div>
                  <div className="text-sm font-medium mt-1">
                    {HUB_LABELS[hub]}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Description placeholder */}
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

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      <div className="text-xs text-gray-400">{sub}</div>
    </div>
  );
}
