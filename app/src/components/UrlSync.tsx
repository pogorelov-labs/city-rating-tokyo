'use client';

import { useEffect, useRef } from 'react';
import { useAppStore } from '@/lib/store';
import { useCityId } from '@/lib/city-context';
import { decodeParamsToState, buildShareUrl, encodeStateToParams, selectUrlView } from '@/lib/url-state';

export default function UrlSync() {
  const city = useCityId();
  const hydrated = useRef(false);

  // On mount: read URL → store (into this page's city slice)
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;

    const params = new URLSearchParams(window.location.search);
    if (params.toString()) {
      const state = decodeParamsToState(params, city);
      useAppStore.getState().hydrateFromUrl(city, state);
      return;
    }

    // Arrived without a query, yet state may have come along from another
    // page — e.g. weights tuned on the Tokyo map, then the city switcher (a
    // plain link) opened /bangkok. Write it back so the address bar is
    // shareable at once. Links that do carry a query are left untouched until
    // the user changes something, so utm_* and friends survive for analytics.
    const view = selectUrlView(useAppStore.getState(), city);
    if (encodeStateToParams(view, city).toString()) {
      window.history.replaceState(null, '', buildShareUrl(view, city));
    }
  }, [city]);

  // On store change: store → URL (debounced)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const unsub = useAppStore.subscribe((state) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const url = buildShareUrl(selectUrlView(state, city), city);
        window.history.replaceState(null, '', url);
      }, 300);
    });
    return () => { unsub(); clearTimeout(timer); };
  }, [city]);

  return null;
}
