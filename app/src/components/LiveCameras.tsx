'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { LiveCamera } from '@/lib/types';
import { Locale } from '@/i18n/routing';
import { useIsTouch } from '@/lib/use-is-touch';

interface Props {
  livecams: LiveCamera[];
  locale: Locale;
}

/**
 * Live YouTube camera feeds near the station.
 *
 * Design:
 * - Click-to-load facade: iframe only mounts after user click (saves
 *   ~500 KB JS per page-load; no YouTube cookies until user consents).
 * - `youtube-nocookie.com` domain to match our GDPR footer.
 * - `mute=1` in the embed — broadcast convention; users unmute via
 *   YouTube's own control. Avoids startling office/mobile users.
 * - Tab strip when 2+ cameras (proper ARIA: tab + tabpanel pair).
 *   Tab switch updates the iframe `src` so the player pane stays in
 *   place and doesn't collapse back to the facade.
 * - Dismiss ✕ overlay when playing, so users can collapse back to the
 *   facade without navigating away (important for muting/silencing).
 * - RU locale falls back to EN names — MT3D source has no Russian.
 *
 * No iframe is rendered until `isPlaying` is true, so browser devtools
 * Network panel will show zero YouTube requests on initial page-load.
 */
export default function LiveCameras({ livecams, locale }: Props) {
  const t = useTranslations();
  const isTouch = useIsTouch();
  const [activeIdx, setActiveIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  if (!livecams || livecams.length === 0) return null;

  const active = livecams[activeIdx];

  // iOS Safari often refuses to autoplay YouTube live stream embeds even when
  // muted: the player ends up in a stuck "trying to autoplay" state and shows
  // a black rectangle. Dropping the `autoplay` param on touch devices lets
  // YouTube's own player render its preview + play button, which the user can
  // tap as a (single extra) gesture to actually start the stream. Desktop keeps
  // autoplay because Chrome/Safari/Firefox honor `mute=1` autoplay reliably
  // and the click on our facade already counts as the gesture.
  const iframeSrc = useMemo(() => {
    if (!isTouch) return active.embed_url;
    try {
      const u = new URL(active.embed_url);
      u.searchParams.delete('autoplay');
      return u.toString();
    } catch {
      return active.embed_url.replace(/[?&]autoplay=1/, (m) => (m.startsWith('?') ? '?' : ''));
    }
  }, [active.embed_url, isTouch]);
  // RU falls back to EN — MT3D source has no Russian
  const pickName = (cam: LiveCamera) =>
    locale === 'ja' ? cam.name_ja : cam.name_en;

  const tabIdBase = 'livecam-tab';
  const panelId = 'livecam-panel';

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-3">{t('station.liveCamsTitle')}</h2>

      {/* Tab strip — only when 2+ cameras */}
      {livecams.length > 1 && (
        <div
          className="flex flex-wrap gap-1.5 mb-3"
          role="tablist"
          aria-label={t('station.liveCamsTitle')}
        >
          {livecams.map((cam, idx) => (
            <button
              key={cam.id}
              id={`${tabIdBase}-${idx}`}
              type="button"
              role="tab"
              aria-selected={idx === activeIdx}
              aria-controls={panelId}
              tabIndex={idx === activeIdx ? 0 : -1}
              onClick={() => setActiveIdx(idx)}
              className={
                idx === activeIdx
                  ? 'px-3 py-1 text-xs font-medium rounded-full bg-slate-800 text-white'
                  : 'px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            >
              {pickName(cam)}
            </button>
          ))}
        </div>
      )}

      {/* Player: facade or iframe */}
      <div
        id={panelId}
        role={livecams.length > 1 ? 'tabpanel' : undefined}
        aria-labelledby={livecams.length > 1 ? `${tabIdBase}-${activeIdx}` : undefined}
        className="relative w-full aspect-video bg-slate-900 rounded-lg overflow-hidden"
      >
        {!isPlaying ? (
          <button
            type="button"
            onClick={() => setIsPlaying(true)}
            className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900 text-white group focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-white"
            aria-label={t('station.liveCamsPlay')}
            data-umami-event="livecam-play"
            data-umami-event-station={active.id}
          >
            {/* Real video thumbnail from YouTube. If image fails (channel/video
                removed), the gradient behind shows through naturally. */}
            <img
              src={active.thumbnail}
              alt=""
              aria-hidden
              className="absolute inset-0 w-full h-full object-cover opacity-75 group-hover:opacity-90 transition-opacity"
              loading="lazy"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            {/* Dark gradient overlay so play icon + label stay readable on any thumb */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-black/20" aria-hidden />
            <div className="relative flex flex-col items-center gap-3 px-4">
              <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center group-hover:bg-white/30 transition-colors">
                <svg viewBox="0 0 24 24" className="w-8 h-8 ml-1 fill-white" aria-hidden>
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              <div className="text-sm font-medium drop-shadow">{t('station.liveCamsPlay')}</div>
              <div className="text-xs text-white/90 text-center line-clamp-2 drop-shadow">{pickName(active)}</div>
            </div>
          </button>
        ) : (
          <>
            <iframe
              src={iframeSrc}
              title={pickName(active)}
              className="absolute inset-0 w-full h-full border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
            <button
              type="button"
              onClick={() => setIsPlaying(false)}
              aria-label={t('station.liveCamsClose')}
              title={t('station.liveCamsClose')}
              className="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-white z-10"
              data-umami-event="livecam-close"
              data-umami-event-station={active.id}
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
                <line x1="6" y1="6" x2="18" y2="18" />
                <line x1="6" y1="18" x2="18" y2="6" />
              </svg>
            </button>
          </>
        )}
      </div>

      {/* Footer: YouTube deep link + attribution */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <a
          href={active.watch_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline inline-flex items-center gap-1"
          data-umami-event="livecam-open-youtube"
          data-umami-event-station={active.id}
        >
          {t('station.liveCamsOpenYoutube')}
          <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>
        <span className="text-gray-400">{t('station.liveCamsAttribution')}</span>
      </div>
    </section>
  );
}
