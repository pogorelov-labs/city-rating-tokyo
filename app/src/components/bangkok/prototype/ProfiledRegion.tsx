'use client';
import { Profiler, useEffect, type ReactNode } from 'react';
import { renderProfile, retainRendererLab } from '@/lib/render-profile';

// React's production profiler requires `next build --profile`. These timings
// include descendant renders, not commit/layout/paint or the map's GPU work.
export default function ProfiledRegion({ id, children }: { id: string; children: ReactNode }) {
  useEffect(() => retainRendererLab(), []);
  return <Profiler id={id} onRender={(name, _phase, duration) => renderProfile()?.record(`react.${name}`, duration)}>{children}</Profiler>;
}
