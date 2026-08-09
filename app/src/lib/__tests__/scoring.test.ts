/**
 * Unit tests for the pure scoring functions in app/src/lib/scoring.ts.
 *
 * These guard the load-bearing math that turns raw ratings + weights into the
 * composite score shown on the map and station pages, plus the dealbreaker
 * filter logic. The rent constants mirror scripts/compute-ratings.py and MUST
 * stay in sync (cross-language parity is asserted in scripts/test_schema_parity.py).
 */
import { describe, expect, it } from 'vitest';

import {
  applyDealbreakers,
  calculateWeightedScore,
  computeCompositeAnchors,
  filterStations,
  rentToAffordability,
} from '../scoring';
import {
  DEFAULT_FILTERS,
  DEFAULT_WEIGHTS,
  type FilterState,
  type MapStation,
  type Station,
  type StationRatings,
  type WeightConfig,
} from '../types';

// Rent constants — kept in sync with scripts/compute-ratings.py:RENT_FLOOR/CEILING.
// scoring.ts declares these as module-private consts; we re-declare here so a
// test failure points clearly at the rent range contract rather than a magic
// number. If these literals drift from scoring.ts the parity test in Python
// will fail loudly.
const RENT_FLOOR = 80_000; // → affordability 10
const RENT_CEILING = 300_000; // → affordability 1

const FULL_RATINGS: StationRatings = {
  transport: 7,
  rent: 6,
  daily_essentials: 5,
  safety: 8,
  food: 9,
  green: 4,
  gym_sports: 3,
  vibe: 6,
  nightlife: 7,
  crowd: 5,
};

describe('rentToAffordability', () => {
  it('returns 10 at the rent floor', () => {
    expect(rentToAffordability({ '1k_1ldk': RENT_FLOOR, '2ldk': null, source: 'suumo', updated: '' })).toBe(10);
  });

  it('returns 1 at the rent ceiling', () => {
    expect(rentToAffordability({ '1k_1ldk': RENT_CEILING, '2ldk': null, source: 'suumo', updated: '' })).toBe(1);
  });

  it('clamps above the ceiling to 1', () => {
    expect(rentToAffordability({ '1k_1ldk': RENT_CEILING + 50_000, '2ldk': null, source: 'suumo', updated: '' })).toBe(1);
  });

  it('clamps below the floor to 10', () => {
    expect(rentToAffordability({ '1k_1ldk': 10_000, '2ldk': null, source: 'suumo', updated: '' })).toBe(10);
  });

  it('returns a midpoint value for the midpoint rent', () => {
    const mid = (RENT_FLOOR + RENT_CEILING) / 2;
    // t = 0.5 → 10 - 9*0.5 = 5.5 → rounds to 6 (Math.round banker's-ish; 5.5 → 6)
    expect(rentToAffordability({ '1k_1ldk': mid, '2ldk': null, source: 'suumo', updated: '' })).toBe(6);
  });

  it('returns null when both rent fields are missing', () => {
    expect(rentToAffordability({ '1k_1ldk': null, '2ldk': null, source: 'suumo', updated: '' })).toBeNull();
  });

  it('falls back to 2ldk when 1k_1ldk is missing', () => {
    expect(rentToAffordability({ '1k_1ldk': null, '2ldk': RENT_FLOOR, source: 'suumo', updated: '' })).toBe(10);
  });

  it('prefers 1k_1ldk over 2ldk when both are present', () => {
    // 1k_1ldk=ceiling (→1) should win over 2ldk=floor (→10)
    expect(
      rentToAffordability({ '1k_1ldk': RENT_CEILING, '2ldk': RENT_FLOOR, source: 'suumo', updated: '' }),
    ).toBe(1);
  });
});

