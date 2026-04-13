'use client';

import { useState, useMemo, useDeferredValue } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useAppStore } from '@/lib/store';
import {
  RATING_LABELS,
  PRESET_PROFILES,
  DEFAULT_FILTERS,
  WeightConfig,
  MapStation,
  StationRatings,
} from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
  applyDealbreakers,
} from '@/lib/scoring';
import Tooltip from '@/components/Tooltip';
import { stationDisplayName, stationPrimaryName } from '@/lib/station-name';
import type { Locale } from '@/i18n/routing';

interface FilterPanelProps {
  stations: MapStation[];
}

const RENT_MIN = 80_000;
const RENT_MAX = 300_000;
const RENT_STEP = 10_000;
const COMMUTE_MIN = 10;
const COMMUTE_MAX = 60;
const COMMUTE_STEP = 5;
const CATEGORY_MIN_OPTIONS = [5, 6, 7, 8] as const;

function formatRent(v: number, isMin: boolean, noLimit: string): string {
  if (isMin && v <= RENT_MIN) return '¥80k';
  if (!isMin && v >= RENT_MAX) return noLimit;
  return `¥${(v / 1000).toFixed(0)}k`;
}

function formatCommute(v: number, isMin: boolean, noLimit: string): string {
  if (isMin && v <= COMMUTE_MIN) return '10 min';
  if (!isMin && v >= COMMUTE_MAX) return noLimit;
  return `${v} min`;
}

