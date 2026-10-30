'use client';

import RentNote from '@/components/bangkok/RentNote';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation } from '@/lib/types';
import { useAppStore, useCityState, useCityActions } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { formatRentShort } from '@/lib/cities';
import { useIsTouch } from '@/lib/use-is-touch';
import { stationDisplayName, stationPrimaryName } from '@/lib/station-name';
import { areaKind } from '@/lib/area-key';
import { calculateWeightedScore } from '@/lib/scoring';
import { AreaCardActions, AreaCardMeta } from '@/components/area-card';
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
 * State machine (one `raised` flag, set only from rAF / transitionend / timer
 * callbacks; `open` and `visible` are derived from it):
 *   - null → non-null: mounts offscreen → double-rAF → raised, slide up
 *   - switching stations (non-null → different non-null): stays open, content swaps
 *   - non-null → null: card unmounts at once; `raised` resets during render
 *   - while isFlying: slides down, display:none after transitionend; it slides
 *     back up after flyTo lands
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

  const city = useCity();
  const selectedStation = useCityState((s) => s.selectedStation);
  const isFlying = useAppStore((s) => s.isFlying);
  const compareStations = useCityState((s) => s.compareStations);
  const { setSelectedStation, addCompareStation, removeCompareStation } = useCityActions();
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
  // Tokyo snippets stay RU-only (legacy gate); Bangkok descriptions were
  // written natively in EN/JA/RU, so they show in every locale.
  const snippet = station && (city.unit === 'district' || locale === 'ru') ? snippets[station.slug] : undefined;
  const isCompared = station ? compareStations.includes(station.slug) : false;

  // Visibility state machine — same two phases as MobileDrawer, but driven by
  // selectedStation + isFlying instead of button handlers.
  const [raised, setRaised] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // No station → the card unmounts (early return below), so the next one must
  // slide up from the bottom again. Reset during render, not in an effect: an
  // effect would commit the stale flag first and then render a second time.
  if (!station && raised) setRaised(false);

  // A station is showable when: it exists AND we are not mid-flight.
  const showable = station !== null && !isFlying;
  const open = showable && raised;
  // Still displayed while sliding down; display:none once fully lowered.
  const visible = showable || raised;

  // Phase 1: mounted offscreen (visible, not open). Phase 2, two frames later
  // so the offscreen position has been laid out: slide up.
  useEffect(() => {
    if (!showable) return;
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => setRaised(true));
    });
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [showable]);

  // After slide-down completes, hide (display:none) to avoid Safari 26
  // Liquid Glass toolbar tinting. Fallback timer handles missed transitionend.
  useEffect(() => {
    if (showable || !raised) return;
    const el = cardRef.current;
    const onEnd = (e: TransitionEvent) => {
      if (e.target !== el) return;
      setRaised(false);
    };
    el?.addEventListener('transitionend', onEnd);
    const timer = setTimeout(() => setRaised(false), 300);
    return () => {
      el?.removeEventListener('transitionend', onEnd);
      clearTimeout(timer);
    };
  }, [showable, raised]);

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
  // Bangkok keys are typed: `st.<id>` is a station area, a bare slug a district.
  const isStationArea = city.unit === 'district' && areaKind(station.slug) === 'station';
  const parentDistrict = isStationArea && station.district ? stations.find((s) => s.slug === station.district) : undefined;

  return (
    <div
      ref={cardRef}
      // Reserve a right-hand column for map controls and keep the card inside the map workspace.
      // Compare and filter panels still stack above the card and controls.
      className={`absolute bottom-0 left-3 right-16 md:max-w-96 max-h-[min(60%,calc(100%-10rem))] md:max-h-[min(60%,calc(100%-7rem))] overflow-y-auto z-[1000] bg-white rounded-xl shadow-2xl border border-gray-200 transition-transform duration-200 ease-out ${
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
          <AreaCardMeta primary={names.primary} secondary={names.secondary} score={score} camera={station.hasLiveCamera} variant="touch" />
          <div className="text-xs text-gray-500 mt-1">
            {isStationArea
              ? <>{t('filter.lines', { count: station.line_count })}{parentDistrict && <> · {stationPrimaryName(parentDistrict, locale)}</>}</>
              : city.unit === 'district' && station.station_count !== undefined
              ? station.station_count > 0
                ? <>{t('filter.stations', { count: station.station_count })} · {t('filter.lines', { count: station.line_count })}</>
                : t('map.noRailInDistrict')
              : t('filter.lines', { count: station.line_count })}
            {station.rent_1k ? <> · ~{formatRentShort(city.id, station.rent_1k)}/mo</> : null}
            {city.id === 'bangkok' && station.rent_provenance && <RentNote rent={station.rent_provenance} compact />}
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
          aria-label={t(city.unit === 'district' && !isStationArea ? 'map.closeCardDistrict' : 'map.closeCard')}
          className="shrink-0 -mr-1 -mt-1 p-2 text-gray-400 active:text-gray-600 active:bg-gray-100 rounded-lg"
          style={{ minWidth: 36, minHeight: 36 }}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Actions — 44px WCAG pill buttons */}
      <AreaCardActions city={city.id} slug={station.slug} isCompared={isCompared} compareFull={compareDisabled}
        onCompare={handleCompareToggle} onUncompare={handleCompareToggle} touch />
    </div>
  );
}
