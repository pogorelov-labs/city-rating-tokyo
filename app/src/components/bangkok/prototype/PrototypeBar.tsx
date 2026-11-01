'use client';

import type { BangkokRenderer } from '@/lib/bangkok-prototype';
import { useAppStore } from '@/lib/store';
import { buildShareUrl, selectUrlView } from '@/lib/url-state';

export default function PrototypeBar({ renderer }: { renderer: BangkokRenderer }) {
  const switchRenderer = (next: BangkokRenderer) => {
    const url = new URL(buildShareUrl(selectUrlView(useAppStore.getState(), 'bangkok'), 'bangkok'));
    url.pathname = url.pathname.replace(/\/(maplibre|leaflet)\/?$/, `/${next}`);
    window.location.assign(url);
  };
  return <nav aria-label="Renderer comparison" className="flex shrink-0 items-center gap-2 border-b border-slate-200 bg-slate-50 px-3 py-1 text-sm">
    <span className="mr-auto text-xs font-medium text-slate-600">Renderer lab</span>
    {(['maplibre', 'leaflet'] as const).map((id) => <button key={id} type="button" aria-pressed={renderer === id}
      onClick={() => switchRenderer(id)} className={`min-h-11 rounded-md px-3 font-medium focus-visible:outline-2 focus-visible:outline-blue-600 ${renderer === id ? 'bg-slate-800 text-white' : 'text-slate-700 hover:bg-slate-200'}`}>
      {id === 'maplibre' ? 'MapLibre 3D' : 'Leaflet 2D'}
    </button>)}
  </nav>;
}
