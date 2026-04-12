'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import { MapStation } from '@/lib/types';
import { useAppStore } from '@/lib/store';

interface Props {
  stations: MapStation[];
}

export default function MobileSearchPill({ stations }: Props) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const setHoveredStation = useAppStore((s) => s.setHoveredStation);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const searchResults = useMemo(() => {
    if (!search || search.length < 2) return [];
    const q = search.toLowerCase();
    return stations
      .filter(
        (s) =>
          s.name_en.toLowerCase().includes(q) ||
          s.name_jp.includes(search),
      )
      .slice(0, 6);
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
      className="md:hidden absolute top-2 left-3 right-3 z-[999]"
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
          placeholder="Search station..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="flex-1 text-sm bg-transparent outline-none placeholder:text-gray-400"
        />
        {search && (
          <button
            onClick={() => {
              setSearch('');
              setOpen(false);
            }}
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
          {searchResults.map((s) => (
            <button
              key={s.slug}
              onClick={() => handleSelect(s.slug)}
              data-umami-event="search-select"
              data-umami-event-station={s.slug}
              className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 active:bg-gray-100 flex items-center justify-between border-b border-gray-50 last:border-0"
            >
              <span>
                <span className="font-medium">{s.name_en}</span>
                <span className="text-gray-400 ml-1.5 text-xs">{s.name_jp}</span>
              </span>
              <span className="text-xs text-gray-400">{s.line_count} lines</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