/** Dual-range slider: two thumbs on a single track */
function DualRange({
  min,
  max,
  step,
  valueLow,
  valueHigh,
  onLowChange,
  onHighChange,
  formatLow,
  formatHigh,
  label,
  umamiEvent,
}: {
  min: number;
  max: number;
  step: number;
  valueLow: number;
  valueHigh: number;
  onLowChange: (v: number) => void;
  onHighChange: (v: number) => void;
  formatLow: string;
  formatHigh: string;
  label: string;
  umamiEvent: string;
}) {
  const pctLow = ((valueLow - min) / (max - min)) * 100;
  const pctHigh = ((valueHigh - min) / (max - min)) * 100;

  return (
    <div>
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-700">{label}</span>
        <span className="text-gray-500 tabular-nums">{formatLow} – {formatHigh}</span>
      </div>
      <div className="relative h-4 flex items-center">
        {/* Track background */}
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-gray-200" />
        {/* Active range highlight */}
        <div
          className="absolute h-1.5 rounded-full bg-blue-200"
          style={{ left: `${pctLow}%`, right: `${100 - pctHigh}%` }}
        />
        {/* Low thumb */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={valueLow}
          onChange={(e) => {
            const v = Number(e.target.value);
            onLowChange(Math.min(v, valueHigh - step));
          }}
          data-umami-event={umamiEvent}
          className="absolute inset-x-0 w-full h-1.5 appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-pointer [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white [&::-moz-range-thumb]:shadow-sm [&::-moz-range-thumb]:cursor-pointer"
          style={{ zIndex: valueLow > min + (max - min) * 0.5 ? 3 : 1 }}
        />
        {/* High thumb */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={valueHigh}
          onChange={(e) => {
            const v = Number(e.target.value);
            onHighChange(Math.max(v, valueLow + step));
          }}
          data-umami-event={umamiEvent}
          className="absolute inset-x-0 w-full h-1.5 appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-pointer [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white [&::-moz-range-thumb]:shadow-sm [&::-moz-range-thumb]:cursor-pointer"
          style={{ zIndex: 2 }}
        />
      </div>
    </div>
  );
}

export default function FilterPanel({ stations }: FilterPanelProps) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const weights = useAppStore((s) => s.weights);
  const setWeight = useAppStore((s) => s.setWeight);
  const setAllWeights = useAppStore((s) => s.setAllWeights);
  const resetWeights = useAppStore((s) => s.resetWeights);
  const filters = useAppStore((s) => s.filters);
  const setMinRent = useAppStore((s) => s.setMinRent);
  const setMaxRent = useAppStore((s) => s.setMaxRent);
  const setMinCommute = useAppStore((s) => s.setMinCommute);
  const setMaxCommute = useAppStore((s) => s.setMaxCommute);
  const setCategoryMin = useAppStore((s) => s.setCategoryMin);
  const setFilters = useAppStore((s) => s.setFilters);
  const resetFilters = useAppStore((s) => s.resetFilters);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const setHoveredStation = useAppStore((s) => s.setHoveredStation);
  const hideFloodRisk = useAppStore((s) => s.hideFloodRisk);
  const setHideFloodRisk = useAppStore((s) => s.setHideFloodRisk);
  const hideHighSeismic = useAppStore((s) => s.hideHighSeismic);
  const setHideHighSeismic = useAppStore((s) => s.setHideHighSeismic);
  const [search, setSearch] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const deferredWeights = useDeferredValue(weights);
  const noLimit = t('filter.noLimit');

  const filtersActive =
    filters.minRent > DEFAULT_FILTERS.minRent ||
    filters.maxRent < DEFAULT_FILTERS.maxRent ||
    filters.minCommute > DEFAULT_FILTERS.minCommute ||
    filters.maxCommute < DEFAULT_FILTERS.maxCommute ||
    Object.keys(filters.categoryMins).length > 0 ||
    hideFloodRisk ||
    hideHighSeismic;

  const catMinCount = Object.keys(filters.categoryMins).length;

  // Score all stations, then apply dealbreakers for ranked list + match count
  const scoredStations = useMemo(() => {
    return stations
      .filter((s) => s.ratings !== null)
      .map((s) => ({
        ...s,
        score: calculateWeightedScore(s.ratings!, deferredWeights),
      }));
  }, [stations, deferredWeights]);

  const filtered = useMemo(
    () => applyDealbreakers(scoredStations, filters, hideFloodRisk, hideHighSeismic),
    [scoredStations, filters, hideFloodRisk, hideHighSeismic],
  );

  const ranked = useMemo(
    () =>
      [...filtered]
        .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
        .slice(0, 15),
    [filtered],
  );

  const compositeAnchors = useMemo(
    () => computeCompositeAnchors(stations, deferredWeights),
    [stations, deferredWeights],
  );

  const searchResults = useMemo(() => {
    if (!search || search.length < 2) return [];
    const q = search.toLowerCase();
    return stations
      .filter(
        (s) =>
          s.name_en.toLowerCase().includes(q) ||
          s.name_jp.includes(search) ||
          (s.name_ru && s.name_ru.toLowerCase().includes(q))
      )
      .slice(0, 8);
  }, [stations, search]);

  const totalWithRatings = stations.filter((s) => s.ratings).length;

  function applyPreset(presetId: string) {
    const p = PRESET_PROFILES.find((pr) => pr.id === presetId);
    if (!p) return;
    setAllWeights(p.weights);
    // Reset filters first, then apply preset filters
    resetFilters();
    if (p.filters) {
      if (p.filters.maxRent != null) setMaxRent(p.filters.maxRent);
      if (p.filters.maxCommute != null) setMaxCommute(p.filters.maxCommute);
      if (p.filters.categoryMins) {
        for (const [k, v] of Object.entries(p.filters.categoryMins)) {
          setCategoryMin(k as keyof StationRatings, v);
        }
      }
    }
    setActivePreset(presetId);
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      {/* Search — hidden on mobile where MobileSearchPill takes over */}
      <div className="relative hidden md:block">
        <input
          type="search"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          spellCheck={false}
          placeholder={t('filter.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
        {searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 overflow-hidden">
            {searchResults.map((s) => (
              <button
                key={s.slug}
                onClick={() => {
                  setSelectedStation(s.slug);
                  setHoveredStation(null);
                  setSearch('');
                }}
                onMouseEnter={() => setHoveredStation(s.slug)}
                onMouseLeave={() => setHoveredStation(null)}
                data-umami-event="search-select"
                data-umami-event-station={s.slug}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between border-b border-gray-50 last:border-0"
              >
                <span>
                  <span className="font-medium">{stationDisplayName(s, locale).primary}</span>
                  <span className="text-gray-400 ml-1.5 text-xs">{stationDisplayName(s, locale).secondary}</span>
                </span>
                <span className="text-xs text-gray-400">{t('filter.lines', { count: s.line_count })}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Presets */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t('filter.quickProfiles')}</h2>
        <div className="flex flex-wrap gap-1.5">
          {PRESET_PROFILES.map((p) => (
            <button
              key={p.id}
              onClick={() => applyPreset(p.id)}
              className={`text-xs px-2.5 py-1.5 rounded-full border cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 ${
                activePreset === p.id
                  ? 'bg-blue-100 border-blue-400 text-blue-700'
                  : 'bg-gray-50 border-gray-200 hover:bg-gray-100 text-gray-600'
              }`}
            >
              {p.icon} {t(`presets.${p.id}`)}
            </button>
          ))}
        </div>
      </div>

      {/* Dealbreakers */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('filter.dealbreakers')}</h2>
          {filtersActive && (
            <button
              onClick={() => {
                resetFilters();
                setHideFloodRisk(false);
                setHideHighSeismic(false);
                setActivePreset(null);
              }}
              data-umami-event="clear-filters"
              className="text-xs text-blue-600 hover:underline"
            >
              {t('filter.clearAll')}
            </button>
          )}
        </div>

        <div className="space-y-3">
          {/* Rent range */}
          <DualRange
            min={RENT_MIN}
            max={RENT_MAX}
            step={RENT_STEP}
            valueLow={filters.minRent}
            valueHigh={filters.maxRent}
            onLowChange={(v) => { setMinRent(v); setActivePreset(null); }}
            onHighChange={(v) => { setMaxRent(v); setActivePreset(null); }}
            formatLow={formatRent(filters.minRent, true, noLimit)}
            formatHigh={formatRent(filters.maxRent, false, noLimit)}
            label={t('filter.rent')}
            umamiEvent="filter-rent"
          />

          {/* Commute range */}
          <DualRange
            min={COMMUTE_MIN}
            max={COMMUTE_MAX}
            step={COMMUTE_STEP}
            valueLow={filters.minCommute}
            valueHigh={filters.maxCommute}
            onLowChange={(v) => { setMinCommute(v); setActivePreset(null); }}
            onHighChange={(v) => { setMaxCommute(v); setActivePreset(null); }}
            formatLow={formatCommute(filters.minCommute, true, noLimit)}
            formatHigh={formatCommute(filters.maxCommute, false, noLimit)}
            label={t('filter.commute')}
            umamiEvent="filter-commute"
          />

          {/* Category Minimums */}
          <details className="group">
            <summary className="flex items-center justify-between cursor-pointer text-xs text-gray-700 select-none py-1">
              <span className="flex items-center gap-1.5">
                <svg className="w-3 h-3 text-gray-400 transition-transform group-open:rotate-90" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
                {t('filter.minRatings')}
              </span>
              {catMinCount > 0 && (
                <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full tabular-nums">
                  {t('filter.nSet', { count: catMinCount })}
                </span>
              )}
            </summary>
            <div className="mt-2 space-y-1.5">
              {(Object.keys(RATING_LABELS) as (keyof StationRatings)[]).map((key) => {
                const current = filters.categoryMins[key] ?? null;
                return (
                  <div key={key} className="flex items-center gap-1.5">
                    <span className="text-[11px] text-gray-600 w-16 truncate shrink-0" title={t(`ratings.${key}`)}>
                      {t(`shortLabels.${key}`)}
                    </span>
                    <div className="flex gap-0.5">
                      <button
                        onClick={() => { setCategoryMin(key, null); setActivePreset(null); }}
                        data-umami-event="filter-category-min"
                        data-umami-event-category={key}
                        data-umami-event-value="off"
                        className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
                          current === null
                            ? 'bg-gray-200 border-gray-300 text-gray-700'
                            : 'bg-white border-gray-200 text-gray-400 hover:bg-gray-50'
                        }`}
                      >
                        {t('filter.off')}
                      </button>
                      {CATEGORY_MIN_OPTIONS.map((v) => (
                        <button
                          key={v}
                          onClick={() => { setCategoryMin(key, v); setActivePreset(null); }}
                          data-umami-event="filter-category-min"
                          data-umami-event-category={key}
                          data-umami-event-value={v}
                          className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors tabular-nums ${
                            current === v
                              ? 'bg-blue-100 border-blue-400 text-blue-700'
                              : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                          }`}
                        >
                          {'\u2265'}{v}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </details>

          {/* Environment Safety Filters */}
          <div className="space-y-2 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={hideFloodRisk}
                onChange={(e) => { setHideFloodRisk(e.target.checked); setActivePreset(null); }}
                className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
              />
              <span className="text-xs text-gray-600">
                {t('filter.hideFloodRisk')}
                <span className="text-gray-400 ml-1">{t('filter.belowXm')}</span>
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={hideHighSeismic}
                onChange={(e) => { setHideHighSeismic(e.target.checked); setActivePreset(null); }}
                className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
              />
              <span className="text-xs text-gray-600">
                {t('filter.hideHighSeismic')}
                <span className="text-gray-400 ml-1">{t('filter.seismicThreshold')}</span>
              </span>
            </label>
          </div>
        </div>

        {/* Match counter */}
        <div className="mt-3 text-xs tabular-nums">
          {filtered.length === totalWithRatings ? (
            <span className="text-gray-400">{t('filter.stationCount', { count: totalWithRatings })}</span>
          ) : filtered.length === 0 ? (
            <span className="text-amber-600">{t('filter.noMatch')}</span>
          ) : (
            <span className="text-gray-500">
              {t.rich('filter.matchCount', {
                filtered: filtered.length,
                total: totalWithRatings,
                bold: (chunks) => <span className="font-medium text-gray-700">{chunks}</span>,
              })}
            </span>
          )}
        </div>
      </div>

      <hr className="border-gray-200" />

      {/* Weights */}
      <div>
        <h2 className="text-lg font-bold mb-1">{t('filter.weights')}</h2>
        <p className="text-xs text-gray-500 mb-3">
          {t('filter.weightsDescription')}
        </p>
        <div className="space-y-2">
          {(Object.keys(RATING_LABELS) as (keyof WeightConfig)[]).map(
            (key) => (
              <div key={key}>
                <div className="flex justify-between text-xs mb-0.5 items-center gap-2">
                  <Tooltip content={t(`ratingTooltips.${key}`)}>
                    <span className="text-gray-700">{t(`ratings.${key}`)}</span>
                  </Tooltip>
                  <span className="text-gray-400 tabular-nums shrink-0">
                    {weights[key]}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={50}
                  value={weights[key]}
                  onChange={(e) => { setWeight(key, Number(e.target.value)); setActivePreset(null); }}
                  className="w-full h-1.5 accent-blue-600 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:rounded-full"
                />
              </div>
            )
          )}
        </div>
        <button
          onClick={() => { resetWeights(); setActivePreset(null); }}
          data-umami-event="reset-weights"
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          {t('filter.resetDefaults')}
        </button>
      </div>

      <hr className="border-gray-200" />

      {/* Top Ranked */}
      <div>
        <h2 className="text-lg font-bold mb-2">{t('filter.topRanked')}</h2>
        {ranked.length === 0 ? (
          <p className="text-sm text-gray-400">
            {filtersActive ? t('filter.noMatchFilters') : t('filter.noRatedYet')}
          </p>
        ) : (
          <ol className="space-y-1">
            {ranked.map((s, i) => (
              <li key={s.slug}>
                <button
                  onClick={() => setSelectedStation(s.slug)}
                  onMouseEnter={() => setHoveredStation(s.slug)}
                  onMouseLeave={() => setHoveredStation(null)}
                  onFocus={() => setHoveredStation(s.slug)}
                  onBlur={() => setHoveredStation(null)}
                  data-umami-event="ranked-select"
                  data-umami-event-station={s.slug}
                  className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset"
                >
                  <span className="text-xs text-gray-400 w-5 tabular-nums">
                    {i + 1}.
                  </span>
                  <span className="flex-1 text-sm font-medium truncate">
                    {stationPrimaryName(s, locale)}
                    {s.rentUnknown && (
                      <span className="text-[10px] text-gray-400 ml-1 font-normal">{t('filter.rentUnconfirmed')}</span>
                    )}
                  </span>
                  <span
                    className="text-sm font-bold tabular-nums"
                    style={{ color: compositeToColor(s.score ?? 0, compositeAnchors) }}
                  >
                    {(s.score ?? 0).toFixed(1)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>

      <hr className="border-gray-200" />

      <div className="text-xs text-gray-400">
        <p>{t('filter.stationsMapped', { count: stations.length })}</p>
        <p>{t('filter.withRatings', { count: totalWithRatings })}</p>
      </div>
    </div>
  );
}
