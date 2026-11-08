'use client';

import { useState, useId, useCallback, useEffect, useLayoutEffect } from 'react';
import { useTranslations } from 'next-intl';
import { MapStation } from '@/lib/types';
import FilterPanel from './FilterPanel';
import { useSheetSwipe } from './use-sheet-swipe';
import { prefersReducedMotion, REDUCED_MOTION } from '@/lib/map-motion';
import './mobile-drawer.css';

interface MobileDrawerProps {
  stations: MapStation[];
}

export default function MobileDrawer({ stations }: MobileDrawerProps) {
  const t = useTranslations('drawer');
  // Keep the dialog mounted and modal through its exit. With reduced motion
  // opening and closing both complete in the same interaction.
  const [wantOpen, setWantOpen] = useState(false);
  const [raised, setRaised] = useState(false);
  const open = wantOpen && raised;
  // Drawer is display:none when fully closed to prevent Safari 26 Liquid Glass
  // tinting from scanning its fixed white background behind the toolbar.
  const visible = wantOpen || raised;
  const id = useId();

  const handleOpen = () => { if (prefersReducedMotion()) setRaised(true); setWantOpen(true); };
  const handleClose = useCallback(() => { setWantOpen(false); if (prefersReducedMotion()) setRaised(false); }, []);
  const { panel: drawerRef, clear: clearDrag, ...swipe } = useSheetSwipe(open, handleClose);

  // A native modal contains focus and makes the map behind it inert. Keep
  // that protection during the short exit; close() restores the opener.
  useLayoutEffect(() => {
    const dialog = drawerRef.current;
    if (!dialog) return;
    if (wantOpen && !dialog.open) dialog.showModal(); // First focusable control is Close.
    if (!visible && dialog.open) dialog.close();
  }, [wantOpen, visible, drawerRef]);
  useEffect(() => {
    if (!visible) return;
    const desktop = window.matchMedia('(min-width: 768px)');
    const motion = window.matchMedia(REDUCED_MOTION);
    const wide = () => { if (desktop.matches) { setWantOpen(false); setRaised(false); } };
    const reduce = () => { if (motion.matches) setRaised(wantOpen); };
    desktop.addEventListener('change', wide);
    motion.addEventListener('change', reduce);
    return () => { desktop.removeEventListener('change', wide); motion.removeEventListener('change', reduce); };
  }, [visible, wantOpen]);

  // Phase 1 (wanted, not raised): shown with translate-y-full (offscreen).
  // Phase 2, two frames later so that position has been laid out: slide up.
  useEffect(() => {
    if (!wantOpen || prefersReducedMotion()) return;
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => setRaised(true));
    });
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [wantOpen]);

  // Arm the fallback only while closing. A throttled opening frame must
  // never let an old timer hide a newly opened sheet.
  useEffect(() => {
    if (!wantOpen && raised) {
      const el = drawerRef.current;
      const onEnd = (e: TransitionEvent) => {
        // Ignore bubbled transitionend from children (e.g. button transition-colors)
        if (e.target !== el || e.pseudoElement) return;
        setRaised(false);
      };
      el?.addEventListener('transitionend', onEnd);
      // Fallback in case transitionend doesn't fire (e.g. display:none race)
      const timer = setTimeout(() => setRaised(false), 350);
      return () => { el?.removeEventListener('transitionend', onEnd); clearTimeout(timer); };
    }
  }, [wantOpen, raised, drawerRef]);

  return (
    <>
      {/* Toggle button */}
      <button
        type="button" aria-haspopup="dialog" aria-expanded={wantOpen} aria-controls={id}
        onClick={handleOpen}
        data-umami-event="open-mobile-filters"
        className="mobile-filter-launcher md:hidden fixed left-4 z-[1000] min-h-11 bg-white shadow-lg rounded-full px-4 py-2.5 text-sm font-medium border border-gray-200 flex items-center gap-2 active:bg-slate-100"
        style={{ bottom: 'max(16px, env(safe-area-inset-bottom, 16px))' }}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
        </svg>
        {t('filters')}
      </button>

      {/* Drawer — display:none when fully closed so Safari 26 Liquid Glass
          toolbar tinting doesn't scan this fixed white surface. */}
      <dialog
        ref={drawerRef}
        id={id} aria-labelledby={id + '-title'} data-open={open}
        onCancel={event => { event.preventDefault(); clearDrag(); handleClose(); }}
        onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); event.preventDefault(); clearDrag(); handleClose(); } }}
        onClick={event => {
          if (event.target !== event.currentTarget) return;
          const box = event.currentTarget.getBoundingClientRect();
          if (event.clientY < box.top || event.clientY > box.bottom || event.clientX < box.left || event.clientX > box.right) handleClose();
        }}
        className={`map-filter-sheet md:hidden fixed inset-x-0 top-auto bottom-0 m-0 w-full max-w-none overflow-hidden border-0 bg-white p-0 rounded-t-2xl shadow-2xl transition-transform ${
          open ? 'translate-y-0' : 'translate-y-full'
        }`}
        style={{ display: visible ? undefined : 'none' }}
      >
        <div {...swipe} className="map-filter-grip touch-none select-none px-4 pt-2">
          <div aria-hidden="true" className="mx-auto h-1 w-10 rounded-full bg-gray-300" />
          <div className="flex items-center justify-between">
            <span id={id + '-title'} className="font-bold text-base">{t('filtersAndRanking')}</span>
            <button
              type="button" aria-label={t('close')} onClick={handleClose}
              className="-mr-2 grid h-11 w-11 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600"
            >
              <svg aria-hidden="true" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="map-filter-scroll overflow-y-auto overscroll-contain" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
          <FilterPanel stations={stations} onAreaChosen={handleClose} />
        </div>
      </dialog>
    </>
  );
}
