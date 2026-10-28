'use client';

import { useTranslations } from 'next-intl';
import type { AreaLevel } from '@/lib/types';
import { compositeToColor, scoreToColor, type ColorDimension, type PercentileAnchors } from '@/lib/scoring';

const FILTERED_FILL = '#E5E7EB';

export function Legend({
  anchors,
  level,
  heatmapMode,
  heatmapDimension,
  filtersActive,
}: {
  anchors: PercentileAnchors;
  level: AreaLevel;
  heatmapMode: boolean;
  heatmapDimension: string;
  filtersActive: boolean;
}) {
  const t = useTranslations();
  const dim = heatmapMode && heatmapDimension !== 'composite' ? (heatmapDimension as Exclude<ColorDimension, 'composite'>) : null;
  const stops = dim
    ? [1, 5.5, 10].map((v) => scoreToColor(v, dim))
    : [anchors.p5, (anchors.p5 + anchors.p50) / 2, anchors.p50, (anchors.p50 + anchors.p95) / 2, anchors.p95].map((v) =>
        compositeToColor(v, anchors),
      );
  const title = dim ? t(`ratings.${dim}`) : t('map.compositeScore');
  const caption = level === 'grid' ? 'map.legendGrid' : level === 'station' ? 'map.legendStations' : 'map.legendDistricts';
  return (
    <div className="hidden md:block absolute bottom-6 left-3 z-[900] bg-white/95 border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-[10px] text-gray-600 w-52 pointer-events-none">
      <div className="font-semibold text-gray-700 mb-1 truncate">{title}</div>
      <div className="h-2 rounded-full" style={{ backgroundImage: `linear-gradient(90deg, ${stops.join(', ')})` }} />
      <div className="flex justify-between mt-0.5 tabular-nums">
        <span>{dim ? '1' : anchors.p5.toFixed(1)}</span>
        {!dim && <span>{anchors.p50.toFixed(1)}</span>}
        <span>{dim ? '10' : anchors.p95.toFixed(1)}</span>
      </div>
      {/* The captions describe the weighted score, not a single-category heatmap. */}
      {!dim && <div className="mt-1 text-gray-500 leading-snug">{t(caption)}</div>}
      {level === 'station' && <div className="mt-1 text-gray-500 leading-snug">{t('map.legendNoStation')}</div>}
      {level === 'grid' && (
        <div className="mt-1 text-gray-500 leading-snug">
          {t('map.legendGridFaded')} {t('map.legendGridDistrict')}
        </div>
      )}
      {filtersActive && (
        <div className="mt-1 flex items-center gap-1.5">
          <span className="inline-block w-3 h-2 rounded-sm border border-gray-300" style={{ backgroundColor: FILTERED_FILL }} />
          {t('map.legendFilteredOut')}
        </div>
      )}
    </div>
  );
}

/** District level, zoomed in: point at the finer levels once. */
export function ZoomHint({ onPick }: { onPick: (level: AreaLevel) => void }) {
  const t = useTranslations('map');
  return (
    <div className="hidden md:flex absolute left-3 top-14 z-[999] items-center gap-2 rounded-lg border border-blue-200 bg-blue-50/95 px-2.5 py-1.5 text-[11px] text-blue-800 shadow-sm">
      <span>{t('zoomHint')}</span>
      <button onClick={() => onPick('station')} className="font-semibold hover:underline">
        {t('level_station')}
      </button>
      <span aria-hidden>·</span>
      <button onClick={() => onPick('grid')} className="font-semibold hover:underline">
        {t('level_grid')}
      </button>
    </div>
  );
}
