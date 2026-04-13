import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Methodology - Tokyo Neighborhood Explorer',
  description:
    'How we rate 1,493 Tokyo-area train stations: data sources, rating formulas, confidence levels, and known limitations.',
};

const DATA_SOURCES = [
  {
    category: 'Food & Dining',
    sources: ['HotPepper Gourmet API (restaurant/izakaya/bar counts)', 'OpenStreetMap (restaurant/cafe/fast food POIs)'],
    coverage: '100%',
    confidence: 'strong',
    note: 'Two independent sources with r=0.855 correlation.',
  },
  {
    category: 'Nightlife',
    sources: [
      'HotPepper (late-night shops via midnight=1, izakaya, bars)',
      'OpenStreetMap (bars, pubs, nightclubs, karaoke, hostels)',
    ],
    coverage: '100%',
    confidence: 'strong',
    note: 'Weighted composite of 7 signals including late-night establishments.',
  },
  {
    category: 'Transport',
    sources: ['Station line count (ekidata)', 'MLIT S12 daily passenger counts'],
    coverage: '100%',
    confidence: 'strong',
    note: '94% of stations have official MLIT passenger data.',
  },
  {
    category: 'Rent / Affordability',
    sources: ['Suumo station-level scrape', 'Ward-average fallback (Nominatim)', 'Log-linear distance regression'],
    coverage: '100%',
    confidence: 'mixed',
    note: '18% station-level, 48% ward average, 34% regression estimate. Inverted: cheaper = higher rating.',
  },
  {
    category: 'Safety',
    sources: [
      'Keishicho ArcGIS (Tokyo neighborhood polygons)',
      'Prefectural police ward-level data',
    ],
    coverage: '100%',
    confidence: 'mixed',
    note: 'Tokyo stations use neighborhood-level crime polygons. Other prefectures use ward-level data.',
  },
  {
    category: 'Green & Parks',
    sources: ['OpenStreetMap (parks, gardens, nature reserves, forests)'],
    coverage: '94%',
    confidence: 'moderate',
    note: 'Currently uses park count. Area-based scoring in progress.',
  },
  {
    category: 'Gym & Sports',
    sources: ['OpenStreetMap (fitness centres, sports centres, swimming pools)'],
    coverage: '94%',
    confidence: 'strong',
    note: null,
  },
  {
    category: 'Vibe & Culture',
    sources: [
      'OpenStreetMap (theatres, cinemas, arts centres, bookshops, record shops, vintage shops)',
      'Pedestrian street density',
    ],
    coverage: '98%',
    confidence: 'moderate',
    note: 'Cultural venue density differentiates neighborhood character. 252 stations also have editorial ratings.',
  },
  {
    category: 'Quietness',
    sources: ['MLIT S12 daily passenger counts', 'HotPepper commercial density (fallback)'],
    coverage: '100%',
    confidence: 'strong',
    note: 'Inverted: fewer passengers = higher rating.',
  },
];

