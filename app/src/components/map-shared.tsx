'use client';

import { useState } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

// Map building blocks shared by the Tokyo station map (Map.tsx) and the
// Bangkok district map (DistrictMap.tsx). Kept in their own module so the
// district chunk does not pull in the whole station map.

/** Touch-only zoom buttons — bottom-right, above the compare panel / drawer */
export function TouchZoomControls() {
  const map = useMap();
  return (
    <div className="leaflet-bottom leaflet-right" style={{ pointerEvents: 'none' }}>
      <div
        className="leaflet-control flex flex-col gap-1"
        style={{ pointerEvents: 'auto', marginBottom: 'calc(80px + env(safe-area-inset-bottom, 0px))', marginRight: 10 }}
      >
        <button
          onClick={() => map.zoomIn()}
          className="bg-white rounded-lg shadow-md border border-gray-200 w-10 h-10 flex items-center justify-center text-xl font-bold text-gray-700 active:bg-gray-100"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => map.zoomOut()}
          className="bg-white rounded-lg shadow-md border border-gray-200 w-10 h-10 flex items-center justify-center text-xl font-bold text-gray-700 active:bg-gray-100"
          aria-label="Zoom out"
        >
          −
        </button>
      </div>
    </div>
  );
}

/**
 * Return a darker variant of an `rgb(r, g, b)` string produced by `scoreToColor`.
 * Used for the fallback gradient header so we can't accidentally produce invalid
 * CSS like `${rgbString}cc` (which would be silently dropped by the browser).
 */
export function darkenRgb(rgb: string, factor = 0.7): string {
  const match = rgb.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if (!match) return rgb;
  const r = Math.round(Number(match[1]) * factor);
  const g = Math.round(Number(match[2]) * factor);
  const b = Math.round(Number(match[3]) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * SVG renderer for overlay markers (halo, top-5 pulse) that need CSS
 * className-based animations. The main 1493 markers use the Canvas
 * renderer (preferCanvas on MapContainer) for much cheaper flyTo animation.
 */
let svgOverlayRenderer: L.SVG | null = null;
export function getSvgRenderer(): L.SVG {
  if (!svgOverlayRenderer) svgOverlayRenderer = L.svg();
  return svgOverlayRenderer;
}

/** Score-colored gradient fallback when no imagery is available. */
export function GradientHeader({
  nameJp,
  score,
  color,
  height,
}: {
  nameJp: string;
  score: number | null;
  color: string;
  height: number;
}) {
  return (
    <div
      aria-hidden
      style={{
        width: '100%',
        height,
        backgroundImage:
          score !== null
            ? `linear-gradient(135deg, ${color}, ${darkenRgb(color)})`
            : 'linear-gradient(135deg, #e5e7eb, #9ca3af)',
        borderRadius: '6px 6px 0 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontFamily: 'serif',
        fontWeight: 700,
        fontSize: 26,
        letterSpacing: 2,
        textShadow: '0 1px 3px rgba(0,0,0,0.25)',
      }}
    >
      {nameJp}
    </div>
  );
}

/**
 * Tooltip header: three-tier image loading.
 * 1. LQIP base64 shown instantly (blurred, zero network)
 * 2. VPS thumbnail (320px, ~20 KB) crossfades in over LQIP
 * 3. Gradient fallback if no imagery at all
 *
 * The tooltip has a 400ms CSS show delay. If the thumbnail loads within
 * that window the user never sees the LQIP blur.
 */
export function StationTooltipHero({
  slug,
  thumb,
  lqip,
  nameEn,
  nameJp,
  score,
  color,
}: {
  slug: string;
  thumb: string | undefined;
  lqip: string | undefined;
  nameEn: string;
  nameJp: string;
  score: number | null;
  color: string;
}) {
  const [thumbLoaded, setThumbLoaded] = useState(false);
  const [thumbFailed, setThumbFailed] = useState(false);

  // No imagery at all → compact gradient
  if (!thumb && !lqip) {
    return <GradientHeader nameJp={nameJp} score={score} color={color} height={60} />;
  }

  // Thumb failed → degrade to gradient (even if LQIP exists — permanent blur is worse)
  if (thumbFailed) {
    return <GradientHeader nameJp={nameJp} score={score} color={color} height={100} />;
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 100,
        overflow: 'hidden',
        borderRadius: '6px 6px 0 0',
      }}
    >
      {/* Base layer: LQIP (inline data URL, instant, blurred) */}
      {lqip && !thumbLoaded && (
        <img
          src={lqip}
          alt=""
          aria-hidden
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(20px)',
            transform: 'scale(1.1)',
          }}
        />
      )}
      {/* Top layer: sharp thumbnail, fades in over LQIP */}
      {thumb && !thumbFailed && (
        <img
          src={thumb}
          alt={nameEn}
          onLoad={() => setThumbLoaded(true)}
          onError={() => {
            setThumbFailed(true);
            window.umami?.track('error', {
              category: 'image',
              station: slug,
              context: 'tooltip',
            });
          }}
          style={{
            position: lqip ? 'absolute' : 'relative',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: thumbLoaded ? 1 : 0,
            transition: 'opacity 200ms ease-in',
          }}
        />
      )}
    </div>
  );
}
