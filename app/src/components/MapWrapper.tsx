'use client';

import dynamic from 'next/dynamic';
import { MapStation } from '@/lib/types';

const MapView = dynamic(() => import('./Map'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-gray-100 text-gray-400">
      Loading map...
    </div>
  ),
});

interface MapWrapperProps {
  stations: MapStation[];
  thumbnails?: Record<string, string>;
  snippets?: Record<string, string>;
}

export default function MapWrapper({ stations, thumbnails, snippets }: MapWrapperProps) {
  return <MapView stations={stations} thumbnails={thumbnails} snippets={snippets} />;
}
