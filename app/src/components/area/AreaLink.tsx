'use client';

import type { ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { useAppStore } from '@/lib/store';
import { withGuideWeights } from '@/lib/area-guide';

/** Server-rendered related-area links retain preferences when opened in a new tab. */
export default function AreaLink({ href, children, className, ...analytics }: { href: string; children: ReactNode; className?: string; 'data-umami-event'?: string; 'data-umami-event-station'?: string }) {
  const weights = useAppStore(state => state.weights);
  return <Link href={withGuideWeights(href, weights)} className={className} {...analytics}>{children}</Link>;
}