describe('calculateWeightedScore', () => {
  it('returns the plain average when all weights are equal', () => {
    const weights: WeightConfig = {
      transport: 1, rent: 1, daily_essentials: 1, safety: 1, food: 1,
      green: 1, gym_sports: 1, vibe: 1, nightlife: 1, crowd: 1,
    };
    const sum = Object.values(FULL_RATINGS).reduce((a, b) => a + b, 0);
    const expected = Math.round((sum / 10) * 10) / 10;
    expect(calculateWeightedScore(FULL_RATINGS, weights)).toBe(expected);
  });

  it('drops a zero-weight dimension entirely from the average', () => {
    const onlyFood: WeightConfig = {
      transport: 0, rent: 0, daily_essentials: 0, safety: 0, food: 100,
      green: 0, gym_sports: 0, vibe: 0, nightlife: 0, crowd: 0,
    };
    expect(calculateWeightedScore(FULL_RATINGS, onlyFood)).toBe(FULL_RATINGS.food);
  });

  it('returns 0 when total weight is 0 (no divide-by-zero)', () => {
    const allZero: WeightConfig = {
      transport: 0, rent: 0, daily_essentials: 0, safety: 0, food: 0,
      green: 0, gym_sports: 0, vibe: 0, nightlife: 0, crowd: 0,
    };
    expect(calculateWeightedScore(FULL_RATINGS, allZero)).toBe(0);
  });

  it('produces a value rounded to one decimal place', () => {
    const score = calculateWeightedScore(FULL_RATINGS, DEFAULT_WEIGHTS);
    expect(score).toBe(Math.round(score * 10) / 10);
  });

  it('weights the food dimension heavier when its weight is increased', () => {
    const foodHeavy: WeightConfig = { ...DEFAULT_WEIGHTS, food: 100 };
    const baseline = calculateWeightedScore(FULL_RATINGS, DEFAULT_WEIGHTS);
    const boosted = calculateWeightedScore(FULL_RATINGS, foodHeavy);
    // food=9 is well above the default-weighted average, so cranking food up raises the score
    expect(boosted).toBeGreaterThan(baseline);
  });
});

describe('computeCompositeAnchors', () => {
  it('returns the documented fallback when no station has ratings', () => {
    const anchors = computeCompositeAnchors(
      [{ ratings: null }, { ratings: null }],
      DEFAULT_WEIGHTS,
    );
    expect(anchors).toEqual({ p5: 1, p50: 5.5, p95: 10 });
  });

  it('returns the fallback for an empty station array', () => {
    expect(computeCompositeAnchors([], DEFAULT_WEIGHTS)).toEqual({ p5: 1, p50: 5.5, p95: 10 });
  });

  it('returns equal p5/p50/p95 for a single station', () => {
    const score = calculateWeightedScore(FULL_RATINGS, DEFAULT_WEIGHTS);
    const anchors = computeCompositeAnchors(
      [{ ratings: FULL_RATINGS }],
      DEFAULT_WEIGHTS,
    );
    expect(anchors.p5).toBe(score);
    expect(anchors.p50).toBe(score);
    expect(anchors.p95).toBe(score);
  });

  it('honors the percentile ordering: p5 <= p50 <= p95', () => {
    const stations = Array.from({ length: 40 }, (_, i) => ({
      ratings: { ...FULL_RATINGS, food: (i % 10) + 1 } as StationRatings,
    }));
    const anchors = computeCompositeAnchors(stations, DEFAULT_WEIGHTS);
    expect(anchors.p5).toBeLessThanOrEqual(anchors.p50);
    expect(anchors.p50).toBeLessThanOrEqual(anchors.p95);
  });
});

