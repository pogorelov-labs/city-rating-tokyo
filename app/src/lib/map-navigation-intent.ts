/** Ask a mounted map to flush pending URL state before programmatic navigation. */
export const MAP_NAVIGATION_INTENT = 'city-rating:map-navigation-intent';

export function prepareMapNavigation() {
  window.dispatchEvent(new Event(MAP_NAVIGATION_INTENT));
}
