'use client';

import { useState, useRef } from 'react';
import { ConfidenceLevel } from '@/lib/types';

interface Props {
  level: ConfidenceLevel;
  sources?: string[];
  size?: 'sm' | 'md';
}

const LEVEL_META: Record<ConfidenceLevel, { color: string; label: string; description: string }> = {
  strong: {
    color: '#22c55e',
    label: 'Strong',
    description: 'Based on 2+ verified data sources',
  },
  moderate: {
    color: '#eab308',
    label: 'Moderate',
    description: 'Based on 1 source or ward-level fallback',
  },
  estimate: {
    color: '#9ca3af',
    label: 'Estimate',
    description: 'Computed from formula — no direct data',
  },
};

const SOURCE_LABELS: Record<string, string> = {
  hotpepper: 'HotPepper',
  hotpepper_midnight: 'HotPepper (late-night)',
  osm: 'OpenStreetMap',
  osm_karaoke: 'OSM (karaoke)',
  osm_cultural: 'OSM (cultural)',
  osm_pedestrian: 'OSM (pedestrian)',
  line_count: 'Train lines',
  mlit_s12: 'MLIT passengers',
  suumo: 'Suumo',
  ward_average: 'Ward average',
  distance_estimate: 'Distance estimate',
  keishicho_arcgis: 'Tokyo Police',
  ward_crime_stats: 'Ward crime stats',
  prefecture_average: 'Prefecture average',
  composite_fallback: 'Composite fallback',
  hp_proxy: 'HotPepper proxy',
};

export default function ConfidenceBadge({ level, sources, size = 'sm' }: Props) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleEnter = () => {
    clearTimeout(timeoutRef.current);
    setShow(true);
  };
  const handleLeave = () => {
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

  const meta = LEVEL_META[level];
  const dotSize = size === 'md' ? 'w-2.5 h-2.5' : 'w-2 h-2';
  const sourceList = sources && sources.length > 0
    ? sources.map((s) => SOURCE_LABELS[s] || s).join(', ')
    : null;

  return (
    <span
      className="relative inline-flex items-center shrink-0"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <span
        className={`${dotSize} rounded-full cursor-help inline-block`}
        style={{ backgroundColor: meta.color }}
        aria-label={`Confidence: ${meta.label}`}
      />
      {show && (
        <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 z-50 w-56 px-2.5 py-1.5 text-xs text-white bg-gray-800 rounded-md shadow-lg leading-relaxed pointer-events-none">
          <span className="font-semibold">{meta.label}</span>
          <span className="block text-gray-300">{meta.description}</span>
          {sourceList && (
            <span className="block mt-1 text-gray-300">
              <span className="text-gray-400">Sources: </span>
              {sourceList}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
