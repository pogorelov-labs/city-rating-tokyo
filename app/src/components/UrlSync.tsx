'use client';

import { useEffect, useRef } from 'react';
import { useLocale } from 'next-intl';
import { MAP_NAVIGATION_INTENT } from '@/lib/map-navigation-intent';
import { useAppStore } from '@/lib/store';
import { useCityId } from '@/lib/city-context';
import { decodeParamsToState, buildShareUrl, encodeStateToParams, selectUrlView } from '@/lib/url-state';

export default function UrlSync() {
  const city = useCityId();
  const locale = useLocale();
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
    let timer: ReturnType<typeof setTimeout> | undefined;
    let navigating = false;
    let lastUrl = buildShareUrl(selectUrlView(useAppStore.getState(), city), city);
    const unsub = useAppStore.subscribe((state) => {
      const url = buildShareUrl(selectUrlView(state, city), city);
      // Hover and animation state are not in share links. Replacing history
      // for those changes can interrupt a pending detail-page navigation.
      if (url === lastUrl || navigating) return;
      lastUrl = url;
      clearTimeout(timer);
      timer = setTimeout(() => {
        timer = undefined;
        window.history.replaceState(null, '', url);
      }, 300);
    });
    // Next's client navigation may still be fetching when the click handler
    // returns. Flush the old map entry before the router handles a same-tab
    // local link, then prevent later store updates from interrupting it.
    const flush = () => {
      if (timer === undefined) return;
      clearTimeout(timer);
      timer = undefined;
      const current = buildShareUrl(selectUrlView(useAppStore.getState(), city), city);
      if (current !== window.location.href) window.history.replaceState(null, '', current);
      lastUrl = current;
    };
    const onNavigation = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target instanceof Element ? event.target.closest('a[href]') : null;
      if (!(anchor instanceof HTMLAnchorElement) || anchor.hasAttribute('download') ||
          (anchor.target && anchor.target.toLowerCase() !== '_self')) return;
      const destination = new URL(anchor.href, window.location.href);
      if (destination.origin !== window.location.origin ||
          (destination.pathname === window.location.pathname && destination.search === window.location.search)) return;
      flush();
      // Query-only transitions can keep this map mounted. Continue syncing it.
      if (destination.pathname !== window.location.pathname) navigating = true;
    };
    const onProgrammaticNavigation = () => { flush(); navigating = true; };
    const onPopState = () => {
      navigating = false;
      lastUrl = buildShareUrl(selectUrlView(useAppStore.getState(), city), city);
    };
    document.addEventListener('click', onNavigation, true);
    window.addEventListener('popstate', onPopState);
    window.addEventListener(MAP_NAVIGATION_INTENT, onProgrammaticNavigation);
    return () => {
      unsub(); clearTimeout(timer);
      document.removeEventListener('click', onNavigation, true);
      window.removeEventListener('popstate', onPopState);
      window.removeEventListener(MAP_NAVIGATION_INTENT, onProgrammaticNavigation);
    };
  }, [city, locale]);

  return null;
}
