'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { MapStation } from '@/lib/types';
import FilterPanel from './FilterPanel';

interface MobileDrawerProps {
  stations: MapStation[];
}

export default function MobileDrawer({ stations }: MobileDrawerProps) {
  const t = useTranslations('drawer');
  // Same model as MobileStationCard: `wantOpen` is set only by the handlers,
  // `raised` only from rAF / transitionend / timer callbacks, and `open` /
  // `visible` are derived from the two.
  const [wantOpen, setWantOpen] = useState(false);
  const [raised, setRaised] = useState(false);
  const open = wantOpen && raised;
  // Drawer is display:none when fully closed to prevent Safari 26 Liquid Glass
  // tinting from scanning its fixed white background behind the toolbar.
  const visible = wantOpen || raised;
  const drawerRef = useRef<HTMLDivElement>(null);

  const handleOpen = useCallback(() => setWantOpen(true), []);
  const handleClose = useCallback(() => setWantOpen(false), []);

  // Phase 1 (wanted, not raised): shown with translate-y-full (offscreen).
  // Phase 2, two frames later so that position has been laid out: slide up.
  useEffect(() => {
    if (!wantOpen) return;
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => setRaised(true));
    });
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [wantOpen]);

  // Hide after the 300ms slide-down. Armed only while closing, never in phase 1:
  // a fallback armed there can fire before a slow double rAF and leave the
  // drawer open but display:none.
  useEffect(() => {
    if (!wantOpen && raised) {
      // The drawer div is always rendered (only display toggles), so the ref is
      // set by now. If it ever isn't, the fallback timer below still hides it.
      const el = drawerRef.current;
      const onEnd = (e: TransitionEvent) => {
        // Ignore bubbled transitionend from children (e.g. button transition-colors)
        if (e.target !== el) return;
        setRaised(false);
      };
      el?.addEventListener('transitionend', onEnd);
      // Fallback in case transitionend doesn't fire (e.g. display:none race)
      const timer = setTimeout(() => setRaised(false), 350);
      return () => { el?.removeEventListener('transitionend', onEnd); clearTimeout(timer); };
    }
  }, [wantOpen, raised]);

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={handleOpen}
        data-umami-event="open-mobile-filters"
        className="md:hidden fixed left-4 z-[1000] bg-white shadow-lg rounded-full px-4 py-2.5 text-sm font-medium border border-gray-200 flex items-center gap-2 active:scale-95 transition-transform"
        style={{ bottom: 'max(16px, env(safe-area-inset-bottom, 16px))' }}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
        </svg>
        {t('filters')}
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-[1001] transition-opacity"
          onClick={handleClose}
        />
      )}

      {/* Drawer — display:none when fully closed so Safari 26 Liquid Glass
          toolbar tinting doesn't scan this fixed white surface. */}
      <div
        ref={drawerRef}
        className={`md:hidden fixed bottom-0 left-0 right-0 z-[1002] bg-white rounded-t-2xl shadow-2xl transition-transform duration-300 ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ maxHeight: '80vh', display: visible ? undefined : 'none' }}
      >
        {/* Handle */}
        <div className="flex justify-center pt-2 pb-1">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Close button */}
        <div className="flex justify-between items-center px-4 pb-2">
          <span className="font-bold text-base">{t('filtersAndRanking')}</span>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto" style={{ maxHeight: 'calc(80vh - 60px)', paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
          <FilterPanel stations={stations} />
        </div>
      </div>
    </>
  );
}
