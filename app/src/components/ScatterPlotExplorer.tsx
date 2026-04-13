'use client';

import { useState, useMemo, useDeferredValue } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation, RATING_LABELS } from '@/lib/types';
import { stationPrimaryName } from '@/lib/station-name';
import type { Locale } from '@/i18n/routing';
import { useAppStore } from '@/lib/store';
import {
  calculateWeightedScore,
  compositeToColor,
  computeCompositeAnchors,
  getAxisValue,
} from '@/lib/scoring';

interface Props {
  stations: MapStation[];
}

/** Axis options: rating keys + rent + transit */
const AXIS_KEYS = [
  ...Object.keys(RATING_LABELS),
  'rent_1k',
  'min_transit',
] as const;

export default function ScatterPlotExplorer({ stations }: Props) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const weights = useAppStore((s) => s.weights);
  const deferredWeights = useDeferredValue(weights);
  const [xAxis, setXAxis] = useState('rent');
  const [yAxis, setYAxis] = useState('food');

  function axisLabel(key: string): string {
    if (key === 'rent_1k') return t('scatterAxes.rent_1k');
    if (key === 'min_transit') return t('scatterAxes.min_transit');
    return t(`ratings.${key}`);
  }

  const xLabel = axisLabel(xAxis);
  const yLabel = axisLabel(yAxis);

  // Defer the anchors too — sorting 1493 scores fires on every weight
  // change and should track the deferred score computation below so
  // colors and points stay in sync mid-drag.
  const compositeAnchors = useMemo(
    () => computeCompositeAnchors(stations, deferredWeights),
    [stations, deferredWeights],
  );

  const data = useMemo(() => {
    return stations
      .filter((s) => s.ratings)
      .map((s) => {
        const x = getAxisValue(s, xAxis);
        const y = getAxisValue(s, yAxis);
        if (x === null || y === null) return null;
        const score = calculateWeightedScore(s.ratings!, deferredWeights);
        return { name: stationPrimaryName(s, locale), x, y, score, fill: compositeToColor(score, compositeAnchors) };
      })
      .filter(Boolean) as { name: string; x: number; y: number; score: number; fill: string }[];
  }, [stations, deferredWeights, xAxis, yAxis, compositeAnchors]);

  return (
    <div>
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-gray-500">X:</span>
          <select
            value={xAxis}
            onChange={(e) => setXAxis(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {AXIS_KEYS.map((key) => (
              <option key={key} value={key}>{axisLabel(key)}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-sm">
          <span className="text-gray-500">Y:</span>
          <select
            value={yAxis}
            onChange={(e) => setYAxis(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {AXIS_KEYS.map((key) => (
              <option key={key} value={key}>{axisLabel(key)}</option>
            ))}
          </select>
        </label>
        <span className="text-xs text-gray-400">{t('filter.stationCount', { count: data.length })}</span>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="x" name={xLabel} type="number" tick={{ fontSize: 11 }} label={{ value: xLabel, position: 'bottom', fontSize: 12, fill: '#6b7280' }} />
          <YAxis dataKey="y" name={yLabel} type="number" tick={{ fontSize: 11 }} label={{ value: yLabel, angle: -90, position: 'insideLeft', fontSize: 12, fill: '#6b7280' }} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const d = payload[0].payload as { name: string; x: number; y: number; score: number };
              return (
                <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
                  <div className="font-bold">{d.name}</div>
                  <div className="text-gray-500">{xLabel}: {d.x.toLocaleString()}</div>
                  <div className="text-gray-500">{yLabel}: {d.y.toLocaleString()}</div>
                  <div className="text-gray-500">{t('compare.score')}: {d.score.toFixed(1)}</div>
                </div>
              );
            }}
          />
          <Scatter data={data} fillOpacity={0.7} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
