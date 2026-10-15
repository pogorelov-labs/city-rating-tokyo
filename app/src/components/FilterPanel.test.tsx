import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { station } from '@/test/stations';
import { getCityActions, useAppStore } from '@/lib/store';
import { CITIES, type CityId } from '@/lib/cities';
import { AreaListsProvider } from '@/lib/area-lists';
import { applyDealbreakers } from '@/lib/scoring';
import { PRESET_PROFILES, type MapStation } from '@/lib/types';
import FilterPanel from './FilterPanel';

// Grid loading/ranking is a separate data path; these tests exercise the real
// named-area scorer, city store, translations and controls without Leaflet.
vi.mock('next/dynamic', () => ({ default: () => () => null }));
vi.mock('@/lib/use-is-touch', () => ({ useIsTouch: () => false }));
beforeEach(() => useAppStore.setState(useAppStore.getInitialState(), true));
const areas = [
  station('affordable'), station('expensive', { rent_1k: 230000 }),
  station('flood', { elevation_m: 2 }), station('unrated', { ratings: null }),
];
function mount(city: CityId = 'tokyo', stations = areas, stationAreas: MapStation[] = []) {
  return render(<Providers city={city}>
    {city === 'tokyo' ? <FilterPanel stations={stations} /> : <AreaListsProvider lists={{ district: stations, station: stationAreas }}>
      <FilterPanel stations={stations} />
    </AreaListsProvider>}
  </Providers>);
}

describe('FilterPanel control wiring', () => {
  it('match count and ranked selection agree with the map dealbreaker population', async () => {
    const user = userEvent.setup();
    mount();
    expect(screen.getByText('3 stations')).toBeInTheDocument();
    act(() => getCityActions('tokyo').setMaxRent(150000));
    await user.click(screen.getByRole('checkbox', { name: /Hide flood-risk areas/ }));
    const state = useAppStore.getState().cities.tokyo;
    const visible = applyDealbreakers(areas.filter((s) => s.ratings).map((s) => ({ ...s, score: 7 })),
      state.filters, state.hideFloodRisk, state.hideHighSeismic, state.hideAdultZones, CITIES.tokyo.defaultFilters);
    expect(visible.map((s) => s.slug)).toEqual(['affordable']);
    expect(screen.getByText((_, node) => node?.tagName === 'SPAN' && node.textContent === '1 of 3 stations match')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(visible.length);
    await user.click(screen.getByRole('button', { name: /affordable/ }));
    expect(useAppStore.getState().cities.tokyo.selectedStation).toBe('affordable');
  });

  for (const city of ['tokyo', 'bangkok'] as const) {
    it(`${city}: presets reset old filters BEFORE applying local-unit dealbreakers`, async () => {
      const actions = getCityActions(city);
      actions.setMinRent(CITIES[city].rent.min + CITIES[city].rent.step);
      actions.setCategoryMin('food', 8);
      actions.setHasLiveCamera(true);
      mount(city, []);
      const seen: typeof useAppStore.getState extends () => infer S ? S[] : never = [];
      const unsub = useAppStore.subscribe((s) => seen.push(s));
      await userEvent.setup().click(screen.getByRole('button', { name: /Young Pro/ }));
      unsub();
      const resetAt = seen.findIndex((s) => JSON.stringify(s.cities[city].filters) === JSON.stringify(CITIES[city].defaultFilters));
      expect(resetAt).toBeGreaterThanOrEqual(0);
      expect(seen.slice(resetAt + 1).some((s) => s.cities[city].filters.maxRent === CITIES[city].presetFilters['young-pro'].maxRent)).toBe(true);
      expect(useAppStore.getState().cities[city].filters).toEqual({
        ...CITIES[city].defaultFilters, ...CITIES[city].presetFilters['young-pro'],
      });
      expect(useAppStore.getState().weights).toEqual(PRESET_PROFILES.find((p) => p.id === 'young-pro')!.weights);
      expect(useAppStore.getState().cities[city === 'tokyo' ? 'bangkok' : 'tokyo'].filters).toEqual(CITIES[city === 'tokyo' ? 'bangkok' : 'tokyo'].defaultFilters);
    });

    it(`${city}: low/high rent and commute thumbs cannot cross and keep a one-step gap`, () => {
      const { container } = mount(city, []);
      for (const field of ['rent', 'commute'] as const) {
        const config = CITIES[city][field];
        const [low, high] = container.querySelectorAll<HTMLInputElement>(`input[data-umami-event="filter-${field}"]`);
        fireEvent.change(low, { target: { value: config.max } });
        expect(Number(low.value)).toBe(config.max - config.step);
        fireEvent.change(high, { target: { value: config.min } });
        expect(Number(high.value)).toBe(config.max);
        fireEvent.change(low, { target: { value: config.min } });
        fireEvent.change(high, { target: { value: config.min } });
        expect(Number(high.value)).toBe(config.min + config.step);
      }
    });
  }

  it('uses district vs station-area counts/search/rent messages as Bangkok level changes', () => {
    const districts = [station('district', { rent_1k: 15000 })];
    const stationAreas = [station('st.one', { rent_1k: 12000 }), station('st.two', { rent_1k: 25000 })];
    mount('bangkok', districts, stationAreas);
    expect(screen.getByText('1 districts')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search district, area or station/)).toBeInTheDocument();
    act(() => getCityActions('bangkok').setLevel('station'));
    expect(screen.getByText('2 station areas')).toBeInTheDocument();
    expect(screen.getByText(/2 station areas mapped/)).toBeInTheDocument();
    act(() => getCityActions('bangkok').setMaxRent(20000));
    expect(screen.getByText((_, node) => node?.tagName === 'SPAN' && node.textContent === '1 of 2 station areas match')).toBeInTheDocument();
    act(() => getCityActions('bangkok').setMaxRent(5000));
    expect(screen.getAllByText(/No station areas match/)).toHaveLength(2);
  });
});