const CONFIDENCE_LEVELS = [
  {
    level: 'Measured',
    icon: '◉',
    color: '#6A8059',
    description: 'Two or more independent data sources agree. High confidence in the rating.',
  },
  {
    level: 'Partial',
    icon: '●',
    color: '#C9A227',
    description: 'One data source or an aggregated fallback (e.g., ward-level rent instead of station-level).',
  },
  {
    level: 'Estimate',
    icon: '○',
    color: '#828A8C',
    description: 'Computed from a model or proxy without direct observation (e.g., rent regression, passenger heuristic).',
  },
  {
    level: 'Curated',
    icon: '◆',
    color: '#8B6DB0',
    description: 'Rating set by human research where the value differs from what the pipeline computed.',
  },
];

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            &larr; Back to map
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Methodology</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-10">
        {/* Intro */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">How ratings work</h2>
          <p className="text-gray-700 leading-relaxed">
            Every rating on this site is computed from real, verifiable data &mdash; restaurant databases,
            police crime statistics, transit authority records, and OpenStreetMap. We collect data from
            6+ sources, normalize using statistical percentiles across all 1,493 stations in Greater
            Tokyo, and combine multiple signals per category.
          </p>
          <p className="text-gray-700 leading-relaxed mt-3">
            252 stations also have individually researched descriptions with human-verified ratings.
            The remaining stations are purely data-driven.
          </p>
        </section>

        {/* Pipeline */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Rating pipeline</h2>
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <ol className="space-y-3 text-sm text-gray-700">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
                <div><strong>Scrape</strong> &mdash; Automated scrapers collect POI counts, crime data, passenger volumes, and rent prices from official APIs and open data.</div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
                <div><strong>Normalize</strong> &mdash; Raw counts are log-transformed (to handle extreme skew), then ranked by percentile across all 1,493 stations.</div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
                <div><strong>Cap</strong> &mdash; Absolute caps gate the top tiers: a &ldquo;10&rdquo; for transport requires 5+ train lines, not just being in the top percentile.</div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
                <div><strong>Merge</strong> &mdash; Pipeline ratings are merged with the 252 human-researched stations. Where they agree, pipeline confidence is inherited; where they differ, the human rating is marked &ldquo;Curated.&rdquo;</div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">5</span>
                <div><strong>Export</strong> &mdash; Ratings, confidence metadata, and source attribution are baked into the site at build time. No database at runtime.</div>
              </li>
            </ol>
          </div>
        </section>

        {/* Data Sources */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Data sources by category</h2>
          <div className="space-y-4">
            {DATA_SOURCES.map((ds) => (
              <div key={ds.category} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{ds.category}</h3>
                  <span className="text-xs text-gray-500">{ds.coverage} coverage</span>
                </div>
                <ul className="text-sm text-gray-600 space-y-1 mb-2">
                  {ds.sources.map((src, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-gray-400 mt-0.5">&#8226;</span>
                      {src}
                    </li>
                  ))}
                </ul>
                {ds.note && <p className="text-xs text-gray-500 italic">{ds.note}</p>}
              </div>
            ))}
          </div>
        </section>

        {/* Confidence Levels */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Confidence levels (Data Depth)</h2>
          <p className="text-gray-700 text-sm mb-4">
            Each category rating shows a shape icon indicating how much data backs it.
            Shape encodes the level &mdash; readable without color.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {CONFIDENCE_LEVELS.map((cl) => (
              <div key={cl.level} className="bg-white rounded-lg border border-gray-200 p-4 flex gap-3">
                <span
                  className="text-xl flex-shrink-0 mt-0.5"
                  style={{ color: cl.color }}
                  aria-hidden="true"
                >
                  {cl.icon}
                </span>
                <div>
                  <div className="font-semibold text-gray-900 text-sm">{cl.level}</div>
                  <div className="text-xs text-gray-600 mt-0.5">{cl.description}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Color system */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Color system</h2>
          <p className="text-gray-700 text-sm mb-3">
            Map markers and the ranked list use a diverging palette based on traditional Japanese pigments.
            Color encodes how a station compares to the median, not the raw score.
          </p>
          <div className="flex gap-1 items-center justify-center mb-3">
            {[
              { name: 'Akane', hex: '#8C2926', label: 'Below' },
              { name: 'Sango', hex: '#B3574E', label: '' },
              { name: 'Kinari', hex: '#D9C9A8', label: 'Median' },
              { name: 'Asagi', hex: '#6A8999', label: '' },
              { name: 'Kon', hex: '#2C4A5F', label: 'Above' },
            ].map((p) => (
              <div key={p.name} className="flex flex-col items-center gap-1">
                <div
                  className="w-12 h-8 rounded"
                  style={{ backgroundColor: p.hex }}
                  title={p.name}
                />
                <span className="text-[10px] text-gray-500">{p.label || p.name}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 text-center">
            The palette recalculates as you adjust weight sliders, so the full color range always spans the current distribution.
          </p>
        </section>

        {/* Weighted scoring */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Weighted scoring</h2>
          <p className="text-gray-700 text-sm">
            The composite score you see on the map is a weighted average of all 9 category ratings.
            Default weights emphasize rent (20%) and transport (20%), but you can drag the sliders
            to match your priorities. Dealbreaker filters (max rent, max commute, category minimums)
            are applied independently &mdash; they hide stations outright rather than lowering their score.
          </p>
        </section>

        {/* Known limitations */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Known limitations</h2>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Rent:</strong> Only 18% of stations have real station-level rent data (Suumo). The rest use ward averages or a distance-based regression. Tourist towns (e.g., Hakone) may show unrealistically low rents.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Safety outside Tokyo:</strong> Kanagawa, Saitama, and Chiba stations use ward/city-level crime data, not neighborhood-level. Actual safety may vary within a ward.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Green spaces:</strong> Currently based on park count, not area. A station near one large park (Yoyogi, 54ha) may score similarly to one near many small pocket parks.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Transit times:</strong> Computed from a geographic model calibrated against 252 ground-truth values (MAE 5.5 min). Not timetable-based &mdash; actual times depend on transfers, express services, and time of day.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Food data:</strong> HotPepper API is the primary source. Small independent restaurants without HotPepper listings may be undercounted, especially in rural areas.</span>
            </li>
          </ul>
        </section>

        {/* Data freshness */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Data freshness</h2>
          <p className="text-gray-700 text-sm">
            Ratings were last computed in April 2026. Crime data is from 2024 (Keishicho annual report).
            Passenger counts are from MLIT FY2021. Rent data is from Suumo snapshots taken in April 2026.
            OSM data reflects the state of OpenStreetMap at scrape time (April 2026).
          </p>
        </section>

        {/* Feedback */}
        <section className="pb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Disagree with a rating?</h2>
          <p className="text-gray-700 text-sm">
            Every station page has a feedback button. If you live near a station and think a rating is
            wrong, tell us &mdash; your local knowledge helps improve the data.
          </p>
        </section>
      </main>
    </div>
  );
}
