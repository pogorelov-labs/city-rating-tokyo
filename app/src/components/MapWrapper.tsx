'use client';

import dynamic from 'next/dynamic';
import { Station } from '@/lib/types';
import MapControls from './MapControls';
import ComparePanel from './ComparePanel';
import UrlSync from './UrlSync';

const MapView = dynamic(() => import('./Map'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-gray-100 text-gray-400">
      Loading map...
    </div>
  ),
});

interface MapWrapperProps {
  stations: Station[];
  thumbnails?: Record<string, string>;
  snippets?: Record<string, string>;
}

export default function MapWrapper({ stations, thumbnails, snippets }: MapWrapperProps) {
  return (
    <div className="relative h-full w-full">
      <MapView stations={stations} thumbnails={thumbnails} snippets={snippets} />
      <MapControls />
      <ComparePanel stations={stations} />
      <UrlSync />
    </div>
  );
}
