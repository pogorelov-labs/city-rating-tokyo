/**
 * Multi-city plumbing: the city registry, per-city URL encoding, dealbreakers
 * with city defaults, the per-city store slices and Thai-aware naming/search.
 *
 * The load-bearing invariant: Tokyo behaviour must not change (its shared
 * links, defaults and store shape keep working), while Bangkok values — in
 * baht, with their own ranges — never leak into Tokyo and vice versa.
 */
import { describe, expect, it, beforeEach } from 'vitest';

import { CITIES, CITY_IDS, areaPath, formatRentShort, hasActiveFilters, isCityId } from '../cities';
import { decodeParamsToState, encodeStateToParams, selectUrlView } from '../url-state';
import { applyDealbreakers, dealbreakerReasons } from '../scoring';
import { getCityActions, initialCityState, useAppStore } from '../store';
import { matchArea, stationDisplayName, stationPrimaryName } from '../station-name';
import {
  DEFAULT_FILTERS,
  DEFAULT_WEIGHTS,
  PRESET_PROFILES,
  RATING_LABELS,
  type MapStation,
  type StationRatings,
} from '../types';

const RATING_KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];

const FIVES = Object.fromEntries(RATING_KEYS.map((k) => [k, 5])) as unknown as StationRatings;

function area(partial: Partial<MapStation>): MapStation & { score: number } {
  return {
    slug: 'x',
    name_en: 'X',
    name_jp: 'エックス',
    lat: 13.7,
    lng: 100.5,
    line_count: 1,
    ratings: FIVES,
    rent_1k: 15_000,
    min_transit: 30,
    elevation_m: null,
    seismic_risk_tier: null,
    score: 5,
    ...partial,
  };
}

describe('city registry', () => {
  it('has Tokyo and Bangkok with their unit of rating', () => {
    expect(CITY_IDS).toEqual(['tokyo', 'bangkok']);
    expect(CITIES.tokyo.unit).toBe('station');
    expect(CITIES.bangkok.unit).toBe('district');
    expect(isCityId('bangkok')).toBe(true);
    expect(isCityId('osaka')).toBe(false);
  });

  it('keeps Tokyo defaults identical to the shared schema constants', () => {
    expect(CITIES.tokyo.defaultFilters).toEqual(DEFAULT_FILTERS);
    expect(CITIES.tokyo.rent.min).toBe(DEFAULT_FILTERS.minRent);
    expect(CITIES.tokyo.rent.max).toBe(DEFAULT_FILTERS.maxRent);
  });

  it.each(CITY_IDS)('%s: defaults sit on the slider ranges and steps', (id) => {
    const c = CITIES[id];
    expect(c.defaultFilters.minRent).toBe(c.rent.min);
    expect(c.defaultFilters.maxRent).toBe(c.rent.max);
    expect(c.defaultFilters.minCommute).toBe(c.commute.min);
    expect(c.defaultFilters.maxCommute).toBe(c.commute.max);
    expect((c.rent.max - c.rent.min) % c.rent.step).toBe(0);
    expect((c.commute.max - c.commute.min) % c.commute.step).toBe(0);
    expect(c.hubs).toHaveLength(5);
  });

  it.each(CITY_IDS)('%s: every quick profile has in-range dealbreakers', (id) => {
    const c = CITIES[id];
    for (const p of PRESET_PROFILES) {
      const f = c.presetFilters[p.id];
      expect(f, `${id}/${p.id}`).toBeDefined();
      if (f.maxRent != null) {
        expect(f.maxRent).toBeGreaterThan(c.rent.min);
        expect(f.maxRent).toBeLessThan(c.rent.max);
      }
      if (f.maxCommute != null) expect(f.maxCommute).toBeLessThan(c.commute.max);
    }
  });

  it.each(CITY_IDS)('%s: medians cover every category and anchors are ordered', (id) => {
    const c = CITIES[id];
    expect(Object.keys(c.medians).sort()).toEqual([...RATING_KEYS].sort());
    expect(c.defaultAnchors.p5).toBeLessThan(c.defaultAnchors.p50);
    expect(c.defaultAnchors.p50).toBeLessThan(c.defaultAnchors.p95);
  });

  it('builds locale-agnostic detail paths', () => {
    expect(areaPath('tokyo', 'shibuya')).toBe('/station/shibuya');
    expect(areaPath('bangkok', 'watthana')).toBe('/bangkok/district/watthana');
  });
});

