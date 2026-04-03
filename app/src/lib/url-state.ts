import { WeightConfig, DEFAULT_WEIGHTS } from './types';

const WEIGHT_KEYS = Object.keys(DEFAULT_WEIGHTS) as (keyof WeightConfig)[];

export function encodeStateToParams(state: {
  weights: WeightConfig;
  selectedStation: string | null;
  compareStations: string[];
  heatmapMode: boolean;
  heatmapDimension: string;
}): URLSearchParams {
  const params = new URLSearchParams();

  // Only include weights if different from defaults
  const isDefault = WEIGHT_KEYS.every((k) => state.weights[k] === DEFAULT_WEIGHTS[k]);
  if (!isDefault) {
    params.set('w', WEIGHT_KEYS.map((k) => state.weights[k]).join(','));
  }

  if (state.selectedStation) params.set('s', state.selectedStation);
  if (state.compareStations.length > 0) params.set('c', state.compareStations.join(','));
  if (state.heatmapMode) params.set('hm', '1');
  if (state.heatmapDimension !== 'composite') params.set('hd', state.heatmapDimension);

  return params;
}

export function decodeParamsToState(params: URLSearchParams): {
  weights?: WeightConfig;
  selectedStation?: string;
  compareStations?: string[];
  heatmapMode?: boolean;
  heatmapDimension?: string;
} {
  const result: ReturnType<typeof decodeParamsToState> = {};

  const w = params.get('w');
  if (w) {
    const values = w.split(',').map(Number);
    if (values.length === WEIGHT_KEYS.length && values.every((v) => !isNaN(v))) {
      const weights = {} as WeightConfig;
      WEIGHT_KEYS.forEach((k, i) => { weights[k] = values[i]; });
      result.weights = weights;
    }
  }

  const s = params.get('s');
  if (s) result.selectedStation = s;

  const c = params.get('c');
  if (c) result.compareStations = c.split(',').filter(Boolean);

  if (params.get('hm') === '1') result.heatmapMode = true;

  const hd = params.get('hd');
  if (hd) result.heatmapDimension = hd;

  return result;
}

export function buildShareUrl(state: Parameters<typeof encodeStateToParams>[0]): string {
  const params = encodeStateToParams(state);
  const qs = params.toString();
  return window.location.origin + window.location.pathname + (qs ? '?' + qs : '');
}
