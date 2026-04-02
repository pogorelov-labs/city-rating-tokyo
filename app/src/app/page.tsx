import { getStations } from '@/lib/data';
import FilterPanel from '@/components/FilterPanel';
import MapWrapper from '@/components/MapWrapper';
import MobileDrawer from '@/components/MobileDrawer';

const stations = getStations();

export default function Home() {
  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight">
            Tokyo Neighborhood Explorer
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">
            BETA
          </span>
        </div>
        <div className="text-sm text-gray-500">
          {stations.length} stations
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden md:block w-72 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
          <FilterPanel stations={stations} />
        </aside>

        <main className="flex-1 relative">
          <MapWrapper stations={stations} />
          <MobileDrawer stations={stations} />
        </main>
      </div>
    </div>
  );
}
