'use client';

import { useTranslations } from 'next-intl';
import { useAppStore } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { RATING_LABELS, WeightConfig } from '@/lib/types';

/** Phones: the controls sit in the second row as icons, beside Bangkok's level
 *  switch — text labels ("Тепловая карта", "Метро") ran into the search pill. */
function RailIcon() {
  return (
    <svg className="w-4 h-4 md:hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="5" y="3" width="14" height="14" rx="3" />
      <path d="M5 11h14M9 21l-2-4M15 21l2-4" />
      <circle cx="9" cy="14" r="0.5" fill="currentColor" />
      <circle cx="15" cy="14" r="0.5" fill="currentColor" />
    </svg>
  );
}

function LayersIcon() {
  return (
    <svg className="w-4 h-4 md:hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
    </svg>
  );
}

export default function MapControls() {
  const t = useTranslations();
  const city = useCity();
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const setHeatmapMode = useAppStore((s) => s.setHeatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const setHeatmapDimension = useAppStore((s) => s.setHeatmapDimension);
  const showRailOverlay = useAppStore((s) => s.showRailOverlay);
  const setShowRailOverlay = useAppStore((s) => s.setShowRailOverlay);

  return (
    <div className="absolute top-14 md:top-3 right-3 z-[1000] flex items-center gap-2">
      {city.features.railOverlay && (
        <button
          onClick={() => setShowRailOverlay(!showRailOverlay)}
          aria-pressed={showRailOverlay}
          aria-label={t('map.railNetwork')}
          title={t('map.railNetworkHint')}
          data-umami-event="toggle-rail-overlay"
          className={`map-control-btn flex items-center justify-center text-xs px-2.5 md:px-3 py-1.5 rounded-lg border shadow-sm transition-colors ${
            showRailOverlay
              ? 'bg-slate-800 text-white border-slate-800'
              : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
          }`}
        >
          <RailIcon />
          <span className="hidden md:inline">{t('map.railNetwork')}</span>
        </button>
      )}
      <button
        onClick={() => setHeatmapMode(!heatmapMode)}
        aria-pressed={heatmapMode}
        aria-label={t('map.heatmap')}
        className={`map-control-btn flex items-center justify-center text-xs px-2.5 md:px-3 py-1.5 rounded-lg border shadow-sm transition-colors ${
          heatmapMode
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
        }`}
      >
        <LayersIcon />
        <span className="hidden md:inline">{t('map.heatmap')}</span>
      </button>
      {heatmapMode && (
        <select
          value={heatmapDimension}
          onChange={(e) => setHeatmapDimension(e.target.value)}
          aria-label={t('map.heatmap')}
          // Phones: below the icon row (the level switch shares that row).
          className="map-control-btn absolute top-full right-0 mt-2 md:static md:mt-0 text-xs px-2 py-1.5 rounded-lg border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="composite">{t('map.compositeScore')}</option>
          {(Object.keys(RATING_LABELS) as (keyof WeightConfig)[]).map((key) => (
            <option key={key} value={key}>
              {t(`ratings.${key}`)}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
