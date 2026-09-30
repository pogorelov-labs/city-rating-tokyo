'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { MapStation } from '@/lib/types';
import { useCityActions } from '@/lib/store';
import { useCity } from '@/lib/city-context';
import { stationDisplayName, matchArea } from '@/lib/station-name';
import type { Locale } from '@/i18n/routing';

interface Props {
  stations: MapStation[];
}

export default function MobileSearchPill({ stations }: Props) {
  const t = useTranslations();
  const locale = useLocale() as Locale;
  const city = useCity();
  const isDistrict = city.unit === 'district';
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const { setSelectedStation, setHoveredStation } = useCityActions();
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const searchResults = useMemo(() => {
    if (!search || search.length < 2) return [];
    const hits: { station: MapStation; alias?: string }[] = [];
    for (const s of stations) {
      const m = matchArea(s, search);
      if (m.matched) hits.push({ station: s, alias: m.alias });
      if (hits.length >= 6) break;
    }
    return hits;
  }, [stations, search]);

  // Close dropdown on tap outside
  useEffect(() => {
    if (!open) return;
    const handle = (e: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', handle);
    return () => document.removeEventListener('pointerdown', handle);
  }, [open]);

  const handleSelect = (slug: string) => {
    setSelectedStation(slug);
    setHoveredStation(null);
    setSearch('');
    setOpen(false);
    inputRef.current?.blur();
  };

  return (
    <div
      ref={containerRef}
      className={`md:hidden absolute top-2 left-3 z-[999] ${isDistrict ? 'right-40' : 'right-24'}`}
    >
      {/* Pill */}
      <div className="flex items-center bg-white rounded-xl shadow-lg border border-gray-200 px-3 py-2 gap-2">
        <svg
          className="w-4 h-4 text-gray-400 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        <input
          ref={inputRef}
          type="search"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          spellCheck={false}
          placeholder={t(isDistrict ? 'filter.searchPlaceholderDistrictShort' : 'filter.searchPlaceholder')}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="flex-1 min-w-0 text-base bg-transparent outline-none placeholder:text-gray-400"
        />
        {search && (
          <button
            onClick={() => {
              setSearch('');
              setOpen(false);
            }}
            aria-label={t('filter.clearSearch')}
            className="text-gray-400 hover:text-gray-600 shrink-0"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {open && searchResults.length > 0 && (
        <div className="mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          {searchResults.map(({ station: s, alias }) => (
            <button
              key={s.slug}
              onClick={() => handleSelect(s.slug)}
              data-umami-event="search-select"
              data-umami-event-station={s.slug}
              className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 active:bg-gray-100 flex items-center justify-between gap-2 border-b border-gray-50 last:border-0"
            >
              <span className="min-w-0 truncate">
                {alias && <span className="text-gray-500">{alias} → </span>}
                <span className="font-medium">{stationDisplayName(s, locale).primary}</span>
                <span className="text-gray-400 ml-1.5 text-xs">{stationDisplayName(s, locale).secondary}</span>
              </span>
              <span className="text-xs text-gray-400 shrink-0">
                {isDistrict
                  ? t('filter.stations', { count: s.station_count ?? 0 })
                  : t('filter.lines', { count: s.line_count })}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
