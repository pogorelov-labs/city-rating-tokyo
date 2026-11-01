import { describe, expect, it, vi } from 'vitest';
import { installMapLayers, RAIL_LAYERS } from '@/components/bangkok/maplibre/map-style';
import { FeatureStateCache } from '@/components/bangkok/maplibre/feature-state';
import { labelFeatures, stationFeatures, stationIdsByArea, stationTarget } from '@/components/bangkok/maplibre/map-data';
import { getBangkokMapDistricts, getBangkokMapStationAreas } from '@/lib/bangkok-data';
import { stationPrimaryName } from '@/lib/station-name';

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
  it('builds localized district and station-area labels from the same static population', () => {
    const districts = getBangkokMapDistricts(), areas = getBangkokMapStationAreas();
    const labels = labelFeatures([...districts, ...areas], (area) => stationPrimaryName(area, 'ja'));
    const asok = areas.find((area) => area.slug === 'st.asok')!;
    expect(labels.features).toHaveLength(districts.length + areas.length);
    expect(labels.features.find((feature) => feature.id === asok.slug)?.properties).toEqual({ kind: 'station', name: stationPrimaryName(asok, 'ja') });
    expect(labels.features.find((feature) => feature.id === districts[0].slug)?.properties?.kind).toBe('district');
  });
  it('installs station-area labels on the shared label source independently of rail', () => {
    const layers: { id: string; source?: string; minzoom?: number; layout?: { visibility?: string } }[] = [];
    const map = { addSource: vi.fn(), addLayer: vi.fn((layer) => layers.push(layer)), getLayer: vi.fn(), moveLayer: vi.fn() } as unknown as Parameters<typeof installMapLayers>[0];
    installMapLayers(map, { version: 8, sources: {}, layers: [] });
    expect(layers.find((layer) => layer.id === 'bkk-station-area-labels')).toMatchObject({ source: 'bkk-labels', minzoom: 12, layout: { visibility: 'none' } });
    expect(RAIL_LAYERS).not.toContain('bkk-station-area-labels');
  });
  it('does not treat unlinked station hits as background clicks', () => {
    const unlinked = stationFeatures.features.find((feature) => feature.id === 'bang-bamru')!;
    expect(stationTarget(unlinked.properties!, 'station')).toBeUndefined();
    expect(stationTarget(unlinked.properties!, 'grid')).toBeUndefined();
    expect(stationTarget({ key: 'st.asok', district: 'watthana' }, 'station')).toBe('st.asok');
    expect(stationTarget({ key: 'st.asok', district: 'watthana' }, 'district')).toBe('watthana');
    expect(stationTarget({ key: '', district: 'watthana' }, 'grid')).toBe('watthana');
  });
  it('recognizes interchange connections across physical station IDs', () => {
    const ids = stationIdsByArea.get('st.asok')!;
    expect(ids).toContain('asok');
    expect(ids).toContain('sukhumvit');
    for (const id of ids) expect(stationFeatures.features.find((f) => f.id === id)?.properties?.interchange).toBe(true);
  });
});
