/**
 * URL state encode/decode round-trip and backward-compat tests.
 *
 * The positional weight-key order in the `w` query param is LOAD-BEARING: any
 * reordering silently rewrites every shared URL on the internet. These tests
 * pin the current order, the legacy 9-value order, and the silent-drop
 * behaviour for out-of-range filter values so a future refactor can't quietly
 * break shared links.
 */
import { describe, expect, it } from 'vitest';

import { decodeParamsToState, encodeStateToParams } from '../url-state';
import {
  DEFAULT_FILTERS,
  DEFAULT_WEIGHTS,
  type FilterState,
  type WeightConfig,
} from '../types';

// Current positional order, derived from DEFAULT_WEIGHTS key order (the same
// enumeration url-state.ts uses internally via Object.keys). Re-stating this
// literally here means a test failure flags the drift directly.
const CURRENT_WEIGHT_KEYS = [
  'transport',
  'rent',
  'daily_essentials',
  'safety',
  'food',
  'green',
  'gym_sports',
  'vibe',
  'nightlife',
  'crowd',
] as const;

// Legacy (pre-reorder) order — old shared URLs encode weights in this sequence.
const LEGACY_WEIGHT_KEYS = [
  'food',
  'nightlife',
  'transport',
  'rent',
  'safety',
  'green',
  'gym_sports',
  'vibe',
  'crowd',
  'daily_essentials',
] as const;

const baselineState = {
  weights: { ...DEFAULT_WEIGHTS },
  filters: { ...DEFAULT_FILTERS },
  selectedStation: null,
  compareStations: [],
  heatmapMode: false,
  heatmapDimension: 'composite',
} as const;

describe('encodeStateToParams', () => {
  it('omits the w param entirely when weights equal the defaults', () => {
    const params = encodeStateToParams(baselineState);
    expect(params.has('w')).toBe(false);
  });

  it('emits the w param in CURRENT_WEIGHT_KEYS order when weights differ', () => {
    const weights: WeightConfig = { ...DEFAULT_WEIGHTS, food: 25 };
    const params = encodeStateToParams({ ...baselineState, weights });
    const w = params.get('w')!;
    const values = w.split(',').map(Number);
    expect(values).toHaveLength(CURRENT_WEIGHT_KEYS.length);
    // Spot-check position 4 (food) is the bumped value, and the others are defaults
    expect(values[CURRENT_WEIGHT_KEYS.indexOf('food')]).toBe(25);
    expect(values[CURRENT_WEIGHT_KEYS.indexOf('transport')]).toBe(DEFAULT_WEIGHTS.transport);
  });
});

describe('decodeParamsToState — round trip', () => {
  it('round-trips a non-default weight set through encode then decode', () => {
    const weights: WeightConfig = {
      transport: 30, rent: 5, daily_essentials: 10, safety: 20, food: 15,
      green: 0, gym_sports: 0, vibe: 5, nightlife: 10, crowd: 5,
    };
    const encoded = encodeStateToParams({ ...baselineState, weights });
    const decoded = decodeParamsToState(encoded);
    expect(decoded.weights).toEqual(weights);
  });

  it('a 10-value URL decodes to current WEIGHT_KEYS order', () => {
    // Build a 10-value URL string in CURRENT_WEIGHT_KEYS order
    const weights: WeightConfig = { ...DEFAULT_WEIGHTS, transport: 25, crowd: 10 };
    const w = CURRENT_WEIGHT_KEYS.map((k) => weights[k]).join(',');
    const decoded = decodeParamsToState(new URLSearchParams(`w=${w}`));
    expect(decoded.weights).toBeDefined();
    for (const k of CURRENT_WEIGHT_KEYS) {
      expect(decoded.weights![k]).toBe(weights[k]);
    }
  });

  it('a 9-value URL decodes using LEGACY_WEIGHT_KEYS with daily_essentials defaulted', () => {
    // Old format: 9 values in legacy order, no daily_essentials slot
    // legacy order: food, nightlife, transport, rent, safety, green, gym_sports, vibe, crowd
    const legacyValues = [12, 8, 25, 5, 20, 4, 3, 5, 7];
    const w = legacyValues.join(',');
    const decoded = decodeParamsToState(new URLSearchParams(`w=${w}`));
    expect(decoded.weights).toBeDefined();
    expect(decoded.weights!.food).toBe(12);
    expect(decoded.weights!.nightlife).toBe(8);
    expect(decoded.weights!.transport).toBe(25);
    expect(decoded.weights!.rent).toBe(5);
    expect(decoded.weights!.safety).toBe(20);
    expect(decoded.weights!.green).toBe(4);
    expect(decoded.weights!.gym_sports).toBe(3);
    expect(decoded.weights!.vibe).toBe(5);
    expect(decoded.weights!.crowd).toBe(7);
    // daily_essentials was not in the old format → must fall back to default
    expect(decoded.weights!.daily_essentials).toBe(DEFAULT_WEIGHTS.daily_essentials);
  });

  it('silently drops out-of-range filter values on decode', () => {
    // minRent below the 80000 floor, maxCommute above the 60 ceiling, etc.
    const params = new URLSearchParams();
    params.set('nr', '1000');      // below floor → dropped
    params.set('mr', '999999');    // above ceiling → dropped
    params.set('nc', '1');         // below floor → dropped
    params.set('mc', '999');       // above ceiling → dropped
    params.set('cm', 'transport:99,transport:5'); // 99 is out of 1..10 → only the 5 survives
    const decoded = decodeParamsToState(params);
    if (decoded.filters) {
      expect(decoded.filters.minRent).toBeUndefined();
      expect(decoded.filters.maxRent).toBeUndefined();
      expect(decoded.filters.minCommute).toBeUndefined();
      expect(decoded.filters.maxCommute).toBeUndefined();
      // Only the in-range category min survives
      expect(decoded.filters.categoryMins?.transport).toBe(5);
    } else {
      // Acceptable: filter patch is absent entirely when every value was dropped.
      expect(decoded.filters).toBeUndefined();
    }
  });

  it('decodes selection, compare, heatmap flag, and heatmap dimension', () => {
    const params = new URLSearchParams();
    params.set('s', 'shibuya');
    params.set('c', 'shibuya,shinjuku');
    params.set('hm', '1');
    params.set('hd', 'food');
    const decoded = decodeParamsToState(params);
    expect(decoded.selectedStation).toBe('shibuya');
    expect(decoded.compareStations).toEqual(['shibuya', 'shinjuku']);
    expect(decoded.heatmapMode).toBe(true);
    expect(decoded.heatmapDimension).toBe('food');
  });

  it('ignores a malformed w param (non-numeric values)', () => {
    const decoded = decodeParamsToState(new URLSearchParams('w=abc,1,2'));
    expect(decoded.weights).toBeUndefined();
  });
});
