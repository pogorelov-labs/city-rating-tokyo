'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { ConfidenceLevel } from '@/lib/types';
import { useIsTouch } from '@/lib/use-is-touch';

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

/**
 * Inline SVG icon for a confidence level. Shape encodes the level so the
 * system is readable without color alone:
 *
 *   strong   → bullseye (filled dot + outer ring) — maximum visual weight
 *   moderate → solid filled circle — medium weight
 *   estimate → open dashed circle (stroke only) — lightest
 *   editorial → filled diamond (菱形 hishigata) — different shape = different provenance
 *
 * All shapes share a 14×14 viewBox; `size` controls the rendered px.
 */
export function ConfidenceIcon({ level, size = 12 }: { level: ConfidenceLevel; size?: number }) {
  const color = CONFIDENCE_DOT_COLORS[level];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 14 14"
      className="shrink-0 inline-block"
      aria-hidden
    >
      {level === 'strong' && (
        <>
          <circle cx="7" cy="7" r="5.5" fill="none" stroke={color} strokeWidth="1.5" opacity="0.9" />
          <circle cx="7" cy="7" r="2.5" fill={color} opacity="0.9" />
        </>
      )}
      {level === 'moderate' && (
        <circle cx="7" cy="7" r="4" fill={color} opacity="0.9" />
      )}
      {level === 'estimate' && (
        <circle cx="7" cy="7" r="4.5" fill="none" stroke={color} strokeWidth="1.5" strokeDasharray="2.5 2" opacity="0.9" />
      )}
      {level === 'editorial' && (
        <rect x="3" y="3" width="8" height="8" rx="1" fill={color} opacity="0.9" transform="rotate(45 7 7)" />
      )}
    </svg>
  );
}

export default function ConfidenceBadge({ level, sources, size = 'sm' }: Props) {
  const t = useTranslations();
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLSpanElement>(null);
  const isTouch = useIsTouch();

  // Desktop: hover handlers
  const handleEnter = () => {
    if (isTouch) return;
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };
  const handleLeave = () => {
    if (isTouch) return;
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

  // Touch: tap to toggle
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (!isTouch) return;
      e.preventDefault();
      e.stopPropagation();
      setShow((prev) => !prev);
    },
    [isTouch],
  );

  // Touch: close on tap outside
  useEffect(() => {
    if (!isTouch || !show) return;
    const handleOutside = (e: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShow(false);
      }
    };
    document.addEventListener('pointerdown', handleOutside);
    return () => document.removeEventListener('pointerdown', handleOutside);
  }, [isTouch, show]);

  const label = t(`confidence.${level}.label`);
  const description = t(`confidence.${level}.description`);
  const iconSize = size === 'md' ? 14 : 12;
  // On touch, tap target must be at least 44×44px — use padding
  const touchPad = isTouch ? 'p-3 -m-3' : '';
  const sourceList = sources && sources.length > 0
    ? sources.map((s) => t.has(`sources.${s}`) ? t(`sources.${s}`) : s).join(', ')
    : null;

  return (
    <span
      ref={containerRef}
      className={`relative inline-flex items-center shrink-0 cursor-help ${touchPad}`}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={handleClick}
      aria-label={`Confidence: ${label}`}
    >
      <ConfidenceIcon level={level} size={iconSize} />
      {show && (
        <span className="absolute left-0 bottom-full mb-1.5 z-50 w-56 px-2.5 py-1.5 text-xs text-white bg-gray-800 rounded-md shadow-lg leading-relaxed pointer-events-none">
          <span className="block font-semibold">
            <span className="text-gray-200">Confidence:</span> {label}
          </span>
          <span className="block text-gray-300 mt-0.5">{description}</span>
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
