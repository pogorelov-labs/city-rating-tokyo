'use client';

import { useState, useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { RATING_LABELS, RATING_TOOLTIPS, PRESET_PROFILES, WeightConfig, Station } from '@/lib/types';
import { calculateWeightedScore, scoreToColor } from '@/lib/scoring';

interface FilterPanelProps {
  stations: Station[];
}

export default function FilterPanel({ stations }: FilterPanelProps) {
  const weights = useAppStore((s) => s.weights);
  const setWeight = useAppStore((s) => s.setWeight);
  const setAllWeights = useAppStore((s) => s.setAllWeights);
  const resetWeights = useAppStore((s) => s.resetWeights);
  const setSelectedStation = useAppStore((s) => s.setSelectedStation);
  const [search, setSearch] = useState('');
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const ranked = useMemo(() => {
    return stations
      .filter((s) => s.ratings !== null)
      .map((s) => ({
        ...s,
        score: calculateWeightedScore(s.ratings!, weights),
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 15);
  }, [stations, weights]);

  const searchResults = useMemo(() => {
    if (!search || search.length < 2) return [];
    const q = search.toLowerCase();
    return stations
      .filter(
        (s) =>
          s.name_en.toLowerCase().includes(q) ||
          s.name_jp.includes(search)
      )
      .slice(0, 8);
  }, [stations, search]);

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      {/* Search */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search station..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
        {searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 overflow-hidden">
            {searchResults.map((s) => (
              <button
                key={s.slug}
                onClick={() => {
                  setSelectedStation(s.slug);
                  setSearch('');
                }}
                data-umami-event="search-select"
                data-umami-event-station={s.slug}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between border-b border-gray-50 last:border-0"
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

      {/* Presets */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Quick Profiles</h2>
        <div className="flex flex-wrap gap-1.5">
          {PRESET_PROFILES.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setAllWeights(p.weights);
                setActivePreset(p.id);
              }}
              className={`text-xs px-2.5 py-1.5 rounded-full border cursor-pointer transition-colors ${
                activePreset === p.id
                  ? 'bg-blue-100 border-blue-400 text-blue-700'
                  : 'bg-gray-50 border-gray-200 hover:bg-gray-100 text-gray-600'
              }`}
            >
              {p.icon} {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Weights */}
      <div>
        <h2 className="text-lg font-bold mb-1">Weights</h2>
        <p className="text-xs text-gray-500 mb-3">
          Adjust what matters most to you
        </p>
        <div className="space-y-2">
          {(Object.keys(RATING_LABELS) as (keyof WeightConfig)[]).map(
            (key) => (
              <div key={key}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span title={RATING_TOOLTIPS[key]}>{RATING_LABELS[key]}</span>
                  <span className="text-gray-400 tabular-nums">
                    {weights[key]}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={50}
                  value={weights[key]}
                  onChange={(e) => { setWeight(key, Number(e.target.value)); setActivePreset(null); }}
                  className="w-full h-1.5 accent-blue-600 cursor-pointer"
                />
              </div>
            )
          )}
        </div>
        <button
          onClick={() => { resetWeights(); setActivePreset(null); }}
          data-umami-event="reset-weights"
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          Reset to defaults
        </button>
      </div>

      <hr className="border-gray-200" />

      {/* Top Ranked */}
      <div>
        <h2 className="text-lg font-bold mb-2">Top Ranked</h2>
        {ranked.length === 0 ? (
          <p className="text-sm text-gray-400">No rated stations yet</p>
        ) : (
          <ol className="space-y-1">
            {ranked.map((s, i) => (
              <li key={s.slug}>
                <button
                  onClick={() => setSelectedStation(s.slug)}
                  data-umami-event="ranked-select"
                  data-umami-event-station={s.slug}
                  className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-100 transition-colors"
                >
                  <span className="text-xs text-gray-400 w-5 tabular-nums">
                    {i + 1}.
                  </span>
                  <span className="flex-1 text-sm font-medium truncate">
                    {s.name_en}
                  </span>
                  <span
                    className="text-sm font-bold tabular-nums"
                    style={{ color: scoreToColor(s.score) }}
                  >
                    {s.score.toFixed(1)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>

      <hr className="border-gray-200" />

      <div className="text-xs text-gray-400">
        <p>{stations.length} stations mapped</p>
        <p>{stations.filter((s) => s.ratings).length} with ratings</p>
      </div>
    </div>
  );
}
