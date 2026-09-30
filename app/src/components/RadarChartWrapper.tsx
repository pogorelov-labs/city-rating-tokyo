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
  medianLabel,
  areaLabel,
}: {
  ratings: StationRatings;
  medians?: Record<keyof StationRatings, number>;
  medianLabel?: string;
  areaLabel?: string;
}) {
  return <StationRadarChart ratings={ratings} medians={medians} medianLabel={medianLabel} areaLabel={areaLabel} />;
}