describe('applyDealbreakers', () => {
  const baseStation: MapStation & { score: number | null } = {
    slug: 'shibuya',
    name_en: 'Shibuya',
    name_jp: '渋谷',
    lat: 35.658,
    lng: 139.701,
    line_count: 9,
    ratings: FULL_RATINGS,
    rent_1k: 150_000,
    min_transit: 5,
    elevation_m: 40,
    seismic_risk_tier: 'low',
    hasLiveCamera: false,
    score: 6,
  };

  it('passes everything through with default filters and no environment toggles', () => {
    const out = applyDealbreakers([baseStation], DEFAULT_FILTERS, false, false);
    expect(out).toHaveLength(1);
    // rentActive is false with default filters, so rentUnknown collapses to false (not undefined)
    expect(out[0].rentUnknown).toBe(false);
  });

  it('marks a station rentUnknown when the max-rent filter is active but rent is null', () => {
    const noRent = { ...baseStation, rent_1k: null };
    const filters: FilterState = { ...DEFAULT_FILTERS, maxRent: 120_000 };
    const out = applyDealbreakers([noRent], filters, false, false);
    expect(out).toHaveLength(1);
    expect(out[0].rentUnknown).toBe(true);
  });

  it('drops a station whose rent exceeds the max', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, maxRent: 120_000 };
    const out = applyDealbreakers([{ ...baseStation, rent_1k: 200_000 }], filters, false, false);
    expect(out).toHaveLength(0);
  });

  it('drops a station whose rent is below the min', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, minRent: 100_000 };
    const out = applyDealbreakers([{ ...baseStation, rent_1k: 90_000 }], filters, false, false);
    expect(out).toHaveLength(0);
  });

  it('drops a station whose commute exceeds the max', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, maxCommute: 20 };
    const out = applyDealbreakers([{ ...baseStation, min_transit: 35 }], filters, false, false);
    expect(out).toHaveLength(0);
  });

  it('drops a station below a category minimum', () => {
    const filters: FilterState = {
      ...DEFAULT_FILTERS,
      categoryMins: { safety: 8 },
    };
    const out = applyDealbreakers(
      [{ ...baseStation, ratings: { ...FULL_RATINGS, safety: 5 } }],
      filters,
      false,
      false,
    );
    expect(out).toHaveLength(0);
  });

  it('keeps a station meeting the category minimum', () => {
    const filters: FilterState = {
      ...DEFAULT_FILTERS,
      categoryMins: { safety: 8 },
    };
    const out = applyDealbreakers([baseStation], filters, false, false);
    expect(out).toHaveLength(1);
  });

  it('drops low-elevation stations when flood filter is on (< 5m)', () => {
    const lowStation = { ...baseStation, elevation_m: 3 };
    const out = applyDealbreakers([lowStation], DEFAULT_FILTERS, true, false);
    expect(out).toHaveLength(0);
  });

  it('keeps a station at exactly the 5m flood threshold', () => {
    const edgeStation = { ...baseStation, elevation_m: 5 };
    const out = applyDealbreakers([edgeStation], DEFAULT_FILTERS, true, false);
    expect(out).toHaveLength(1);
  });

  it('drops very_high seismic stations when the seismic filter is on', () => {
    const riskyStation = { ...baseStation, seismic_risk_tier: 'very_high' as const };
    const out = applyDealbreakers([riskyStation], DEFAULT_FILTERS, false, true);
    expect(out).toHaveLength(0);
  });

  it('keeps non-very_high seismic stations when the seismic filter is on', () => {
    const out = applyDealbreakers([baseStation], DEFAULT_FILTERS, false, true);
    expect(out).toHaveLength(1);
  });

  it('requires a live camera when hasLiveCamera filter is set', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, hasLiveCamera: true };
    expect(applyDealbreakers([baseStation], filters, false, false)).toHaveLength(0);
    expect(
      applyDealbreakers([{ ...baseStation, hasLiveCamera: true }], filters, false, false),
    ).toHaveLength(1);
  });
});

describe('filterStations', () => {
  const makeStation = (overrides: Partial<Station>): Station => ({
    slug: 'a',
    name_en: 'A',
    name_jp: 'A',
    lat: 0,
    lng: 0,
    lines: [],
    line_count: 1,
    prefecture: '13',
    ratings: FULL_RATINGS,
    rent_avg: { '1k_1ldk': 100_000, '2ldk': null, source: 'suumo', updated: '' },
    transit_minutes: { shibuya: 10, shinjuku: 15, tokyo: 20, ikebukuro: 25, shinagawa: 30 },
    ...overrides,
  } as Station);

  it('skips stations with null ratings', () => {
    const out = filterStations(
      [{ ...makeStation({}), ratings: null }],
      DEFAULT_WEIGHTS,
      {},
    );
    expect(out).toHaveLength(0);
  });

  it('sorts results by score descending', () => {
    const low = { ...FULL_RATINGS, food: 1 } as StationRatings;
    const high = { ...FULL_RATINGS, food: 10 } as StationRatings;
    const out = filterStations(
      [makeStation({ slug: 'low', ratings: low }), makeStation({ slug: 'high', ratings: high })],
      { ...DEFAULT_WEIGHTS, food: 100 },
      {},
    );
    expect(out[0].slug).toBe('high');
    expect(out[1].slug).toBe('low');
  });

  it('applies the maxRent filter', () => {
    const out = filterStations(
      [makeStation({ slug: 'cheap', rent_avg: { '1k_1ldk': 80_000, '2ldk': null, source: '', updated: '' } }),
       makeStation({ slug: 'pricey', rent_avg: { '1k_1ldk': 250_000, '2ldk': null, source: '', updated: '' } })],
      DEFAULT_WEIGHTS,
      { maxRent: 150_000 },
    );
    expect(out.map((s) => s.slug)).toEqual(['cheap']);
  });
});
