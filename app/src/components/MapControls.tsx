'use client';

import { useAppStore } from '@/lib/store';
import { RATING_LABELS, WeightConfig } from '@/lib/types';

export default function MapControls() {
  const heatmapMode = useAppStore((s) => s.heatmapMode);
  const setHeatmapMode = useAppStore((s) => s.setHeatmapMode);
  const heatmapDimension = useAppStore((s) => s.heatmapDimension);
  const setHeatmapDimension = useAppStore((s) => s.setHeatmapDimension);

  return (
    <div className="absolute top-3 right-3 z-[1000] flex items-center gap-2">
      <button
        onClick={() => setHeatmapMode(!heatmapMode)}
        className={`text-xs px-3 py-1.5 rounded-lg border shadow-sm transition-colors ${
          heatmapMode
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
        }`}
      >
        Heatmap
      </button>
      {heatmapMode && (
        <select
          value={heatmapDimension}
          onChange={(e) => setHeatmapDimension(e.target.value)}
          className="text-xs px-2 py-1.5 rounded-lg border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="composite">Composite Score</option>
          {(Object.keys(RATING_LABELS) as (keyof WeightConfig)[]).map((key) => (
            <option key={key} value={key}>
              {RATING_LABELS[key]}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
