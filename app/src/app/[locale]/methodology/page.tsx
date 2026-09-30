import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { Link } from '@/i18n/navigation';
import bangkokMeta from '@/data/bangkok/meta.json';

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
    note: '96% of stations have official MLIT passenger data (FY2024; an earlier year for unmanned JR East stations that dropped out of the latest tables).',
  },
  {
    category: 'Rent / Affordability',
    sources: ['Suumo station-level listings', 'e-Stat municipal average (labelled on the station page)', 'Log-linear distance regression'],
    coverage: '100%',
    confidence: 'mixed',
    note: '18% station-level listings, 76% municipal average, 6% regression estimate. A municipal average is capped at 9 and a regression at 8, so only listings can reach 10. Inverted: cheaper = higher rating.',
  },
  {
    category: 'Safety',
    sources: [
      'Tokyo Metropolitan Police neighborhood (町丁) crime counts',
      'Kanagawa, Saitama and Chiba police municipal crime statistics',
      'e-Stat population and boundaries',
    ],
    coverage: '100%',
    confidence: 'mixed',
    note: 'Weighted crimes per 10,000 people, 2024, the same formula in all four prefectures (daytime population in office districts). Tokyo stations use the neighborhoods within 800 m; elsewhere the municipality or ward, which is why those are marked Partial.',
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
    confidence: 'mixed',
    note: 'Measured when both cultural venues and pedestrian streets are observed, Partial with cultural venues alone. Cultural venue density differentiates neighborhood character. 252 stations also have editorial ratings.',
  },
  {
    category: 'Quietness',
    sources: ['MLIT S12 daily passenger counts', 'HotPepper commercial density (fallback)'],
    coverage: '100%',
    confidence: 'strong',
    note: 'Inverted: fewer passengers = higher rating. 55 unmanned stations that operators never report use a commercial-density proxy.',
  },
  {
    category: 'Daily Essentials',
    sources: ['OpenStreetMap (supermarkets, pharmacies, clinics, dentists, banks, laundry, post offices, schools, kindergartens)'],
    coverage: '100%',
    confidence: 'strong',
    note: '9 subcategories weighted by daily-life importance. 1491 stations from direct OSM data, 2 from proxy.',
  },
];

