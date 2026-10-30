'use client';

import CompactAreaCard from '@/components/area/CompactAreaCard';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation } from '@/lib/types';
import { useAppStore, useCityState, useCityActions } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { useIsTouch } from '@/lib/use-is-touch';
import { stationDisplayName } from '@/lib/station-name';
import { areaKind } from '@/lib/area-key';
import { calculateWeightedScore } from '@/lib/scoring';
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
  // The server supplies a snippet in the current locale for either city.
  const snippet = station ? snippets[station.slug] : undefined;
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

  return (
    <div
      ref={cardRef}
      // Reserve a right-hand column for the shared Leaflet zoom controls.
      // Compare and filter panels still stack above the card and controls.
      className={`md:hidden fixed bottom-0 left-3 right-16 z-[1000] bg-white rounded-xl shadow-2xl border border-gray-200 transition-transform duration-200 ease-out ${
        open ? 'translate-y-0' : 'translate-y-full'
      }`}
      style={{
        display: visible ? undefined : 'none',
        marginBottom: 'max(12px, env(safe-area-inset-bottom, 12px))',
      }}
      role="dialog"
      aria-label={names.primary}
    >
      <CompactAreaCard key={station.slug} area={station} city={city.id} score={score} weights={weights}
        thumbnail={thumbEntry} snippet={snippet} variant="mobile" isCompared={isCompared} compareFull={compareDisabled}
        onCompare={handleCompareToggle} onUncompare={handleCompareToggle} onClose={handleClose}
        closeLabel={t(city.unit === 'district' && !isStationArea ? 'map.closeCardDistrict' : 'map.closeCard')} />
    </div>
  );
}
