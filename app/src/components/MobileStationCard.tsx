'use client';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation } from '@/lib/types';
import { useAppStore } from '@/lib/store';
import { useIsTouch } from '@/lib/use-is-touch';
import { stationDisplayName } from '@/lib/station-name';
import { calculateWeightedScore } from '@/lib/scoring';
import { Link } from '@/i18n/navigation';
import type { Locale } from '@/i18n/routing';

interface MobileStationCardProps {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
}

/**
 * Bottom-docked station card for touch devices.
 *
 * Replaces the Leaflet Popup on mobile (which clips off-screen, has tiny tap
 * targets, and can't reliably position above a marker near the viewport edge).
 * Follows the industry-standard pattern used by Google Maps, Apple Maps, Airbnb.
 *
 * State machine:
 *   - null → non-null: setVisible(true) → double-rAF → setOpen(true), slide up
 *   - switching stations (non-null → different non-null): stays open, content swaps
 *   - non-null → null: setOpen(false), transitionend → setVisible(false), slide down
 *   - while isFlying: card stays hidden; it appears after flyTo lands
 *
 * `display: none` when fully hidden avoids Safari 26 Liquid Glass toolbar
 * tinting scanning the card's white background behind the toolbar.
 */
export default function MobileStationCard({
  stations,
  thumbnails = {},
  snippets = {},
}: MobileStationCardProps) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const isTouch = useIsTouch();

  const selectedStation = useAppStore((s) => s.selectedStation);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const isFlying = useAppStore((s) => s.isFlying);
  const compareStations = useAppStore((s) => s.compareStations);
  const addCompareStation = useAppStore((s) => s.addCompareStation);
  const removeCompareStation = useAppStore((s) => s.removeCompareStation);
  const weights = useAppStore((s) => s.weights);

  const station = useMemo(
    () => stations.find((s) => s.slug === selectedStation) ?? null,
    [stations, selectedStation],
  );

  const score = useMemo(
    () => (station?.ratings ? calculateWeightedScore(station.ratings, weights) : null),
    [station, weights],
  );

  const thumbEntry = station ? thumbnails[station.slug] : undefined;
  const snippet = station && locale === 'ru' ? snippets[station.slug] : undefined;
  const isCompared = station ? compareStations.includes(station.slug) : false;

  // Visibility state machine — mirrors MobileDrawer pattern.
  const [visible, setVisible] = useState(false);
  const [open, setOpen] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Drive the slide-up animation based on selectedStation + isFlying.
  // A station is showable when: it exists AND we are not mid-flight.
  const showable = station !== null && !isFlying;

  useEffect(() => {
    if (showable) {
      // Phase 1: mount offscreen, Phase 2: slide up.
      setVisible(true);
      const raf1 = requestAnimationFrame(() => {
        const raf2 = requestAnimationFrame(() => setOpen(true));
        return () => cancelAnimationFrame(raf2);
      });
      return () => cancelAnimationFrame(raf1);
    } else {
      setOpen(false);
    }
  }, [showable]);

  // After slide-down completes, unmount (display:none) to avoid Safari 26
  // Liquid Glass toolbar tinting. Fallback timer handles missed transitionend.
  useEffect(() => {
    if (!open && visible) {
      const el = cardRef.current;
      if (!el) {
        setVisible(false);
        return;
      }
      const onEnd = (e: TransitionEvent) => {
        if (e.target !== el) return;
        setVisible(false);
      };
      el.addEventListener('transitionend', onEnd);
      const timer = setTimeout(() => setVisible(false), 300);
      return () => {
        el.removeEventListener('transitionend', onEnd);
        clearTimeout(timer);
      };
    }
  }, [open, visible]);

  const handleClose = useCallback(() => {
    setSelectedStation(null);
  }, [setSelectedStation]);

  const handleCompareToggle = useCallback(() => {
    if (!station) return;
    if (isCompared) {
      removeCompareStation(station.slug);
    } else {
      addCompareStation(station.slug);
    }
  }, [station, isCompared, addCompareStation, removeCompareStation]);

  // Desktop or no station to show → render nothing.
  if (!isTouch) return null;
  if (!station) return null;

  const names = stationDisplayName(station, locale);
  const compareDisabled = !isCompared && compareStations.length >= 3;

  return (
    <div
      ref={cardRef}
      className={`md:hidden fixed bottom-0 left-3 right-3 z-[800] bg-white rounded-xl shadow-2xl border border-gray-200 transition-transform duration-200 ease-out ${
        open ? 'translate-y-0' : 'translate-y-full'
      }`}
      style={{
        display: visible ? undefined : 'none',
        marginBottom: 'max(12px, env(safe-area-inset-bottom, 12px))',
      }}
      role="dialog"
      aria-label={names.primary}
    >
      <div className="flex items-start gap-3 p-3">
        {/* Image thumbnail (60x60 horizontal layout) */}
        <div
          className="shrink-0 overflow-hidden rounded-lg bg-gray-100"
          style={{ width: 60, height: 60 }}
        >
          {thumbEntry?.lqip && !thumbEntry?.thumb && (
            <img
              src={thumbEntry.lqip}
              alt=""
              aria-hidden
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'blur(8px)',
                transform: 'scale(1.1)',
              }}
            />
          )}
          {thumbEntry?.thumb && (
            <img
              src={thumbEntry.thumb}
              alt={names.primary}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
        </div>

        {/* Text content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2">
            <div className="min-w-0">
              <div className="font-bold text-base truncate">{names.primary}</div>
              {names.secondary && (
                <div className="text-gray-500 text-xs truncate">{names.secondary}</div>
              )}
            </div>
            {score !== null && (
              <div className="shrink-0 font-bold text-lg text-slate-800">
                {score.toFixed(1)}
              </div>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {t('filter.lines', { count: station.line_count })}
            {station.rent_1k ? <> · ~¥{(station.rent_1k / 1000).toFixed(0)}k/mo</> : null}
          </div>
          {snippet && (
            <div className="text-xs text-gray-600 mt-1.5 line-clamp-2 leading-relaxed">
              {snippet}
            </div>
          )}
        </div>

        {/* Close button */}
        <button
          onClick={handleClose}
          aria-label={t('map.closeCard')}
          className="shrink-0 -mr-1 -mt-1 p-2 text-gray-400 active:text-gray-600 active:bg-gray-100 rounded-lg"
          style={{ minWidth: 36, minHeight: 36 }}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Actions — 44px WCAG pill buttons */}
      <div className="flex items-stretch gap-2 px-3 pb-3">
        <Link
          href={`/station/${station.slug}`}
          data-umami-event="view-details"
          data-umami-event-station={station.slug}
          className="flex-1 flex items-center justify-center rounded-lg bg-blue-600 text-white text-sm font-medium active:bg-blue-700"
          style={{ minHeight: 44 }}
        >
          {t('map.viewDetails')}
        </Link>
        <button
          onClick={handleCompareToggle}
          disabled={compareDisabled}
          className={`flex-1 flex items-center justify-center rounded-lg text-sm font-medium border active:bg-gray-100 disabled:opacity-40 ${
            isCompared
              ? 'text-red-600 border-red-200 bg-red-50'
              : 'text-purple-700 border-purple-200 bg-purple-50'
          }`}
          style={{ minHeight: 44 }}
        >
          {isCompared ? t('map.removeCompare') : t('map.compare')}
        </button>
      </div>
    </div>
  );
}
