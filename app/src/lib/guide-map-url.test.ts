import { describe, expect, it } from 'vitest';
import { CITIES } from './cities';
import { DEFAULT_WEIGHTS } from './types';
import { decodeParamsToState, type UrlStateView } from './url-state';
import { guideMapHref } from './guide-map-url';

const view: UrlStateView = {
  level: 'grid', weights: { ...DEFAULT_WEIGHTS, food: 3 },
  filters: { ...CITIES.bangkok.defaultFilters, maxRent: 25000, categoryMins: { safety: 7 } },
  hideFloodRisk: true, hideAdultZones: true, hideHighSeismic: false,
  selectedStation: 'cell.99', compareStations: ['st.asok', 'khlong-toei'], heatmapMode: true, heatmapDimension: 'food',
};

describe('guide map return URL', () => {
  it('preserves map filters, flags, comparisons and guide weights while selecting the guide station and level', () => {
    const href = guideMapHref('/bangkok?lv=station&s=st.asok', 'bangkok', view);
    const url = new URL(href, 'https://city-rating.test');
    const result = decodeParamsToState(url.searchParams, 'bangkok');
    expect(url.pathname).toBe('/bangkok');
    expect(result).toMatchObject({ level: 'station', selectedStation: 'st.asok', weights: view.weights,
      filters: { maxRent: 25000, categoryMins: { safety: 7 } }, hideFloodRisk: true, hideAdultZones: true,
      compareStations: view.compareStations, heatmapMode: true, heatmapDimension: 'food' });
  });
  it('honors a district target and defaults on a fresh guide', () => {
    const fresh = { ...view, weights: DEFAULT_WEIGHTS, filters: CITIES.bangkok.defaultFilters,
      hideFloodRisk: false, hideAdultZones: false, compareStations: [], heatmapMode: false, heatmapDimension: 'composite' };
    expect(guideMapHref('/bangkok?lv=district&s=khlong-toei', 'bangkok', fresh)).toBe('/bangkok?s=khlong-toei');
  });
  it('preserves Tokyo seismic and camera filters for a newly selected station', () => {
    const tokyo = { ...view, filters: { ...CITIES.tokyo.defaultFilters, hasLiveCamera: true },
      hideFloodRisk: true, hideHighSeismic: true, selectedStation: 'old-station' };
    const url = new URL(guideMapHref('/?s=shibuya', 'tokyo', tokyo), 'https://city-rating.test');
    expect(decodeParamsToState(url.searchParams, 'tokyo')).toMatchObject({ selectedStation: 'shibuya',
      hideHighSeismic: true, hideFloodRisk: true, filters: { hasLiveCamera: true } });
  });
  it('never turns an arbitrary URL into a return destination', () => {
    expect(() => guideMapHref('https://evil.example/bangkok?s=st.asok', 'bangkok', view)).toThrow();
    expect(() => guideMapHref('/other?s=st.asok', 'bangkok', view)).toThrow();
  });
});
