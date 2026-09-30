'use client';

import dynamic from 'next/dynamic';
import { StationRatings } from '@/lib/types';

const StationRadarChart = dynamic(() => import('./RadarChart'), {
  ssr: false,
  loading: () => (
    <div className="h-[300px] flex items-center justify-center text-gray-300">
      Loading chart...
    </div>
  ),
});

export default function RadarChartWrapper({
  ratings,
  medians,
  medianLabelKey,
  areaLabelKey,
}: {
  ratings: StationRatings;
  medians?: Record<keyof StationRatings, number>;
  medianLabelKey?: string;
  areaLabelKey?: string;
}) {
  return (
    <StationRadarChart ratings={ratings} medians={medians} medianLabelKey={medianLabelKey} areaLabelKey={areaLabelKey} />
  );
}
