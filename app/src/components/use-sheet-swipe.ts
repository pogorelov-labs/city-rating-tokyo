'use client';

import { useCallback, useEffect, useRef, type PointerEvent } from 'react';

/** Only the sheet header captures gestures. Scroll, sliders and links inside
 * the sheet body keep their normal browser behavior. No React update per move. */
export function useSheetSwipe(open: boolean, dismiss: () => void) {
  const panel = useRef<HTMLDialogElement>(null);
  const drag = useRef<{ id: number; start: number; height: number; samples: { y: number; time: number }[] } | null>(null);
  const clear = useCallback(() => {
    drag.current = null;
    if (!panel.current) return;
    panel.current.removeAttribute('data-dragging');
    panel.current.style.removeProperty('translate');
  }, []);
  useEffect(() => { if (!open) clear(); return clear; }, [open, clear]);
  const sample = (event: PointerEvent) => {
    const d = drag.current; if (!d || d.id !== event.pointerId) return;
    const time = event.timeStamp, y = event.clientY;
    d.samples = d.samples.filter(p => time - p.time <= 100);
    d.samples.push({ y, time });
    const distance = Math.min(d.height, Math.max(0, y - d.start));
    const first = d.samples[0];
    return { distance, velocity: (y - first.y) / Math.max(1, time - first.time), height: d.height };
  };
  return {
    panel,
    onPointerDown(event: PointerEvent<HTMLElement>) {
      if (!open || drag.current || !event.isPrimary || event.button !== 0 || (event.target as Element).closest('button')) return;
      const el = panel.current; if (!el) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { id: event.pointerId, start: event.clientY, height: el.offsetHeight, samples: [{ y: event.clientY, time: event.timeStamp }] };
      el.setAttribute('data-dragging', 'true');
    },
    onPointerMove(event: PointerEvent) {
      const p = sample(event);
      if (p) panel.current?.style.setProperty('translate', `0 ${p.distance}px`);
    },
    onPointerUp(event: PointerEvent) {
      const p = sample(event); if (!p) return;
      clear();
      if (p.distance >= Math.min(128, p.height * .3) || (p.distance >= 24 && p.velocity >= .6)) dismiss();
    },
    onLostPointerCapture(event: PointerEvent) { if (drag.current?.id === event.pointerId) clear(); },
    onPointerCancel(event: PointerEvent) { if (drag.current?.id === event.pointerId) clear(); },
    clear,
  };
}
