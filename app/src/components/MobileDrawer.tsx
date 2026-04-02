'use client';

import { useState } from 'react';
import { Station } from '@/lib/types';
import FilterPanel from './FilterPanel';

interface MobileDrawerProps {
  stations: Station[];
}

export default function MobileDrawer({ stations }: MobileDrawerProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen(true)}
        className="md:hidden fixed bottom-4 left-4 z-[1000] bg-white shadow-lg rounded-full px-4 py-2.5 text-sm font-medium border border-gray-200 flex items-center gap-2 active:scale-95 transition-transform"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
        </svg>
        Filters
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-[1001] transition-opacity"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={`md:hidden fixed bottom-0 left-0 right-0 z-[1002] bg-white rounded-t-2xl shadow-2xl transition-transform duration-300 ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ maxHeight: '80vh' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-2 pb-1">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Close button */}
        <div className="flex justify-between items-center px-4 pb-2">
          <span className="font-bold text-base">Filters & Ranking</span>
          <button
            onClick={() => setOpen(false)}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(80vh - 60px)' }}>
          <FilterPanel stations={stations} />
        </div>
      </div>
    </>
  );
}
