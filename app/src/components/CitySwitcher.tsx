'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { CITIES, CITY_IDS } from '@/lib/cities';
import { useCityId } from '@/lib/city-context';
import { useAppStore } from '@/lib/store';
import { withGuideWeights } from '@/lib/area-guide';

/**
 * Locale-aware links carry shared weights across full navigations and new
 * tabs. City-specific filters and selection stay in their own store slices.
 */
export default function CitySwitcher() {
  const t = useTranslations('city');
  const current = useCityId();
  const weights = useAppStore(state => state.weights);

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
