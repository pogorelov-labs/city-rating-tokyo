import { getTranslations, setRequestLocale } from 'next-intl/server';
import { getMapStations, getThumbnails, getSnippets } from '@/lib/data';
import FilterPanel from '@/components/FilterPanel';
import MapWrapper from '@/components/MapWrapper';
import MobileDrawer from '@/components/MobileDrawer';
import MobileSearchPill from '@/components/MobileSearchPill';
import HeaderActions from '@/components/HeaderActions';
import LocaleSwitcher from '@/components/LocaleSwitcher';
import FeedbackWidget from '@/components/FeedbackWidget';

const stations = getMapStations();
const thumbnails = getThumbnails();
const snippets = getSnippets();

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('header');

  return (
    <div className="flex flex-col h-dvh overflow-x-hidden">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white shrink-0 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xl font-bold tracking-tight truncate">
            <span className="md:hidden">{t('titleShort')}</span>
            <span className="hidden md:inline">{t('titleFull')}</span>
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium shrink-0">
            {t('beta')}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-500 shrink-0">
          <HeaderActions stations={stations} />
          <LocaleSwitcher />
          <span className="hidden md:inline">{t('stationCount', { count: stations.length })}</span>
          <a
            href="https://github.com/ruspg/city-rating-tokyo"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden md:inline text-gray-400 hover:text-gray-600 transition-colors"
          >
            {t('byline')}
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
          <MapWrapper
            stations={stations}
            thumbnails={thumbnails}
            snippets={snippets}
          />
          <MobileSearchPill stations={stations} />
          <MobileDrawer stations={stations} />
        </main>
      </div>
    </div>
  );
}
