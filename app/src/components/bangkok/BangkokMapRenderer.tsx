'use client';

import dynamic from 'next/dynamic';
import { Component, useCallback, useEffect, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import type { MapStation } from '@/lib/types';
import type { BangkokRenderer } from '@/lib/bangkok-prototype';
import type { MapUnavailableReason } from '@/lib/bangkok-renderer';

function MapLoading() {
  const t = useTranslations('loading');
  return <div role="status" className="h-full w-full flex items-center justify-center bg-gray-100 text-gray-400">{t('map')}</div>;
}

type Props = {
  stations: MapStation[];
  thumbnails?: Record<string, { thumb: string; lqip: string }>;
  snippets?: Record<string, string>;
  defaultRenderer: BangkokRenderer;
  prototypeRenderer?: BangkokRenderer;
};

type EngineProps = Omit<Props, 'defaultRenderer' | 'prototypeRenderer'> & {
  prototype?: boolean;
  onUnavailable?: (reason: MapUnavailableReason) => void;
  onImportFailure?: () => void;
};

function FailedImport({ onImportFailure }: EngineProps) {
  useEffect(() => { onImportFailure?.(); }, [onImportFailure]);
  return null;
}

class RendererErrorBoundary extends Component<{ onFailure: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() { return { failed: true }; }

  componentDidCatch() { this.props.onFailure(); }

  render() { return this.state.failed ? null : this.props.children; }
}

const DistrictMap = dynamic(() => import('@/components/DistrictMap'), { ssr: false, loading: MapLoading });
const MapLibreMap = dynamic<EngineProps>(
  () => import('@/components/bangkok/maplibre/MapLibreMap').catch(() => ({ default: FailedImport })),
  { ssr: false, loading: MapLoading },
);

/** Renderer state is local to the view; scoring and selections stay in the city store. */
export default function BangkokMapRenderer({ defaultRenderer, prototypeRenderer, ...mapProps }: Props) {
  const t = useTranslations('map');
  const [renderer, setRenderer] = useState<BangkokRenderer>(defaultRenderer);
  const [failure, setFailure] = useState<MapUnavailableReason | null>(null);
  const [importFailed, setImportFailed] = useState(false);
  const unavailable = useCallback((reason: MapUnavailableReason) => {
    setFailure(reason);
    if (!prototypeRenderer) setRenderer('leaflet');
  }, [prototypeRenderer]);
  const importUnavailable = useCallback(() => {
    setImportFailed(true);
    unavailable('load');
  }, [unavailable]);
  const renderUnavailable = useCallback(() => unavailable('load'), [unavailable]);
  const failureMessage = failure === 'webgl' ? t('rendererUnavailableWebgl') : failure === 'context' ? t('rendererUnavailableContext') : failure ? t('rendererUnavailableLoad') : null;
  const active = prototypeRenderer ?? renderer;
  const choose = (next: BangkokRenderer) => {
    setFailure(null);
    setRenderer(next);
  };

  return <>
    {active === 'maplibre'
      ? <RendererErrorBoundary onFailure={renderUnavailable}>
          <MapLibreMap {...mapProps} prototype={!!prototypeRenderer} onUnavailable={unavailable} onImportFailure={importUnavailable} />
        </RendererErrorBoundary>
      : <DistrictMap {...mapProps} prototype={!!prototypeRenderer} />}
    {!prototypeRenderer && <div className="map-renderer-selector absolute left-3 top-24 md:left-auto md:right-3 md:top-14 z-[1000] flex items-start gap-1">
      <label className="sr-only" htmlFor="bangkok-map-renderer">{t('rendererLabel')}</label>
      <select id="bangkok-map-renderer" value={renderer} onChange={(event) => choose(event.target.value as BangkokRenderer)}
        className="map-control-btn max-w-[10rem] rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-700 shadow-sm focus-visible:outline-2 focus-visible:outline-blue-600">
        <option value="maplibre" disabled={importFailed}>{t('rendererThreeD')}</option>
        <option value="leaflet">{t('rendererStandard')}</option>
      </select>
      {failureMessage && <>
        <span role="status" className="sr-only">{failureMessage}</span>
        <details className="relative">
          <summary aria-label={failureMessage} title={failureMessage} className="map-control-btn flex h-9 w-9 cursor-pointer list-none items-center justify-center rounded-lg border border-amber-200 bg-white text-sm font-bold text-amber-800 shadow-sm focus-visible:outline-2 focus-visible:outline-blue-600">!</summary>
          <p className="absolute -left-28 top-full mt-1 w-60 max-w-[calc(100vw-1.5rem)] rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs text-amber-900 shadow-sm">{failureMessage}</p>
        </details>
      </>}
    </div>}
    {prototypeRenderer && failure && <p role="alert" className="absolute left-3 top-24 z-[1000] rounded-lg bg-white px-3 py-2 text-xs text-amber-900">{failure === 'webgl' ? t('rendererUnavailableWebgl') : failure === 'context' ? t('rendererUnavailableContext') : t('rendererUnavailableLoad')}</p>}
  </>;
}
