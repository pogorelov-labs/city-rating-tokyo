'use client';

import { useDeferredValue, useMemo } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import railData from '@/data/bangkok/rail.json';
import type { Locale } from '@/i18n/routing';
import type { FilterState, MapStation, RailStation, StationRatings, WeightConfig } from '@/lib/types';
import { useAppStore, useCityActions, useCityState } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { useAreaLists } from '@/lib/area-lists';
import { cellKey, stationAreaKey } from '@/lib/area-key';
import { compositeToColor, type PercentileAnchors } from '@/lib/scoring';
import {
  cellInfo,
  countPassing,
  gridAnchors,
  gridHotspots,
  NEAR_STATION_M,
  passMask,
  scoreCells,
  useBangkokGrid,
  type BangkokGrid,
  type GridDistrict,
} from '@/lib/bangkok-grid';
import { stationPrimaryName } from '@/lib/station-name';

const STATION_BY_ID = new Map((railData as unknown as { stations: RailStation[] }).stations.map((s) => [s.id, s]));

interface Ranking {
  districts: GridDistrict[];
  scores: Float32Array;
  anchors: PercentileAnchors;
  pass: Uint8Array;
  passing: { cells: number; km2: number };
  hotspots: number[];
}

// The match counter and the list render in two places of the side panel;
// both ask for the same inputs in one render, so keep the last result.
let last: { grid: BangkokGrid; weights: WeightConfig; filters: FilterState; districts: MapStation[]; value: Ranking } | null =
  null;

function rank(grid: BangkokGrid, weights: WeightConfig, filters: FilterState, defaults: FilterState, districts: MapStation[]) {
  if (last && last.grid === grid && last.weights === weights && last.filters === filters && last.districts === districts) {
    return last.value;
  }
  const bySlug = new Map(districts.map((d) => [d.slug, d]));
  const gridDistricts = grid.header.districts.map((slug) => ({
    ratings: (bySlug.get(slug)?.ratings ?? {}) as StationRatings,
    rent_1k: bySlug.get(slug)?.rent_1k ?? null,
  }));
  const scores = scoreCells(grid, weights, gridDistricts);
  const pass = passMask(grid, filters, defaults, gridDistricts);
  const value: Ranking = {
    districts: gridDistricts,
    scores,
    anchors: gridAnchors(grid, scores),
    pass,
    passing: countPassing(grid, pass),
    hotspots: gridHotspots(grid, scores, pass, 10),
  };
  last = { grid, weights, filters, districts, value };
  return value;
}

function useGridRanking(districts: MapStation[]) {
  const city = useCity();
  const { grid, error } = useBangkokGrid(true);
  const weights = useDeferredValue(useAppStore((s) => s.weights));
  const filters = useCityState((s) => s.filters);
  const ranking = useMemo(
    () => (grid ? rank(grid, weights, filters, city.defaultFilters, districts) : null),
    [grid, weights, filters, city, districts],
  );
  return { grid, error, ranking };
}

/** "12,480 of 39,149 cells match (499 km²)" — the grid's match counter. */
export function GridMatchCount({ districts }: { districts: MapStation[] }) {
  const t = useTranslations('filter');
  const locale = useLocale() as Locale;
  const { grid, error, ranking } = useGridRanking(districts);
  if (error) return <span className="text-amber-600">{t('gridError')}</span>;
  if (!grid || !ranking) return <span className="text-gray-400">{t('gridLoading')}</span>;
  const nf = new Intl.NumberFormat(locale === 'en' ? 'en-US' : locale);
  const total = grid.cells.length;
  const { cells, km2 } = ranking.passing;
  if (cells === total) return <span className="text-gray-400">{t('stationCountGrid', { count: nf.format(total) })}</span>;
  if (cells === 0) return <span className="text-amber-600">{t('noMatchGrid')}</span>;
  return (
    <span className="text-gray-500">
      {t.rich('matchCountGrid', {
        filtered: nf.format(cells),
        total: nf.format(total),
        km2: nf.format(Math.round(km2)),
        bold: (chunks) => <span className="font-medium text-gray-700">{chunks}</span>,
      })}
    </span>
  );
}

/**
 * "Best spots": the top built-up cells under the current weights and
 * dealbreakers, ≥ 1.5 km apart, named after the nearest station area (or
 * the district where no station is in walking range).
 */
export function GridHotspotList({ districts }: { districts: MapStation[] }) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const lists = useAreaLists();
  const { setSelectedStation, setHoveredStation } = useCityActions();
  const { grid, error, ranking } = useGridRanking(districts);

  if (error) return <p className="text-sm text-amber-600">{t('filter.gridError')}</p>;
  if (!grid || !ranking) return <p className="text-sm text-gray-400">{t('filter.gridLoading')}</p>;
  if (ranking.hotspots.length === 0) return <p className="text-sm text-gray-400">{t('filter.noMatchFiltersGrid')}</p>;

  const areaByKey = new Map((lists?.station ?? []).map((a) => [a.slug, a]));
  const districtBySlug = new Map(districts.map((d) => [d.slug, d]));

  return (
    <ol className="space-y-1">
      {ranking.hotspots.map((i, n) => {
        const info = cellInfo(grid, i, ranking.districts);
        if (!info) return null;
        const area = info.areaId ? areaByKey.get(stationAreaKey(info.areaId)) : undefined;
        const station = info.stationId ? STATION_BY_ID.get(info.stationId) : undefined;
        const district = districtBySlug.get(info.districtSlug);
        const districtLabel = district ? stationPrimaryName(district, locale) : info.districtSlug;
        const stationLabel = area
          ? stationPrimaryName(area, locale)
          : station && info.stationDistanceM !== null && info.stationDistanceM <= NEAR_STATION_M
            ? locale === 'ja' && station.name_ja
              ? station.name_ja
              : station.name_en
            : null;
        const score = ranking.scores[i];
        const key = cellKey(i);
        return (
          <li key={i}>
            <button
              onClick={() => setSelectedStation(key)}
              onMouseEnter={() => setHoveredStation(key)}
              onMouseLeave={() => setHoveredStation(null)}
              onFocus={() => setHoveredStation(key)}
              onBlur={() => setHoveredStation(null)}
              data-umami-event="ranked-select"
              data-umami-event-station="cell"
              className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset"
            >
              <span className="text-xs text-gray-400 w-5 tabular-nums">{n + 1}.</span>
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-medium truncate">
                  {stationLabel ? t('map.cellNear', { station: stationLabel }) : districtLabel}
                </span>
                {stationLabel && <span className="block text-[11px] text-gray-400 truncate">{districtLabel}</span>}
              </span>
              <span className="text-sm font-bold tabular-nums" style={{ color: compositeToColor(score, ranking.anchors) }}>
                {score.toFixed(1)}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
