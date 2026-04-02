'use client';

import { useState, useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Station, SCATTER_AXIS_OPTIONS } from '@/lib/types';
import { useAppStore } from '@/lib/store';
import { calculateWeightedScore, scoreToColor, getAxisValue } from '@/lib/scoring';

interface Props {
  stations: Station[];
}

export default function ScatterPlotExplorer({ stations }: Props) {
  const weights = useAppStore((s) => s.weights);
  const [xAxis, setXAxis] = useState('rent');
  const [yAxis, setYAxis] = useState('food');

  const xLabel = SCATTER_AXIS_OPTIONS.find((o) => o.key === xAxis)?.label ?? xAxis;
  const yLabel = SCATTER_AXIS_OPTIONS.find((o) => o.key === yAxis)?.label ?? yAxis;

  const data = useMemo(() => {
    return stations
      .filter((s) => s.ratings)
      .map((s) => {
        const x = getAxisValue(s, xAxis);
        const y = getAxisValue(s, yAxis);
        if (x === null || y === null) return null;
        const score = calculateWeightedScore(s.ratings!, weights);
        return { name: s.name_en, x, y, score, fill: scoreToColor(score) };
      })
      .filter(Boolean) as { name: string; x: number; y: number; score: number; fill: string }[];
  }, [stations, weights, xAxis, yAxis]);

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
            {SCATTER_AXIS_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
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
            {SCATTER_AXIS_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
            ))}
          </select>
        </label>
        <span className="text-xs text-gray-400">{data.length} stations</span>
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
                  <div className="text-gray-500">Score: {d.score.toFixed(1)}</div>
                </div>
              );
            }}
          />
          <Scatter data={data} fill="#3b82f6">
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} fillOpacity={0.7} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
