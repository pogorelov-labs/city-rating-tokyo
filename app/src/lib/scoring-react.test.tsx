import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { station } from '@/test/stations';
import { getCityActions, useAppStore } from './store';
import { DEFAULT_WEIGHTS, type StationRatings } from './types';
import { calculateWeightedScore } from './scoring';
import { ScoredAreasProvider, useScoredAreas } from './scoring-react';

vi.mock('./scoring', async (importOriginal) => {
  const original = await importOriginal<typeof import('./scoring')>();
  return { ...original, calculateWeightedScore: vi.fn(original.calculateWeightedScore) };
});

beforeEach(() => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  vi.mocked(calculateWeightedScore).mockClear();
});

function foodOnly() {
  const weights = { ...DEFAULT_WEIGHTS };
  for (const key of Object.keys(weights) as (keyof typeof weights)[]) weights[key] = key === 'food' ? 100 : 0;
  return weights;
}

function ratings(food: number): StationRatings {
  return { transport: 7, rent: 7, daily_essentials: 7, safety: 7, food,
    green: 7, gym_sports: 7, vibe: 7, nightlife: 7, crowd: 7 };
}

describe('useScoredAreas', () => {
  it('shares scores across consumers while keeping unfiltered anchors and unrated map areas', async () => {
    useAppStore.getState().setAllWeights(foodOnly());
    const areas = [
      station('high', { ratings: ratings(10), rent_1k: 100000 }),
      station('low', { ratings: ratings(2), rent_1k: 160000 }),
      station('unknown', { ratings: null, rent_1k: null }),
    ];
    function wrapper({ children }: { children: ReactNode }) {
      return <Providers><ScoredAreasProvider primaryAreas={areas}>{children}</ScoredAreasProvider></Providers>;
    }
    // Explicit level sharing survives separate serialized copies of the same
    // homepage props at the desktop/mobile client boundaries.
    const { result } = renderHook(() => [useScoredAreas(areas, 'primary'), useScoredAreas([...areas], 'primary')] as const, { wrapper });
    expect(result.current[0]).toBe(result.current[1]);
    expect(result.current[0].scored.map((area) => area.score)).toEqual([10, 2, null]);
    expect(calculateWeightedScore).toHaveBeenCalledTimes(2);
    expect(result.current[0].anchors).toEqual({ p5: 2, p50: 10, p95: 10 });
    expect(result.current[0].ranked.map((area) => area.slug)).toEqual(['high', 'low']);

    act(() => getCityActions('tokyo').setMaxRent(120000));
    expect(result.current[0]).toBe(result.current[1]);
    expect(result.current[0].passing.map(({ slug, rentUnknown }) => [slug, rentUnknown])).toEqual([
      ['high', false], ['unknown', true],
    ]);
    expect(result.current[0].ranked.map((area) => area.slug)).toEqual(['high']);
    expect(result.current[0].ratedCount).toBe(2);
    expect(result.current[0].anchors).toEqual({ p5: 2, p50: 10, p95: 10 });
    expect(calculateWeightedScore).toHaveBeenCalledTimes(2);

    act(() => useAppStore.getState().setAllWeights({ ...foodOnly(), food: 0, transport: 100 }));
    await waitFor(() => expect(result.current[0].scored.map((area) => area.score)).toEqual([7, 7, null]));
    expect(result.current[0]).toBe(result.current[1]);
    expect(result.current[0].anchors).toEqual({ p5: 7, p50: 7, p95: 7 });
    expect(calculateWeightedScore).toHaveBeenCalledTimes(4);
  });

  it('keeps equal-score ranking stable and provides independent Bangkok levels', () => {
    useAppStore.getState().setAllWeights(foodOnly());
    const districts = [station('district-a', { ratings: ratings(6) }), station('district-b', { ratings: ratings(6) })];
    const areas = [station('st.one', { ratings: ratings(9) })];
    function wrapper({ children }: { children: ReactNode }) {
      return <Providers city="bangkok"><ScoredAreasProvider primaryAreas={districts} stationAreas={areas}>
        {children}
      </ScoredAreasProvider></Providers>;
    }
    const { result } = renderHook(() => [useScoredAreas(districts), useScoredAreas(areas)] as const, { wrapper });
    expect(result.current[0].ranked.map((area) => area.slug)).toEqual(['district-a', 'district-b']);
    expect(result.current[1].ranked.map((area) => area.slug)).toEqual(['st.one']);
    expect(result.current[0].anchors).toEqual({ p5: 6, p50: 6, p95: 6 });
    expect(result.current[1].anchors).toEqual({ p5: 9, p50: 9, p95: 9 });
  });

  it('works for a standalone list outside the shared provider', () => {
    useAppStore.getState().setAllWeights(foodOnly());
    const areas = [station('standalone', { ratings: ratings(8) })];
    const { result } = renderHook(() => useScoredAreas(areas), { wrapper: Providers });
    expect(result.current.ranked.map(({ slug, score }) => [slug, score])).toEqual([['standalone', 8]]);
  });
});
