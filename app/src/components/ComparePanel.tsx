'use client';

import { useMemo, useDeferredValue } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useAppStore } from '@/lib/store';
import { MapStation, RATING_LABELS, WeightConfig } from '@/lib/types';
import {
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
} from '@/lib/scoring';
import CompareRadarChart from './CompareRadarChart';
import { stationPrimaryName } from '@/lib/station-name';
import type { Locale } from '@/i18n/routing';

const COLORS = ['#3b82f6', '#f97316', '#8b5cf6'];

interface Props {
  stations: MapStation[];
}

export default function ComparePanel({ stations }: Props) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const compareStations = useAppStore((s) => s.compareStations);
  const removeCompareStation = useAppStore((s) => s.removeCompareStation);
  const clearCompareStations = useAppStore((s) => s.clearCompareStations);
  const weights = useAppStore((s) => s.weights);
  // Defer weights so the (expensive) percentile sort over 1493 scores
  // doesn't fire on every drag frame while the user is adjusting sliders.
  const deferredWeights = useDeferredValue(weights);

  const compared = useMemo(() => {
    return compareStations
      .map((slug) => stations.find((s) => s.slug === slug))
      .filter((s): s is MapStation => s !== undefined && s.ratings !== null);
  }, [compareStations, stations]);

  const compositeAnchors = useMemo(
    () => computeCompositeAnchors(stations, deferredWeights),
    [stations, deferredWeights],
  );

  if (compared.length < 2) return null;

  const keys = Object.keys(RATING_LABELS) as (keyof WeightConfig)[];

  return (
    <div className="absolute bottom-0 left-0 md:left-72 right-0 z-[900] bg-white rounded-t-xl shadow-2xl border-t border-gray-200 max-h-[50vh] overflow-y-auto" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {compared.map((s, i) => (
              <span
                key={s.slug}
                className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border"
                style={{ borderColor: COLORS[i], color: COLORS[i] }}
              >
                {stationPrimaryName(s, locale)}
                <button
                  onClick={() => removeCompareStation(s.slug)}
                  className="hover:opacity-60 ml-0.5"
                >
                  x
                </button>
              </span>
            ))}
          </div>
          <button
            onClick={clearCompareStations}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            {t('compare.clearAll')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Radar */}
          <CompareRadarChart
            series={compared.map((s) => ({
              label: stationPrimaryName(s, locale),
              ratings: s.ratings!,
            }))}
          />

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-1 pr-2 text-gray-500 font-normal">{t('compare.dimension')}</th>
                  {compared.map((s, i) => (
                    <th key={s.slug} className="text-right py-1 px-2 font-semibold" style={{ color: COLORS[i] }}>
                      {stationPrimaryName(s, locale)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => {
                  const values = compared.map((s) => s.ratings![key]);
                  const maxVal = Math.max(...values);
                  return (
                    <tr key={key} className="border-b border-gray-50">
                      <td className="py-1 pr-2 text-gray-500">{t(`ratings.${key}`)}</td>
                      {compared.map((s, i) => {
                        const v = s.ratings![key];
                        return (
                          <td
                            key={i}
                            className={`text-right py-1 px-2 tabular-nums ${v === maxVal ? 'font-bold text-green-600' : ''}`}
                          >
                            {v}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
                {/* Composite score */}
                <tr className="border-t border-gray-200">
                  <td className="py-1 pr-2 font-semibold text-gray-700">{t('compare.score')}</td>
                  {compared.map((s, i) => {
                    const score = calculateWeightedScore(s.ratings!, deferredWeights);
                    return (
                      <td key={i} className="text-right py-1 px-2 font-bold tabular-nums" style={{ color: compositeToColor(score, compositeAnchors) }}>
                        {score.toFixed(1)}
                      </td>
                    );
                  })}
                </tr>
                {/* Rent */}
                <tr>
                  <td className="py-1 pr-2 text-gray-500">{t('compare.rent1k')}</td>
                  {compared.map((s, i) => (
                    <td key={i} className="text-right py-1 px-2 tabular-nums">
                      {s.rent_1k ? `¥${(s.rent_1k / 1000).toFixed(0)}k` : '-'}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        {/* Extra clearance for Safari's dynamic toolbar on mobile */}
        <div className="h-4 md:hidden" />
      </div>
    </div>
  );
}
