// Both renderers compute the pan coast as speed / (deceleration * linearity).
// These values give a quick flick up to 400 ms / 168 CSS px of follow-through.
// The native handlers still own velocity samples, projection and interruption.
export const PAN_INERTIA = { linearity: 0.35, maxSpeed: 840, deceleration: 6000 } as const;

export const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';
export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.(REDUCED_MOTION)?.matches === true;

const durations = { step: 220, view: 300, district: 375 } as const;
const easeOut = (t: number) => 1 - (1 - t) ** 3;
export const cameraMotion = (kind: keyof typeof durations) => ({
  duration: prefersReducedMotion() ? 0 : durations[kind],
  easing: easeOut,
  essential: false,
});
