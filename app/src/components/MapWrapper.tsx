'use client';

import dynamic from 'next/dynamic';
import { MapStation } from '@/lib/types';
import { useCityState } from '@/lib/store';
import { useCity } from '@/lib/city-context';
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

// Bangkok: district polygons + rail overlay. A separate chunk, so the Tokyo
// homepage never downloads the district geometry (and vice versa).
const DistrictMapView = dynamic(() => import('./DistrictMap'), {
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

// MobileStationCard is touch-only; lazy-load so desktop doesn't ship it.
const MobileStationCard = dynamic(() => import('./MobileStationCard'), {
  ssr: false,
});

interface MapWrapperProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

export default function MapWrapper({ stations, thumbnails, snippets }: MapWrapperProps) {
  const city = useCity();
  // Gate ComparePanel behind the store so the recharts chunk is never
  // downloaded unless the user actively compares something.
  const hasCompareTarget = useCityState((s) => s.compareStations.length >= 2);
  const View = city.unit === 'district' ? DistrictMapView : MapView;

  return (
    <div className="relative h-full w-full">
      <View stations={stations} thumbnails={thumbnails} snippets={snippets} />
      <MapControls />
      {hasCompareTarget && <ComparePanel stations={stations} />}
      <MobileStationCard stations={stations} thumbnails={thumbnails} snippets={snippets} />
      <UrlSync />
    </div>
  );
}
