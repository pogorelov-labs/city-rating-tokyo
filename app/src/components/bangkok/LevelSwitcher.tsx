'use client';

import { useTranslations } from 'next-intl';
import { useCity } from '@/lib/city-context';
import { useCityActions, useCityState } from '@/lib/store';
import { ensureBangkokGrid } from '@/lib/bangkok-grid';
import type { AreaLevel } from '@/lib/types';

/**
 * Level-of-detail switch for cities rated at several scales (Bangkok:
 * districts → station areas → 200 m grid). A segmented control: exactly one
 * level is painted on the map and ranked in the side panel; the selection,
 * weights and dealbreakers carry over.
 */
export default function LevelSwitcher() {
  const t = useTranslations('map');
  const city = useCity();
  const level = useCityState((s) => s.level);
  const { setLevel } = useCityActions();
  if (city.levels.length < 2) return null;

  const choose = (l: AreaLevel) => {
    if (l === level) return;
    setLevel(l);
    window.umami?.track('switch-level', { city: city.id, level: l });
  };

  return (
    <div
      role="radiogroup"
      aria-label={t('levelLabel')}
      className="absolute left-3 top-14 md:top-3 z-[1000] flex items-center rounded-lg border border-gray-200 bg-white/95 p-0.5 shadow-sm"
    >
      {city.levels.map((l) => {
        const active = l === level;
        return (
          <button
            key={l}
            role="radio"
            aria-checked={active}
            title={t(`levelHint_${l}`)}
            onClick={() => choose(l)}
            // Warm the grid while the pointer is on its way to the button.
            onPointerEnter={l === 'grid' ? () => void ensureBangkokGrid() : undefined}
            onFocus={l === 'grid' ? () => void ensureBangkokGrid() : undefined}
            className={`map-control-btn text-xs px-2.5 py-1 rounded-md transition-colors whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              active ? 'bg-slate-800 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {t(`level_${l}`)}
          </button>
        );
      })}
    </div>
  );
}
