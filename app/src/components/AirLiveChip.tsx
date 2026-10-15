'use client';
import { useEffect, useState } from 'react';
import type { AirCity, LiveAir } from '@/lib/air/model';
export type AirLabels = Record<'loading' | 'fresh' | 'stale' | 'unavailable' | 'permission_pending' | 'observed' | 'fetched' | 'coverage' | 'preliminary', string>;
export function AirLiveView({ data, labels }: { data: LiveAir | null; labels: AirLabels }) {
  return <div aria-live="polite" className="space-y-1 text-sm">
    <p className="font-medium text-gray-900">{labels[data?.status ?? 'loading']}</p>
    {data?.value != null && <p className="text-2xl font-semibold tabular-nums text-gray-900">{data.value.toFixed(1)} <span className="text-sm font-normal">µg/m³</span></p>}
    {data?.observedAt && <p className="text-xs text-gray-600">{labels.observed}: <time dateTime={data.observedAt}>{data.observedAt.replace('T',' ').replace('.000Z',' UTC')}</time></p>}
    {data?.fetchedAt && <p className="text-xs text-gray-600">{labels.fetched}: <time dateTime={data.fetchedAt}>{data.fetchedAt.replace('T',' ').replace('.000Z',' UTC')}</time></p>}
    {data && data.eligible > 0 && <p className="text-xs text-gray-600">{labels.coverage}: {data.reporting} / {data.eligible}</p>}
    {data?.value != null && <p className="text-xs text-gray-600">{labels.preliminary}</p>}
  </div>;
}
export default function AirLiveChip({ city, labels }: { city: AirCity; labels: AirLabels }) {
  const [data, setData] = useState<LiveAir | null>(null);
  useEffect(() => {
    let active = true; let current: AbortController | undefined;
    async function refresh() {
      current?.abort(); const controller = new AbortController(); current = controller;
      const timeout = setTimeout(() => controller.abort(), 20000);
      try {
        const response = await fetch(`/api/air/${city}`, { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Air unavailable');
        const next = await response.json() as LiveAir;
        if (next.city !== city || !['fresh','stale','unavailable','permission_pending'].includes(next.status)) throw new Error('Invalid air response');
        if (active && current === controller) setData(next);
      } catch {
        if (active && current === controller) setData(previous => previous
          ? { ...previous, status: 'unavailable', value: null }
          : { city, status:'unavailable', value:null, observedAt:null, fetchedAt:null, checkedAt:'', reporting:0, eligible:0, unit:'µg/m³', scope:city === 'tokyo' ? 'national_monitor' : 'reporting_monitors' });
      } finally { clearTimeout(timeout); }
    }
    void refresh();
    // Re-fetch server-derived freshness; never infer fresh data from client clock.
    const interval = setInterval(() => { if (!document.hidden) void refresh(); }, 300000);
    const visible = () => { if (!document.hidden) void refresh(); };
    document.addEventListener('visibilitychange', visible);
    return () => { active = false; current?.abort(); clearInterval(interval); document.removeEventListener('visibilitychange', visible); };
  }, [city]);
  return <AirLiveView data={data} labels={labels} />;
}
