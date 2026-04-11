'use client';

import { useState, useRef } from 'react';
import { ConfidenceLevel } from '@/lib/types';

interface Props {
  level: ConfidenceLevel;
  sources?: string[];
  size?: 'sm' | 'md';
}

/**
 * Pigment dot colors for the three data-quality states, chosen to live
 * in the same muted palette universe as the diverging akane↔kon bar
 * colors. Replaces the Tailwind traffic-light triad (#22c55e/#eab308/
 * #9ca3af) which clashed with the bar palette after CRTKY-66. CRTKY-68.
 *
 * Exported so the legend at the bottom of the station Ratings card can
 * re-use the same hex values without drift.
 */
export const CONFIDENCE_DOT_COLORS: Record<ConfidenceLevel, string> = {
  strong: '#6A8059',   // 苔色 koke-iro (moss green)
  moderate: '#C9A227', // 山吹 yamabuki (mountain-rose gold)
  estimate: '#828A8C', // 鈍色 nibi-iro (muted grey)
  editorial: '#8B6DB0', // 藤色 fuji-iro (wisteria purple)
};

// Labels describe HOW the rating was derived, so they read correctly even
// without the word "confidence" in front of them. The ConfidenceLevel type
// keys in the data pipeline stay as strong|moderate|estimate; only the
// displayed strings change. CRTKY-67.
const LEVEL_META: Record<ConfidenceLevel, { color: string; label: string; description: string }> = {
  strong: {
    color: CONFIDENCE_DOT_COLORS.strong,
    label: 'Measured',
    description: 'Direct count from 2+ verified sources',
  },
  moderate: {
    color: CONFIDENCE_DOT_COLORS.moderate,
    label: 'Partial',
    description: 'Single source or aggregated fallback',
  },
  estimate: {
    color: CONFIDENCE_DOT_COLORS.estimate,
    label: 'Estimate',
    description: 'Modeled from formula, not observed',
  },
  editorial: {
    color: CONFIDENCE_DOT_COLORS.editorial,
    label: 'Curated',
    description: 'Set by human researcher, may differ from data',
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
  ai_research: 'AI researcher',
};

export default function ConfidenceBadge({ level, sources, size = 'sm' }: Props) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleEnter = () => {
    clearTimeout(timeoutRef.current);
    // 400ms enter delay so briefly brushing the badge during scroll/pan
    // doesn't trigger a tooltip flash. Leave delay stays at 150ms so the
    // tooltip doesn't vanish mid-click.
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };
  const handleLeave = () => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

  const meta = LEVEL_META[level];
  // Shrunk from w-2/w-2.5 to w-1.5/w-2 in CRTKY-68 so the dots recede
  // visually behind the bar and number (metadata below data-ink).
  const dotSize = size === 'md' ? 'w-2 h-2' : 'w-1.5 h-1.5';
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
        style={{ backgroundColor: meta.color, opacity: 0.9 }}
        aria-label={`Confidence: ${meta.label}`}
      />
      {show && (
        <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 z-50 w-56 px-2.5 py-1.5 text-xs text-white bg-gray-800 rounded-md shadow-lg leading-relaxed pointer-events-none">
          <span className="block font-semibold">
            <span className="text-gray-200">Confidence:</span> {meta.label}
          </span>
          <span className="block text-gray-300 mt-0.5">{meta.description}</span>
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