describe('formatRentShort', () => {
  it('keeps the Tokyo format', () => {
    expect(formatRentShort('tokyo', 120_000)).toBe('¥120k');
    expect(formatRentShort('tokyo', 85_400)).toBe('¥85k');
  });

  it('uses baht, with half-thousands below ฿10k', () => {
    expect(formatRentShort('bangkok', 32_000)).toBe('฿32k');
    expect(formatRentShort('bangkok', 8_500)).toBe('฿8.5k');
    expect(formatRentShort('bangkok', 9_000)).toBe('฿9k');
    expect(formatRentShort('bangkok', 8_300)).toBe('฿8.5k');
  });
});

describe('url state per city', () => {
  const bkkDefaults = CITIES.bangkok.defaultFilters;
  const view = (filters = bkkDefaults) => ({
    weights: { ...DEFAULT_WEIGHTS },
    filters: { ...filters, categoryMins: { ...filters.categoryMins } },
    selectedStation: null,
    compareStations: [] as string[],
    heatmapMode: false,
    heatmapDimension: 'composite',
  });

  it('omits Bangkok filters at their defaults', () => {
    expect(encodeStateToParams(view(), 'bangkok').toString()).toBe('');
  });

  it('round-trips a baht rent limit and a long commute', () => {
    const params = encodeStateToParams(view({ ...bkkDefaults, maxRent: 18_000, maxCommute: 75 }), 'bangkok');
    expect(params.get('mr')).toBe('18000');
    expect(params.get('mc')).toBe('75');
    expect(decodeParamsToState(params, 'bangkok').filters).toEqual({ maxRent: 18_000, maxCommute: 75 });
  });

  it('drops yen values on a Bangkok page and baht values on a Tokyo page', () => {
    expect(decodeParamsToState(new URLSearchParams('mr=150000'), 'bangkok').filters).toBeUndefined();
    expect(decodeParamsToState(new URLSearchParams('mr=18000'), 'tokyo').filters).toBeUndefined();
    // 75 min is a valid Bangkok commute but above Tokyo's 60-minute range
    expect(decodeParamsToState(new URLSearchParams('mc=75'), 'tokyo').filters).toBeUndefined();
  });

  it('ignores the live-camera flag where the city has no cameras', () => {
    expect(decodeParamsToState(new URLSearchParams('lc=1'), 'bangkok').filters).toBeUndefined();
    expect(decodeParamsToState(new URLSearchParams('lc=1'), 'tokyo').filters).toEqual({ hasLiveCamera: true });
  });

  it('flattens one city slice with the shared preferences', () => {
    const state = {
      weights: { ...DEFAULT_WEIGHTS, food: 40 },
      heatmapMode: true,
      heatmapDimension: 'food',
      cities: {
        tokyo: { ...initialCityState('tokyo'), selectedStation: 'shibuya' },
        bangkok: { ...initialCityState('bangkok'), selectedStation: 'watthana' },
      },
    };
    const v = selectUrlView(state, 'bangkok');
    expect(v.selectedStation).toBe('watthana');
    expect(v.weights.food).toBe(40);
    expect(v.filters.maxRent).toBe(bkkDefaults.maxRent);
  });
});

describe('dealbreakers with city defaults', () => {
  const d = CITIES.bangkok.defaultFilters;

  it('keeps every district when Bangkok filters are wide open', () => {
    const areas = [area({ rent_1k: 7_000 }), area({ slug: 'y', rent_1k: 38_000, min_transit: 100 })];
    expect(applyDealbreakers(areas, { ...d }, false, false, d)).toHaveLength(2);
    expect(hasActiveFilters('bangkok', { ...d }, { hideFloodRisk: false, hideHighSeismic: false })).toBe(false);
  });

  it('explains why a district is excluded', () => {
    const f = { ...d, maxRent: 25_000, maxCommute: 45, categoryMins: { safety: 7 } };
    const reasons = dealbreakerReasons(
      area({ rent_1k: 32_000, min_transit: 60, ratings: { ...FIVES, safety: 5 } }),
      f,
      false,
      false,
      d,
    );
    expect(reasons.map((r) => r.kind)).toEqual(['rentHigh', 'commuteLong', 'category']);
    expect(reasons[2]).toEqual({ kind: 'category', key: 'safety', min: 7 });
    expect(hasActiveFilters('bangkok', f, { hideFloodRisk: false, hideHighSeismic: false })).toBe(true);
  });

  it('treats the live-camera flag as active (map and counter agree)', () => {
    expect(
      hasActiveFilters('tokyo', { ...DEFAULT_FILTERS, hasLiveCamera: true }, { hideFloodRisk: false, hideHighSeismic: false }),
    ).toBe(true);
  });
});

