import { getTranslations } from 'next-intl/server';
import type { MapStation } from '@/lib/types';
import type { CityId } from '@/lib/cities';
import { CityProvider } from '@/lib/city-context';
import FilterPanel from '@/components/FilterPanel';
import MapWrapper from '@/components/MapWrapper';
import MobileDrawer from '@/components/MobileDrawer';
import MobileSearchPill from '@/components/MobileSearchPill';
import HeaderActions from '@/components/HeaderActions';
import LocaleSwitcher from '@/components/LocaleSwitcher';
import FeedbackWidget from '@/components/FeedbackWidget';
import CitySwitcher from '@/components/CitySwitcher';

interface Props {
  city: CityId;
  stations: MapStation[];
  thumbnails: Record<string, { thumb: string; lqip: string }>;
  snippets: Record<string, string>;
}

/**
 * The map homepage shell shared by every city: header (title, city switcher,
 * actions, locale), filter sidebar, map. `CityProvider` tells every client
 * component below which city's config / store slice to use.
 */
export default async function CityHome({ city, stations, thumbnails, snippets }: Props) {
  const t = await getTranslations();
  const isBangkok = city === 'bangkok';

  return (
    <CityProvider city={city}>
      <div className="flex flex-col h-dvh overflow-x-hidden">
        <header className="flex items-center justify-between gap-2 px-4 py-2 border-b border-gray-200 bg-white shrink-0 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            {/* On mobile the city switcher doubles as the title. */}
            <h1 className="hidden md:block text-xl font-bold tracking-tight truncate">
              <span className="lg:hidden">{isBangkok ? t('bangkok.header.titleShort') : t('header.titleShort')}</span>
              <span className="hidden lg:inline">{isBangkok ? t('bangkok.header.titleFull') : t('header.titleFull')}</span>
            </h1>
            <CitySwitcher />
            <span className="hidden min-[380px]:inline text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium shrink-0">
              {t('header.beta')}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-500 shrink-0">
            <HeaderActions stations={stations} />
            <LocaleSwitcher />
            <span className="hidden xl:inline">
              {isBangkok
                ? t('bangkok.header.districtCount', { count: stations.length })
                : t('header.stationCount', { count: stations.length })}
            </span>
            <a
              href="https://github.com/ruspg/city-rating-tokyo"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden xl:inline text-gray-400 hover:text-gray-600 transition-colors"
            >
              {t('header.byline')}
            </a>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          <aside className="hidden md:block w-72 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
            <FilterPanel stations={stations} />
            <div className="p-3 border-t border-gray-200">
              <FeedbackWidget source="general" />
            </div>
          </aside>

          <main className="flex-1 relative">
            <MapWrapper stations={stations} thumbnails={thumbnails} snippets={snippets} />
            <MobileSearchPill stations={stations} />
            <MobileDrawer stations={stations} />
          </main>
        </div>
      </div>
    </CityProvider>
  );
}