/** Bangkok (district-level) sources — see research/bangkok/00-overview.md. */
const BANGKOK_SOURCES: { category: string; sources: string; confidence: string }[] = [
  { category: 'Transport', sources: 'OpenStreetMap rail network (BTS, MRT, ARL, SRT Red, Gold, monorails) + bus stops and boat piers; modelled commute to 5 hubs', confidence: 'Partial' },
  { category: 'Rent / Affordability', sources: 'Researcher estimate of typical 1-bed / 2-bed condo asking rents, calibrated on published listing aggregates', confidence: 'Curated' },
  { category: 'Daily Essentials', sources: 'Overture Maps Places + OpenStreetMap (convenience stores, markets, pharmacies, clinics, banks, laundries, schools)', confidence: 'Measured (49/50)' },
  { category: 'Safety', sources: 'Researcher assessment — no open district-level crime data is published', confidence: 'Curated' },
  { category: 'Food & Dining', sources: 'Overture Maps Places + OpenStreetMap (restaurants, street-food stalls, cafés, food courts)', confidence: 'Measured (43/50)' },
  { category: 'Parks & Green', sources: 'OpenStreetMap park / garden / woodland polygons — hectares within 1 km', confidence: 'Partial' },
  { category: 'Gym & Sports', sources: 'Overture Maps Places + OpenStreetMap (gyms, sports centres, pools)', confidence: 'Measured / Partial' },
  { category: 'Vibe & Atmosphere', sources: 'Overture + OSM culture venues, cafés, temples, markets, pedestrian streets', confidence: 'Measured / Partial' },
  { category: 'Nightlife', sources: 'Overture + OSM bars, pubs, clubs, live-music venues, karaoke', confidence: 'Measured / Partial' },
  { category: 'Quietness', sources: 'DOPA registered population density + density of all mapped places (inverted)', confidence: 'Partial' },
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

export default async function MethodologyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations();
  const isEnglish = locale === 'en';
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            &larr; {t('nav.backToMap')}
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">{t('methodology.title')}</h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-10">
        {!isEnglish && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
            {t('methodology.englishOnlyNotice')}
          </div>
        )}
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
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Last train:</strong> Sourced from <a href="https://github.com/nagix/mini-tokyo-3d" className="underline">mini-tokyo-3d</a> (MIT licensed). We show the latest boardable departure in any direction. Weekday vs Sat/Holiday are split; Saturday and Sunday/Holiday timetables are combined in the source. Post-midnight times appear as 00:xx (no 24:00+ convention).</span>
            </li>
          </ul>
        </section>

        {/* Data freshness */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Data freshness</h2>
          <p className="text-gray-700 text-sm">
            Ratings were last computed in April 2026. Crime data is from 2024 police statistics in all four prefectures.
            Passenger counts are from MLIT S12, fiscal year 2024. Rent data is from Suumo snapshots taken in April 2026.
            OSM data reflects the state of OpenStreetMap at scrape time (April 2026).
          </p>
          <p className="text-gray-500 text-xs mt-3">
            Passenger counts: 出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）を加工して作成 —
            MLIT National Land Numerical Information,{' '}
            <a href="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html" className="underline">
              station passenger data (S12)
            </a>
            , processed by City Rating Tokyo.
          </p>
          <p className="text-gray-500 text-xs mt-2">
            Crime: 出典：警視庁ホームページ, 神奈川県警察ホームページ, 埼玉県警察ホームページ,
            千葉県警察ホームページ (2024 statistics). Population and small-area boundaries:
            出典：政府統計の総合窓口(e-Stat)（https://www.e-stat.go.jp/）を加工して作成; Tokyo daytime
            population: 東京都の統計. Source files and checksums are listed in data/crime/sources.json.
          </p>
        </section>

        {/* Bangkok */}
        <section id="bangkok" className="scroll-mt-4">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Bangkok: district-level ratings</h2>
          <p className="text-gray-700 leading-relaxed">
            Bangkok is rated by its {bangkokMeta.district_count} districts (<em>khet</em>), not by station:
            large parts of the city are not served by rail, and districts are how people there search for
            a place to live. The rail network is drawn on top of the map ({bangkokMeta.station_count} stations
            on 10 lines) as context.
          </p>
          <p className="text-gray-700 leading-relaxed mt-3">
            Each district is covered by a 200&nbsp;m grid. Every point records what a resident standing there
            can reach: places to eat, shops and clinics within walking distance, park hectares within 1&nbsp;km,
            the nearest rail station, and a modelled peak-hour commute to five hubs (Siam, Asok, Silom, Rama&nbsp;9,
            Mo&nbsp;Chit). Points in built-up areas carry full weight and empty paddy fields or river water almost
            none, so a huge semi-rural district is judged by where people actually live. District signals are then
            percentile-ranked across the 50 districts, exactly like Tokyo&apos;s stations.
          </p>
          <div className="bg-white rounded-lg border border-gray-200 mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="px-4 py-2 font-medium">Category</th>
                  <th className="px-4 py-2 font-medium">Sources</th>
                  <th className="px-4 py-2 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {BANGKOK_SOURCES.map((row) => (
                  <tr key={row.category} className="border-b border-gray-50 last:border-0 align-top">
                    <td className="px-4 py-2 font-medium text-gray-900 whitespace-nowrap">{row.category}</td>
                    <td className="px-4 py-2 text-gray-600">{row.sources}</td>
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">{row.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            The two POI sources agree closely across districts (Pearson r of log density: food{' '}
            {bangkokMeta.source_agreement_r.food}, nightlife {bangkokMeta.source_agreement_r.nightlife}, daily
            essentials {bangkokMeta.source_agreement_r.daily_essentials}, culture {bangkokMeta.source_agreement_r.vibe}).
            A category is &ldquo;Measured&rdquo; in a district only when both are well mapped there.
          </p>
          <h3 className="font-semibold text-gray-900 mt-5 mb-2">Bangkok limitations</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Scores are relative within each city.</strong> A Bangkok 8 means &ldquo;among the best of Bangkok&apos;s 50 districts&rdquo; &mdash; it is not comparable with a Tokyo 8. Weights carry over between cities; dealbreakers are kept per city because rent is in different currencies.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Rent and safety are researcher estimates.</strong> Bangkok publishes no open district-level rent or crime statistics and the listing portals block automated access, so both are marked &ldquo;Curated&rdquo;. Safety does not cover road traffic, the city&apos;s largest real risk.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Mapping bias.</strong> Tourist and expat districts are mapped more thoroughly than outer suburbs in both OSM and Overture; outer-district food and nightlife scores are likely understated.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Commute model.</strong> Door-to-door estimate: walk or motorbike taxi to a station, peak waits and average line speeds calibrated on published end-to-end times, or a road trip with distance-dependent peak speed. Not timetable-based; lines under construction are not included.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>No flood layer yet.</strong> Elevation and seismic filters are Tokyo-only. District-level flood exposure for Bangkok (e.g. from BMA Traffy Fondue flood reports) is a planned addition.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">&#9888;</span>
              <span><strong>Population</strong> is DOPA house registration (2020, via Wikidata); central districts house many unregistered residents, so their real density is higher.</span>
            </li>
          </ul>
          <p className="text-xs text-gray-500 mt-3">
            Data: &copy; OpenStreetMap contributors (ODbL), Overture Maps Places release 2026-09-23 (CDLA-Permissive-2.0),
            Wikidata (CC0), district photos from Wikimedia Commons (credited on each page). Computed {bangkokMeta.data_date}.
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
