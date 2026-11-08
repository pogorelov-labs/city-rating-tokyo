import { CITIES, type CityId } from './cities';
import { decodeParamsToState, encodeStateToParams, type UrlStateView } from './url-state';

/** Return to the guide's own area while retaining the active map settings. */
export function guideMapHref(mapHref: string, city: CityId, view: UrlStateView): string {
  const path = city === 'bangkok' ? '/bangkok' : '/';
  const base = 'https://city-rating.invalid';
  const target = new URL(mapHref, base);
  if (target.origin !== base || target.pathname !== path) throw new Error('Invalid guide map destination');
  const destination = decodeParamsToState(target.searchParams, city);
  const params = encodeStateToParams({
    ...view,
    level: destination.level ?? CITIES[city].defaultLevel,
    selectedStation: destination.selectedStation ?? null,
  }, city);
  const query = params.toString();
  return path + (query ? `?${query}` : '');
}
