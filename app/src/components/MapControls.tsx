'use client';

import { useTranslations } from 'next-intl';
import { useAppStore } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { RATING_LABELS, WeightConfig } from '@/lib/types';

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
    <div className="absolute top-3 right-3 z-[1000] flex items-center gap-2">
      {city.features.railOverlay && (
        <button
          onClick={() => setShowRailOverlay(!showRailOverlay)}
          aria-pressed={showRailOverlay}
          title={t('map.railNetworkHint')}
          data-umami-event="toggle-rail-overlay"
          className={`map-control-btn text-xs px-3 py-1.5 rounded-lg border shadow-sm transition-colors ${
            showRailOverlay
              ? 'bg-slate-800 text-white border-slate-800'
              : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
          }`}
        >
          {t('map.railNetwork')}
        </button>
      )}
      <button
        onClick={() => setHeatmapMode(!heatmapMode)}
        aria-pressed={heatmapMode}
        className={`map-control-btn text-xs px-3 py-1.5 rounded-lg border shadow-sm transition-colors ${
          heatmapMode
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
        }`}
      >
        {t('map.heatmap')}
      </button>
      {heatmapMode && (
        <select
          value={heatmapDimension}
          onChange={(e) => setHeatmapDimension(e.target.value)}
          className="map-control-btn text-xs px-2 py-1.5 rounded-lg border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
