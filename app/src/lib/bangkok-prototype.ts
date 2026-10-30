export type BangkokRenderer = 'leaflet' | 'maplibre';

/** Zoom is normalized to Leaflet's 256-pixel world for comparable ground scale. */
export interface PrototypeCamera {
  lng: number;
  lat: number;
  zoom: number;
  pitch?: number;
  bearing?: number;
}

export interface BangkokRendererHandle {
  renderer: BangkokRenderer;
  ready: () => boolean;
  setCamera: (camera: PrototypeCamera, duration?: number) => void;
  getCamera: () => PrototypeCamera;
  project: (lng: number, lat: number) => { x: number; y: number };
  stats: () => Record<string, number | string | boolean>;
  /** Controlled ablation, exposed only with ?profile=1 in the renderer lab. */
  setLayerGroup?: (group: 'grid' | 'areas' | 'labels' | 'rail' | 'buildings', visible: boolean) => void;
  inspectArea?: (key: string) => { area: Record<string, unknown>; stations: Record<string, unknown>[];
    rendered: { id?: string | number; state: Record<string, unknown> }[];
    renderedFocus: { id?: string | number; state: Record<string, unknown> }[];
    renderedStations: { id?: string | number; state: Record<string, unknown> }[] };
  inspectCartography?: () => { layers: string[]; nature: { layer: string; kind: string; name: string }[];
    paint: Record<string, unknown>; focusVisible: boolean };
}

declare global {
  interface Window {
    __bangkokRenderer?: BangkokRendererHandle;
    __bangkokInitialCamera?: PrototypeCamera;
    __bangkokInitialBuildings?: boolean;
    __bangkokGridPaint?: { version: number; at: number };
  }
}

export function recordPrototypeGridPaint() {
  if (typeof window !== 'undefined' && window.__bangkokRenderer) {
    window.__bangkokGridPaint = { version: (window.__bangkokGridPaint?.version ?? 0) + 1, at: performance.now() };
  }
}

export const ASOK_CAMERA: PrototypeCamera = { lng: 100.5606, lat: 13.7374, zoom: 16, pitch: 50, bearing: -20 };
