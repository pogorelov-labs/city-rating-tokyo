'use client';

import { useTranslations } from 'next-intl';
import { Link, usePathname, useRouter } from '@/i18n/navigation';
import { CITIES, CITY_IDS, type CityId } from '@/lib/cities';
import { useCityId } from '@/lib/city-context';
import { useAppStore } from '@/lib/store';
import { withGuideWeights } from '@/lib/area-guide';
import { encodeStateToParams, selectUrlView } from '@/lib/url-state';

/**
 * Locale-aware links carry shared weights across full navigations and new
 * tabs. City-specific filters and selection stay in their own store slices.
 */
export default function CitySwitcher() {
  const t = useTranslations('city');
  const current = useCityId();
  const router = useRouter();
  const pathname = usePathname();
  const weights = useAppStore(state => state.weights);

  const switchCity = (event: { preventDefault: () => void }, destination: CityId) => {
    if (destination === current && pathname === CITIES[current].homePath) { event.preventDefault(); return; }
    const state = useAppStore.getState();
    const path = CITIES[destination].homePath;
    const params = encodeStateToParams(selectUrlView(state, destination), destination).toString();
    const target = path + (params ? `?${params}` : '');
    // Leave the ordinary Link navigation in place when no destination state
    // needs carrying. onNavigate only runs for uncanceled same-tab SPA links;
    // copied URLs, new tabs, downloads and modified clicks keep the public href.
    if (target !== withGuideWeights(path, weights)) {
      event.preventDefault();
      router.push(target);
    }
  };

  return (
    <nav
      aria-label={t('switchLabel')}
      className="inline-flex items-center rounded-lg border border-gray-200 bg-white overflow-hidden text-xs shrink-0"
    >
      {CITY_IDS.map((id) => {
        const active = id === current;
        return (
          <Link
            key={id}
            href={withGuideWeights(CITIES[id].homePath, weights)}
            onNavigate={(event) => switchCity(event, id)}
            aria-current={active ? 'page' : undefined}
            data-umami-event="switch-city"
            data-umami-event-city={id}
            className={`px-2.5 py-1 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset ${
              active ? 'bg-slate-800 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t(id)}
          </Link>
        );
      })}
    </nav>
  );
}
