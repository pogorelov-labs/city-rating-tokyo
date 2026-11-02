// With linearity 1 and a quadratic ease-out, the first coast frame starts
// at release velocity: distance = speed × duration / 2. Cap a fast throw.
export const decelerate = (t: number) => t * (2 - t);
export const PAN_INERTIA = { linearity: 1, maxSpeed: 1650, deceleration: 3600, easing: decelerate } as const;
// Leaflet also uses 1 / easeLinearity as its easing exponent. A value of
// one would coast at constant speed and then stop abruptly.
export const LEAFLET_PAN = { easeLinearity: .5, inertiaMaxSpeed: 825, inertiaDeceleration: 3600 } as const;

export const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';
export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.(REDUCED_MOTION)?.matches === true;

export type BangkokMotion = 'system' | 'smooth';
const storageKey = 'city-rating:bangkok:camera-motion';
const changed = 'bangkok-camera-motion-change';
let unsaved: BangkokMotion | undefined;

/** A personal camera preference, independent of filters, shared URLs and Tokyo. */
export function bangkokMotion(): BangkokMotion {
  if (typeof window === 'undefined') return 'system';
  if (unsaved) return unsaved;
  try { return window.localStorage.getItem(storageKey) === 'smooth' ? 'smooth' : 'system'; }
  catch { return 'system'; }
}
export function setBangkokMotion(value: BangkokMotion) {
  try {
    if (value === 'system') window.localStorage.removeItem(storageKey);
    else window.localStorage.setItem(storageKey, value);
    unsaved = undefined;
  } catch { unsaved = value; }
  window.dispatchEvent(new Event(changed));
}
export function subscribeBangkokMotion(notify: () => void) {
  const query = window.matchMedia?.(REDUCED_MOTION);
  const storage = (event: StorageEvent) => {
    if (event.key === storageKey || event.key === null) { unsaved = undefined; notify(); }
  };
  window.addEventListener(changed, notify);
  window.addEventListener('storage', storage);
  query?.addEventListener('change', notify);
  return () => {
    window.removeEventListener(changed, notify);
    window.removeEventListener('storage', storage);
    query?.removeEventListener('change', notify);
  };
}
export const smoothOverride = () => prefersReducedMotion() && bangkokMotion() === 'smooth';
export const bangkokCameraReduced = () => prefersReducedMotion() && bangkokMotion() !== 'smooth';

const durations = { step: 220, view: 300, district: 375 } as const;
const easeOut = (t: number) => 1 - (1 - t) ** 3;
export function cameraMotion(kind: keyof typeof durations) {
  const reduced = prefersReducedMotion(), optedIn = reduced && bangkokMotion() === 'smooth';
  // Only an explicit personal opt-in may bypass MapLibre's device preference.
  return { duration: reduced && !optedIn ? 0 : durations[kind], easing: easeOut, essential: optedIn };
}
