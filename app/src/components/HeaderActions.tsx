'use client';

import { useState } from 'react';
import { Station } from '@/lib/types';
import ScatterPlotExplorer from './ScatterPlotExplorer';

interface Props {
  stations: Station[];
}

export default function HeaderActions({ stations }: Props) {
  const [scatterOpen, setScatterOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setScatterOpen(true)}
        className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
      >
        Scatter Plot
      </button>

      {scatterOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setScatterOpen(false)}
          />
          <div className="relative bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Scatter Plot Explorer</h2>
              <button
                onClick={() => setScatterOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ScatterPlotExplorer stations={stations} />
          </div>
        </div>
      )}
    </>
  );
}
