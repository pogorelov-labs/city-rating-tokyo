'use client';

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { StationRatings, RATING_LABELS } from '@/lib/types';
import { CITY_MEDIANS } from '@/lib/scoring';

interface Props {
  ratings: StationRatings;
}

const MEDIAN_STROKE = '#94a3b8';
const MEDIAN_FILL = '#94a3b8';
const STATION_STROKE = '#2563eb';
const STATION_FILL = '#2563eb';

export default function StationRadarChart({ ratings }: Props) {
  const keys = Object.keys(RATING_LABELS) as (keyof StationRatings)[];

  const data = keys.map((key) => ({
    category: RATING_LABELS[key].replace(' & ', '\n& '),
    station: ratings[key],
    median: CITY_MEDIANS[key],
    fullMark: 10,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis
            dataKey="category"
            tick={{ fontSize: 11, fill: '#6b7280' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 10]}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickCount={6}
          />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          {/* Draw median first so the station polygon reads on top (CRTKY-76). */}
          <Radar
            name="Tokyo median"
            dataKey="median"
            stroke={MEDIAN_STROKE}
            fill={MEDIAN_FILL}
            fillOpacity={0.1}
            strokeWidth={1.5}
            dot={false}
          />
          <Radar
            name="This station"
            dataKey="station"
            stroke={STATION_STROKE}
            fill={STATION_FILL}
            fillOpacity={0.22}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-center text-[10px] text-gray-400 leading-relaxed px-1">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: MEDIAN_STROKE, opacity: 0.85 }} />
          Typical Tokyo (median)
        </span>
        <span className="mx-2 text-gray-300">·</span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: STATION_STROKE, opacity: 0.9 }} />
          This station
        </span>
      </p>
    </div>
  );
}
