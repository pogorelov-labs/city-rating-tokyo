'use client';

import { useCallback, useMemo } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import railData from '@/data/bangkok/rail.json';
import type { Locale } from '@/i18n/routing';
import type { MapStation, RailStation, StationRatings } from '@/lib/types';
import { useAppStore, useCityActions, useCityState } from '@/lib/store';
import { useAreaLists } from '@/lib/area-lists';
import { parseAreaKey, stationAreaKey } from '@/lib/area-key';
import { cellInfo, scoreCells, useBangkokGrid, type GridDistrict } from '@/lib/bangkok-grid';
import { stationPrimaryName } from '@/lib/station-name';
import { useIsTouch } from '@/lib/use-is-touch';
import { CellDetails } from './popups';

const STATION_BY_ID = new Map((railData as unknown as { stations: RailStation[] }).stations.map((s) => [s.id, s]));

/**
 * Touch counterpart of the grid-cell popup: a bottom card like
 * MobileStationCard (the Leaflet popup clips and has tiny targets on phones).
 */
export default function CellCard({ districts }: { districts: MapStation[] }) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const isTouch = useIsTouch();
  const selected = useCityState((s) => s.selectedStation);
  const isFlying = useAppStore((s) => s.isFlying);
  const weights = useAppStore((s) => s.weights);
  const { setSelectedStation } = useCityActions();
  const lists = useAreaLists();
  const { grid } = useBangkokGrid(true);

  const gridDistricts: GridDistrict[] = useMemo(() => {
    if (!grid) return [];
    const bySlug = new Map(districts.map((d) => [d.slug, d]));
    return grid.header.districts.map((slug) => ({
      ratings: (bySlug.get(slug)?.ratings ?? {}) as StationRatings,
      rent_1k: bySlug.get(slug)?.rent_1k ?? null,
    }));
  }, [grid, districts]);

  const key = selected ? parseAreaKey(selected) : null;
  const index = key?.kind === 'cell' ? key.index : null;
  const info = useMemo(
    () => (grid && index !== null ? cellInfo(grid, index, gridDistricts) : null),
    [grid, index, gridDistricts],
  );
  // One cell's score: the full-grid pass is cheap, but only the value is needed.
  const score = useMemo(() => {
    if (!grid || index === null || !info) return null;
    const s = scoreCells(grid, weights, gridDistricts)[index];
    return Number.isNaN(s) ? null : s;
  }, [grid, index, info, weights, gridDistricts]);

  const districtName = useCallback(
    (slug: string) => {
      const d = districts.find((x) => x.slug === slug);
      return d ? stationPrimaryName(d, locale) : slug;
    },
    [districts, locale],
  );
  const stationName = useCallback(
    (id: string) => {
      const s = STATION_BY_ID.get(id);
      return s ? (locale === 'ja' && s.name_ja ? s.name_ja : s.name_en) : id;
    },
    [locale],
  );
  const areaName = useCallback(
    (id: string) => {
      const a = lists?.station.find((x) => x.slug === stationAreaKey(id));
      return a ? stationPrimaryName(a, locale) : stationName(id);
    },
    [lists, locale, stationName],
  );

  if (!isTouch || !grid || !info || isFlying) return null;

  return (
    <div
      // Same stacking as MobileStationCard: over the touch zoom buttons (equal
      // z, later in the DOM), under the compare panel and the filter drawer.
      className="md:hidden fixed bottom-0 left-3 right-3 z-[1000] bg-white rounded-xl shadow-2xl border border-gray-200 max-h-[60vh] overflow-y-auto"
      style={{ marginBottom: 'max(12px, env(safe-area-inset-bottom, 12px))' }}
      role="dialog"
      aria-label={t('map.cellTitle')}
    >
      <div className="flex items-start gap-2 p-3">
        <div className="flex-1 min-w-0">
          <CellDetails
            info={info}
            score={score}
            medians={grid.header.medians}
            stationName={stationName}
            areaName={areaName}
            districtName={districtName}
            compact
          />
        </div>
        <button
          onClick={() => setSelectedStation(null)}
          aria-label={t('map.closeCardCell')}
          className="shrink-0 -mr-1 -mt-1 p-2 text-gray-400 active:text-gray-600 active:bg-gray-100 rounded-lg"
          style={{ minWidth: 36, minHeight: 36 }}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
