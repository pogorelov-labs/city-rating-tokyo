/** Ask a mounted map to flush pending URL state before programmatic navigation. */
export const MAP_NAVIGATION_INTENT = 'city-rating:map-navigation-intent';

export function prepareMapNavigation() {
  window.dispatchEvent(new Event(MAP_NAVIGATION_INTENT));
}

/** A repeated explicit district choice asks the active map to reveal it again. */
export const DISTRICT_FOCUS_INTENT = 'city-rating:district-focus-intent';
export function requestDistrictFocus(city: string, key: string) {
  if (city === 'bangkok' && !key.includes('.')) {
    window.dispatchEvent(new CustomEvent(DISTRICT_FOCUS_INTENT, { detail: { city, key } }));
  }
}
