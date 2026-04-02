'use client';

import { useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { Station, RATING_LABELS, WeightConfig } from '@/lib/types';
import { calculateWeightedScore, scoreToColor } from '@/lib/scoring';
import CompareRadarChart from './CompareRadarChart';

const COLORS = ['#3b82f6', '#f97316', '#8b5cf6'];

interface Props {
  stations: Station[];
}

export default function ComparePanel({ stations }: Props) {
  const compareStations = useAppStore((s) => s.compareStations);
  const removeCompareStation = useAppStore((s) => s.removeCompareStation);
  const clearCompareStations = useAppStore((s) => s.clearCompareStations);
  const weights = useAppStore((s) => s.weights);

  const compared = useMemo(() => {
    return compareStations
      .map((slug) => stations.find((s) => s.slug === slug))
      .filter((s): s is Station => s !== undefined && s.ratings !== null);
  }, [compareStations, stations]);

  if (compared.length < 2) return null;

  const keys = Object.keys(RATING_LABELS) as (keyof WeightConfig)[];

  return (
    <div className="absolute bottom-0 left-0 md:left-72 right-0 z-[900] bg-white rounded-t-xl shadow-2xl border-t border-gray-200 max-h-[50vh] overflow-y-auto">
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
                {s.name_en}
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
            Clear all
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Radar */}
          <CompareRadarChart
            series={compared.map((s) => ({
              label: s.name_en,
              ratings: s.ratings!,
            }))}
          />

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-1 pr-2 text-gray-500 font-normal">Dimension</th>
                  {compared.map((s, i) => (
                    <th key={s.slug} className="text-right py-1 px-2 font-semibold" style={{ color: COLORS[i] }}>
                      {s.name_en}
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
                      <td className="py-1 pr-2 text-gray-500">{RATING_LABELS[key]}</td>
                      {values.map((v, i) => (
                        <td
                          key={i}
                          className={`text-right py-1 px-2 tabular-nums ${v === maxVal ? 'font-bold text-green-600' : ''}`}
                        >
                          {v}
                        </td>
                      ))}
                    </tr>
                  );
                })}
                {/* Composite score */}
                <tr className="border-t border-gray-200">
                  <td className="py-1 pr-2 font-semibold text-gray-700">Score</td>
                  {compared.map((s, i) => {
                    const score = calculateWeightedScore(s.ratings!, weights);
                    return (
                      <td key={i} className="text-right py-1 px-2 font-bold tabular-nums" style={{ color: scoreToColor(score) }}>
                        {score.toFixed(1)}
                      </td>
                    );
                  })}
                </tr>
                {/* Rent */}
                <tr>
                  <td className="py-1 pr-2 text-gray-500">Rent (1K)</td>
                  {compared.map((s, i) => (
                    <td key={i} className="text-right py-1 px-2 tabular-nums">
                      {s.rent_avg?.['1k_1ldk'] ? `¥${(s.rent_avg['1k_1ldk'] / 1000).toFixed(0)}k` : '-'}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
