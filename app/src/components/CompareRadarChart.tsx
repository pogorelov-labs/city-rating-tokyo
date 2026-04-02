'use client';

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts';
import { StationRatings, RATING_LABELS, WeightConfig } from '@/lib/types';

const COLORS = ['#3b82f6', '#f97316', '#8b5cf6'];

interface Series {
  label: string;
  ratings: StationRatings;
}

interface Props {
  series: Series[];
}

export default function CompareRadarChart({ series }: Props) {
  const keys = Object.keys(RATING_LABELS) as (keyof WeightConfig)[];

  const data = keys.map((key) => {
    const point: Record<string, string | number> = { category: RATING_LABELS[key] };
    series.forEach((s, i) => {
      point[`s${i}`] = s.ratings[key];
    });
    return point;
  });

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis dataKey="category" tick={{ fontSize: 10 }} />
          <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 9 }} />
          {series.map((s, i) => (
            <Radar
              key={i}
              name={s.label}
              dataKey={`s${i}`}
              stroke={COLORS[i]}
              fill={COLORS[i]}
              fillOpacity={0.12}
              strokeWidth={2}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
      <div className="flex items-center justify-center gap-4 mt-1">
        {series.map((s, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} />
            <span>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
