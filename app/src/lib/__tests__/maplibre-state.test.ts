import { describe, expect, it, vi } from 'vitest';
import { FeatureStateCache } from '@/components/bangkok/maplibre/feature-state';
import { stationFeatures, stationIdsByArea } from '@/components/bangkok/maplibre/map-data';

describe('MapLibre paint state', () => {
  it('diffs updates, keeps interaction and rating fields independent, and replays after context loss', () => {
    const cache = new FeatureStateCache(), submit = vi.fn();
    cache.set('areas', 'asok', { color: 'green', opacity: .6 }, submit);
    expect(cache.set('areas', 'asok', { color: 'green', opacity: .6 }, submit)).toBe(false);
    cache.set('areas', 'asok', { selected: true }, submit);
    cache.set('areas', 'asok', { color: 'orange', opacity: .6 }, submit);
    expect(submit.mock.calls.map(([patch]) => patch)).toEqual([{ color: 'green', opacity: .6 }, { selected: true }, { color: 'orange' }]);
    cache.set('stations', 'asok', { selected: true }, submit);
    expect(submit).toHaveBeenCalledTimes(4);
    cache.clear();
    expect(cache.set('areas', 'asok', { selected: true }, submit)).toBe(true);
  });
  it('recognizes interchange connections across physical station IDs', () => {
    const ids = stationIdsByArea.get('st.asok')!;
    expect(ids).toContain('asok');
    expect(ids).toContain('sukhumvit');
    for (const id of ids) expect(stationFeatures.features.find((f) => f.id === id)?.properties?.interchange).toBe(true);
  });
});
