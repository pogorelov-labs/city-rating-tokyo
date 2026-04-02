'use client';

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts';
import { StationRatings, RATING_LABELS } from '@/lib/types';

interface Props {
  ratings: StationRatings;
}

export default function StationRadarChart({ ratings }: Props) {
  const data = (Object.keys(ratings) as (keyof StationRatings)[]).map(
    (key) => ({
      category: RATING_LABELS[key].replace(' & ', '\n& '),
      value: ratings[key],
      fullMark: 10,
    })
  );

  return (
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
        <Radar
          name="Rating"
          dataKey="value"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.2}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
