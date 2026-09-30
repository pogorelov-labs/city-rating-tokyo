'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { CITIES, CITY_IDS } from '@/lib/cities';
import { useCityId } from '@/lib/city-context';

/**
 * Tokyo ⇄ Bangkok segmented control. Plain locale-aware links (not state):
 * each city is its own route (`/`, `/bangkok`), so the choice is shareable,
 * indexable and survives reloads. Weights live in the shared store and carry
 * over; each city keeps its own filters and selection (see lib/store.ts).
 */
export default function CitySwitcher() {
  const t = useTranslations('city');
  const current = useCityId();

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
            href={CITIES[id].homePath}
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
