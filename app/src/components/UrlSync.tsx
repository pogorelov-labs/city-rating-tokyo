'use client';

import { useEffect, useRef } from 'react';
import { useAppStore } from '@/lib/store';
import { decodeParamsToState, buildShareUrl } from '@/lib/url-state';

export default function UrlSync() {
  const hydrated = useRef(false);

  // On mount: read URL → store
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;

    const params = new URLSearchParams(window.location.search);
    if (params.toString()) {
      const state = decodeParamsToState(params);
      useAppStore.getState().hydrateFromUrl(state);
    }
  }, []);

  // On store change: store → URL (debounced)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const unsub = useAppStore.subscribe((state) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const url = buildShareUrl(state);
        window.history.replaceState(null, '', url);
      }, 300);
    });
    return () => { unsub(); clearTimeout(timer); };
  }, []);

  return null;
}
