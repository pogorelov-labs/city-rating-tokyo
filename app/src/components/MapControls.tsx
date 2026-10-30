'use client';

import { useTranslations } from 'next-intl';
import { useEffect, useRef, useState } from 'react';
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

function LayersIcon({ compact = false }: { compact?: boolean }) {
  return (
    <svg className={compact ? "w-4 h-4" : "w-4 h-4 md:hidden"} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
    </svg>
  );
}

export default function MapControls() {
  const t = useTranslations();
  const city = useCity();
  const container = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const parent = container.current?.parentElement;
    if (!parent) return;
    const observer = new ResizeObserver(([entry]) => {
      const compact = entry.contentRect.width < 640;
      setNarrow(compact);
      if (!compact) setOpen(false);
    });
    observer.observe(parent);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!open) return;
    const outside = (event: Event) => { if (!container.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside); };
  }, [open]);
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const setHeatmapMode = useAppStore((s) => s.setHeatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const setHeatmapDimension = useAppStore((s) => s.setHeatmapDimension);
  const showRailOverlay = useAppStore((s) => s.showRailOverlay);
  const setShowRailOverlay = useAppStore((s) => s.setShowRailOverlay);

  const compact = city.id === 'bangkok' && narrow;
  if (compact) return (
    <div ref={container} className="absolute top-14 md:top-3 right-3 z-[1000]" onKeyDown={(event) => { if (event.key === 'Escape' && open) { event.stopPropagation(); setOpen(false); } }}>
      <button type="button" aria-label={t('map.layers')} aria-expanded={open} onClick={() => setOpen(!open)} className="map-control-btn flex h-11 w-11 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-700 shadow-sm focus-visible:outline-2 focus-visible:outline-blue-600"><LayersIcon compact /></button>
      {open && <div role="group" aria-label={t('map.layers')} className="absolute right-14 top-0 flex min-w-40 flex-col gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-lg">
        <button type="button" aria-pressed={showRailOverlay} onClick={() => setShowRailOverlay(!showRailOverlay)} data-umami-event="toggle-rail-overlay" className="min-h-11 rounded px-3 text-left text-sm hover:bg-slate-100">{t('map.railNetwork')}{showRailOverlay && <span aria-hidden="true"> ✓</span>}</button>
        <button type="button" aria-pressed={heatmapMode} onClick={() => setHeatmapMode(!heatmapMode)} className="min-h-11 rounded px-3 text-left text-sm hover:bg-slate-100">{t('map.heatmap')}{heatmapMode && <span aria-hidden="true"> ✓</span>}</button>
        {heatmapMode && <select value={heatmapDimension} onChange={(event) => { setHeatmapDimension(event.target.value); setOpen(false); }} aria-label={t('map.heatmap')} className="min-h-11 max-w-48 rounded border border-gray-200 px-2 text-sm">
          <option value="composite">{t('map.compositeScore')}</option>
          {(Object.keys(RATING_LABELS) as (keyof WeightConfig)[]).map((key) => <option key={key} value={key}>{t(`ratings.${key}`)}</option>)}
        </select>}
      </div>}
    </div>
  );
  return (
    <div ref={container} className="absolute top-14 md:top-3 right-3 z-[1000] flex items-center gap-2">
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
