'use client';

import dynamic from 'next/dynamic';
import { MapStation } from '@/lib/types';
import { useAppStore } from '@/lib/store';
import MapControls from './MapControls';
import UrlSync from './UrlSync';

const MapView = dynamic(() => import('./Map'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-gray-100 text-gray-400">
      Loading map...
    </div>
  ),
});

// ComparePanel imports recharts (CompareRadarChart). Load it only when the
// user has actually queued 2+ stations for comparison.
const ComparePanel = dynamic(() => import('./ComparePanel'), {
  ssr: false,
});

interface MapWrapperProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

export default function MapWrapper({ stations, thumbnails, snippets }: MapWrapperProps) {
  // Gate ComparePanel behind the store so the recharts chunk is never
  // downloaded unless the user actively compares something.
  const hasCompareTarget = useAppStore((s) => s.compareStations.length >= 2);

  return (
    <div className="relative h-full w-full">
      <MapView stations={stations} thumbnails={thumbnails} snippets={snippets} />
      <MapControls />
      {hasCompareTarget && <ComparePanel stations={stations} />}
      <UrlSync />
    </div>
  );
}
