import { getStations } from '@/lib/data';
import FilterPanel from '@/components/FilterPanel';
import MapWrapper from '@/components/MapWrapper';
import MobileDrawer from '@/components/MobileDrawer';
import HeaderActions from '@/components/HeaderActions';
import stationImages from '@/data/station-images.json';

const imageData = stationImages as Record<string, { url: string; alt: string }[]>;

const stations = getStations();

// Pre-compute thumbnail URLs and atmosphere snippets for map hover
const stationThumbnails: Record<string, string> = {};
const stationSnippets: Record<string, string> = {};
for (const s of stations) {
  const imgs = imageData[s.slug];
  if (imgs?.[0]) stationThumbnails[s.slug] = imgs[0].url;
  if (s.description?.atmosphere) {
    stationSnippets[s.slug] = s.description.atmosphere.length > 120
      ? s.description.atmosphere.slice(0, 120) + '...'
      : s.description.atmosphere;
  }
}

export default function Home() {
  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white shrink-0 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xl font-bold tracking-tight truncate">
            Tokyo Neighborhood Explorer
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium shrink-0">
            BETA
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-500 shrink-0">
          <HeaderActions stations={stations} />
          <span>{stations.length} stations</span>
          <a
            href="https://github.com/ruspg/city-rating-tokyo"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            by @ruspg
          </a>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden md:block w-72 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
          <FilterPanel stations={stations} />
        </aside>

        <main className="flex-1 relative">
          <MapWrapper
            stations={stations}
            thumbnails={stationThumbnails}
            snippets={stationSnippets}
          />
          <MobileDrawer stations={stations} />
        </main>
      </div>
    </div>
  );
}