describe('per-city store slices', () => {
  beforeEach(() => {
    useAppStore.setState({
      cities: { tokyo: initialCityState('tokyo'), bangkok: initialCityState('bangkok') },
      weights: { ...DEFAULT_WEIGHTS },
    });
  });

  it('starts each city at its own defaults', () => {
    const { cities } = useAppStore.getState();
    expect(cities.tokyo.filters.maxRent).toBe(300_000);
    expect(cities.bangkok.filters.maxRent).toBe(CITIES.bangkok.rent.max);
  });

  it('never leaks filters, selection or compare lists across cities', () => {
    const bkk = getCityActions('bangkok');
    bkk.setMaxRent(20_000);
    bkk.setSelectedStation('watthana');
    bkk.addCompareStation('watthana');
    bkk.addCompareStation('bang-rak');
    const { cities } = useAppStore.getState();
    expect(cities.bangkok.filters.maxRent).toBe(20_000);
    expect(cities.bangkok.compareStations).toEqual(['watthana', 'bang-rak']);
    expect(cities.tokyo.filters.maxRent).toBe(300_000);
    expect(cities.tokyo.selectedStation).toBeNull();
    expect(cities.tokyo.compareStations).toEqual([]);
  });

  it('shares weights between cities', () => {
    useAppStore.getState().setWeight('food', 33);
    expect(useAppStore.getState().weights.food).toBe(33);
  });

  it('hands out referentially stable actions per city', () => {
    expect(getCityActions('bangkok')).toBe(getCityActions('bangkok'));
    expect(getCityActions('bangkok')).not.toBe(getCityActions('tokyo'));
  });

  it('resets filters to the city defaults and caps compare at three', () => {
    const bkk = getCityActions('bangkok');
    bkk.setMaxRent(12_000);
    bkk.setCategoryMin('safety', 8);
    bkk.resetFilters();
    expect(useAppStore.getState().cities.bangkok.filters).toEqual({ ...CITIES.bangkok.defaultFilters, categoryMins: {} });
    for (const s of ['a', 'b', 'c', 'd']) bkk.addCompareStation(s);
    expect(useAppStore.getState().cities.bangkok.compareStations).toEqual(['a', 'b', 'c']);
  });

  it('hydrates a URL into the right city only', () => {
    useAppStore.getState().hydrateFromUrl('bangkok', { selectedStation: 'sathon', filters: { maxRent: 15_000 } });
    const { cities } = useAppStore.getState();
    expect(cities.bangkok.selectedStation).toBe('sathon');
    expect(cities.bangkok.filters.maxRent).toBe(15_000);
    expect(cities.tokyo.selectedStation).toBeNull();
  });
});

describe('names and search', () => {
  const watthana = {
    name_en: 'Watthana',
    name_jp: 'ワッタナー区',
    name_ru: 'Ваттхана',
    name_th: 'วัฒนา',
    aliases: ['Thong Lo', 'Ekkamai', 'Asok'],
  };
  const shibuya = { name_en: 'Shibuya', name_jp: '渋谷' };

  it('keeps Thai visible as the secondary name in every locale', () => {
    expect(stationDisplayName(watthana, 'en')).toEqual({ primary: 'Watthana', secondary: 'วัฒนา' });
    expect(stationDisplayName(watthana, 'ja')).toEqual({ primary: 'ワッタナー区', secondary: 'วัฒนา' });
    expect(stationDisplayName(watthana, 'ru')).toEqual({ primary: 'Ваттхана', secondary: 'วัฒนา' });
    expect(stationPrimaryName(watthana, 'ja')).toBe('ワッタナー区');
  });

  it('leaves Tokyo naming unchanged', () => {
    expect(stationDisplayName(shibuya, 'en')).toEqual({ primary: 'Shibuya', secondary: '渋谷' });
    expect(stationDisplayName(shibuya, 'ja')).toEqual({ primary: '渋谷', secondary: 'Shibuya' });
    expect(stationDisplayName(shibuya, 'ru')).toEqual({ primary: 'Shibuya', secondary: '渋谷' });
  });

  it('matches names in any script and reports alias hits', () => {
    expect(matchArea(watthana, 'watt')).toEqual({ matched: true });
    expect(matchArea(watthana, 'วัฒ')).toEqual({ matched: true });
    expect(matchArea(watthana, 'ваттх')).toEqual({ matched: true });
    expect(matchArea(watthana, 'thong')).toEqual({ matched: true, alias: 'Thong Lo' });
    expect(matchArea(watthana, 'silom')).toEqual({ matched: false });
    expect(matchArea(watthana, 'a')).toEqual({ matched: false });
  });
});
