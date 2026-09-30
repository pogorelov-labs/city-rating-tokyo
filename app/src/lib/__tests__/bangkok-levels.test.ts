/**
 * Bangkok's three levels of detail: districts → station areas → 200 m grid.
 *
 * Covers the typed selection keys, the level in share links and the store,
 * the generated station-area data, and the packed grid (synthetic cases for
 * the decoder / scoring / dealbreakers, plus the committed file itself —
 * a stale or mis-packed grid would only show up as a wrong-looking map).
 */
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';

import stationsData from '@/data/bangkok/stations.json';
import stationGeometry from '@/data/bangkok/station-geometry.json';
import railData from '@/data/bangkok/rail.json';
import meta from '@/data/bangkok/meta.json';
import { cellKey, parseAreaKey, stationAreaKey } from '../area-key';
import { CITIES, areaPath, isAreaLevel } from '../cities';
import { decodeParamsToState, encodeStateToParams, selectUrlView } from '../url-state';
import { getCityActions, initialCityState, useAppStore } from '../store';
import { matchArea } from '../station-name';
import {
  GRID_HEADER,
  cellAt,
  cellBounds,
  cellCenter,
  cellInfo,
  countPassing,
  decodeGrid,
  gridAnchors,
  gridHotspots,
  passMask,
  scoreCells,
  type BangkokGrid,
  type GridDistrict,
  type GridHeader,
} from '../bangkok-grid';
import { getBangkokMapDistricts, getBangkokMapStationAreas, getBangkokStationAreaThumbnails } from '../bangkok-data';
import {
  DEFAULT_WEIGHTS,
  RATING_LABELS,
  type RailStation,
  type StationArea,
  type StationRatings,
  type WeightConfig,
} from '../types';

const RATING_KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];
const areas = (stationsData as unknown as { areas: StationArea[] }).areas;
const rail = railData as unknown as { stations: RailStation[] };
const geometry = stationGeometry as unknown as Record<string, { polygons: unknown[]; bbox: [[number, number], [number, number]] }>;

// ─── keys, URL, store ─────────────────────────────────────────────────────

describe('typed area keys', () => {
  it('round-trips districts, station areas and cells', () => {
    expect(parseAreaKey('watthana')).toEqual({ kind: 'district', id: 'watthana', index: null });
    expect(parseAreaKey(stationAreaKey('phaya-thai'))).toEqual({ kind: 'station', id: 'phaya-thai', index: null });
    expect(parseAreaKey(cellKey(41873))).toEqual({ kind: 'cell', id: 'cell.41873', index: 41873 });
    expect(parseAreaKey('cell.nope').index).toBeNull();
  });

  it('maps keys to pages', () => {
    expect(areaPath('bangkok', 'watthana')).toBe('/bangkok/district/watthana');
    expect(areaPath('bangkok', 'st.asok')).toBe('/bangkok/station/asok');
    expect(areaPath('bangkok', 'cell.12')).toBe('/bangkok');
    expect(areaPath('tokyo', 'shibuya')).toBe('/station/shibuya');
  });
});

describe('level of detail', () => {
  beforeEach(() => {
    useAppStore.setState((s) => ({
      cities: { ...s.cities, tokyo: initialCityState('tokyo'), bangkok: initialCityState('bangkok') },
    }));
  });

  it('is configured per city', () => {
    expect(CITIES.tokyo.levels).toEqual(['station']);
    expect(CITIES.bangkok.levels).toEqual(['district', 'station', 'grid']);
    expect(isAreaLevel('bangkok', 'grid')).toBe(true);
    expect(isAreaLevel('tokyo', 'grid')).toBe(false);
    expect(initialCityState('bangkok').level).toBe('district');
    expect(initialCityState('tokyo').level).toBe('station');
  });

  it('is in share links only when it is not the default', () => {
    const base = { ...selectUrlView(useAppStore.getState(), 'bangkok') };
    expect(encodeStateToParams(base, 'bangkok').has('lv')).toBe(false);
    const grid = encodeStateToParams({ ...base, level: 'grid', selectedStation: 'cell.41873' }, 'bangkok');
    expect(grid.toString()).toBe('lv=grid&s=cell.41873'); // '.' needs no escaping
    expect(decodeParamsToState(new URLSearchParams('lv=station&s=st.asok'), 'bangkok')).toMatchObject({
      level: 'station',
      selectedStation: 'st.asok',
    });
    // Tokyo has no finer level; an injected lv is ignored.
    expect(decodeParamsToState(new URLSearchParams('lv=grid'), 'tokyo').level).toBeUndefined();
    expect(decodeParamsToState(new URLSearchParams('lv=hexes'), 'bangkok').level).toBeUndefined();
  });

  it('switching level keeps the selection and drops the hover', () => {
    const a = getCityActions('bangkok');
    a.setSelectedStation('watthana');
    a.setHoveredStation('st.nana');
    a.setLevel('grid');
    const s = useAppStore.getState().cities.bangkok;
    expect(s.level).toBe('grid');
    expect(s.selectedStation).toBe('watthana');
    expect(s.hoveredStation).toBeNull();
    // Tokyo untouched.
    expect(useAppStore.getState().cities.tokyo.level).toBe('station');
  });

  it('hydrates the level from a link', () => {
    useAppStore.getState().hydrateFromUrl('bangkok', { level: 'station', selectedStation: 'st.siam' });
    expect(useAppStore.getState().cities.bangkok).toMatchObject({ level: 'station', selectedStation: 'st.siam' });
  });
});

describe('search', () => {
  it('ignores spacing in romanised names', () => {
    const silom = { name_en: 'Sala Daeng / Si Lom', name_jp: 'サラデーン / シーロム', name_th: 'ศาลาแดง / สีลม' };
    expect(matchArea(silom, 'silom').matched).toBe(true);
    expect(matchArea({ name_en: 'Thong Lo', name_jp: 'トンロー' }, 'thonglo').matched).toBe(true);
    expect(matchArea({ name_en: 'On Nut', name_jp: 'オンヌット' }, 'on nut').matched).toBe(true);
    // Two letters stay a plain substring search, no squashing.
    expect(matchArea({ name_en: 'Bang Na', name_jp: 'バーンナー' }, 'gn').matched).toBe(false);
  });
});

// ─── station areas (generated data) ───────────────────────────────────────

describe('Bangkok station areas', () => {
  const stationById = new Map(rail.stations.map((s) => [s.id, s]));
  const districtSlugs = new Set(getBangkokMapDistricts().map((d) => d.slug));
  const areaIds = new Set(areas.map((a) => a.id));

  it('cover every rail station inside Bangkok exactly once', () => {
    expect(areas.length).toBe(meta.station_area_count);
    const members = areas.flatMap((a) => a.station_ids);
    expect(new Set(members).size).toBe(members.length);
    const inside = rail.stations.filter((s) => s.district).map((s) => s.id);
    expect(new Set(members)).toEqual(new Set(inside));
    for (const s of rail.stations) {
      if (s.district) expect(areaIds.has(s.area!), s.id).toBe(true);
      else expect(s.area ?? null).toBeNull();
    }
  });

  it('merge interchanges of different lines, never neighbouring stops', () => {
    const byId = new Map(areas.map((a) => [a.id, a]));
    expect(byId.get('asok')!.station_ids).toEqual(['asok', 'sukhumvit']);
    expect(byId.get('sala-daeng')!.station_ids).toEqual(['sala-daeng', 'si-lom']);
    expect(byId.get('mo-chit')!.station_ids).toContain('chatuchak-park');
    // Chong Nonsi and Saint Louis are 436 m apart on one line: two areas.
    expect(byId.has('chong-nonsi') && byId.has('saint-louis')).toBe(true);
  });

  it.each(areas.map((a) => [a.id, a] as const))('%s is complete', (_id, a) => {
    for (const name of [a.name_en, a.name_th, a.name_jp]) expect(name.trim()).not.toBe('');
    for (const key of RATING_KEYS) {
      expect(Number.isInteger(a.ratings[key])).toBe(true);
      expect(a.ratings[key]).toBeGreaterThanOrEqual(1);
      expect(a.ratings[key]).toBeLessThanOrEqual(10);
    }
    expect(a.confidence.rent).toBe('editorial');
    expect(a.confidence.safety).toBe('editorial');
    expect(a.rent.two_bed!).toBeGreaterThan(a.rent.one_bed!);
    expect(Object.keys(a.transit_minutes).sort()).toEqual([...CITIES.bangkok.hubs].sort());
    expect(a.min_transit).toBe(Math.min(...Object.values(a.transit_minutes)));
    expect(districtSlugs.has(a.district)).toBe(true);
    const share = a.districts.reduce((sum, d) => sum + d.share, 0);
    expect(share).toBeGreaterThan(0.9);
    expect(share).toBeLessThanOrEqual(1.005); // shares are rounded to 0.001
    for (const d of a.districts) expect(districtSlugs.has(d.slug)).toBe(true);
    for (const n of a.neighbors) expect(areaIds.has(n), n).toBe(true);
    for (const id of a.station_ids) expect(stationById.get(id)?.area).toBe(a.id);
    expect(geometry[a.id]?.polygons.length).toBeGreaterThan(0);
    // Photo credits stay one line (Commons boilerplate is trimmed in the build).
    if (a.image) expect(a.image.artist.length).toBeLessThanOrEqual(60);
  });

  it('every station has a Japanese name', () => {
    for (const s of rail.stations.filter((x) => x.district)) expect(s.name_ja, s.id).toBeTruthy();
  });

  it('exposes typed map keys', () => {
    const map = getBangkokMapStationAreas();
    expect(map).toHaveLength(areas.length);
    for (const m of map) {
      expect(m.slug.startsWith('st.')).toBe(true);
      expect(m.line_colors).toHaveLength(m.line_ids!.length);
    }
    for (const key of Object.keys(getBangkokStationAreaThumbnails())) expect(key.startsWith('st.')).toBe(true);
  });
});

// ─── the 200 m grid ───────────────────────────────────────────────────────

/** 3 × 2 synthetic grid: row 0 = north. Cell 5 is outside Bangkok. */
function syntheticGrid(): BangkokGrid {
  const header: GridHeader = {
    ...GRID_HEADER,
    nx: 3,
    ny: 2,
    west: 100,
    east: 100.3,
    south: 13,
    north: 13.2,
    cells: 5,
    cell_m: 200,
    fields: ['food', 'nightlife', 'daily_essentials', 'gym_sports', 'vibe', 'green', 'transport', 'crowd', 'district', 'weight', 'hub_siam', 'hub_asok', 'station', 'station_dist', 'area'],
    districts: ['a', 'b'],
    stations: ['s1'],
    areas: ['s1'],
    scales: { weight: 250, station_dist_m: 20 },
  };
  const values: Record<string, number[]> = {
    food: [10, 5, 1, 7, 3, 0],
    nightlife: [10, 5, 1, 7, 3, 0],
    daily_essentials: [10, 5, 1, 7, 3, 0],
    gym_sports: [10, 5, 1, 7, 3, 0],
    vibe: [10, 5, 1, 7, 3, 0],
    green: [10, 5, 1, 7, 3, 0],
    transport: [10, 5, 1, 7, 3, 0],
    crowd: [10, 5, 1, 7, 3, 0],
    district: [1, 1, 2, 2, 2, 0],
    weight: [250, 250, 25, 250, 200, 0],
    hub_siam: [10, 40, 90, 20, 60, 0],
    hub_asok: [15, 30, 80, 25, 70, 0],
    station: [1, 1, 1, 1, 1, 0],
    station_dist: [10, 60, 255, 20, 30, 0],
    area: [1, 0, 0, 1, 0, 0],
  };
  // Encode like the build: per-row delta mod 256.
  const raw = new Uint8Array(header.fields.length * 6);
  header.fields.forEach((f, k) => {
    for (let r = 0; r < 2; r++) {
      let prev = 0;
      for (let c = 0; c < 3; c++) {
        const v = values[f][r * 3 + c];
        raw[k * 6 + r * 3 + c] = (v - prev + 256) % 256;
        prev = v;
      }
    }
  });
  return decodeGrid(raw, header);
}

const DISTRICTS: GridDistrict[] = [
  { ratings: { ...Object.fromEntries(RATING_KEYS.map((k) => [k, 5])), rent: 2, safety: 8 } as StationRatings, rent_1k: 30_000 },
  { ratings: { ...Object.fromEntries(RATING_KEYS.map((k) => [k, 5])), rent: 9, safety: 6 } as StationRatings, rent_1k: 10_000 },
];

describe('grid decoding and geometry', () => {
  const g = syntheticGrid();

  it('undoes the row delta and lists inside cells', () => {
    expect(Array.from(g.planes.food)).toEqual([10, 5, 1, 7, 3, 0]);
    expect(Array.from(g.cells)).toEqual([0, 1, 2, 3, 4]);
  });

  it('finds the cell under a point, north row first', () => {
    expect(cellAt(g, 13.15, 100.05)).toBe(0);
    expect(cellAt(g, 13.05, 100.15)).toBe(4);
    expect(cellAt(g, 13.05, 100.25)).toBe(-1); // outside Bangkok
    expect(cellAt(g, 12.9, 100.05)).toBe(-1); // outside the bbox
    const [[s, w], [n, e]] = cellBounds(g.header, 4);
    expect([s, w, n, e].map((x) => +x.toFixed(6))).toEqual([13, 100.1, 13.1, 100.2]);
    expect(cellCenter(g.header, 4).map((x) => +x.toFixed(6))).toEqual([13.05, 100.15]);
  });

  it('reads a cell with its district estimates', () => {
    const info = cellInfo(g, 2, DISTRICTS)!;
    expect(info.districtSlug).toBe('b');
    expect(info.ratings.rent).toBe(9);
    expect(info.ratings.safety).toBe(6);
    expect(info.minCommute).toBe(80);
    expect(info.stationDistanceM).toBeNull(); // 255 = beyond 5 km
    expect(info.weight).toBeCloseTo(0.1);
    expect(cellInfo(g, 0, DISTRICTS)!.areaId).toBe('s1');
    expect(cellInfo(g, 5, DISTRICTS)).toBeNull();
  });
});

describe('grid scoring, dealbreakers, best spots', () => {
  const g = syntheticGrid();
  const equal = Object.fromEntries(Object.keys(DEFAULT_WEIGHTS).map((k) => [k, 10])) as unknown as WeightConfig;

  it('scores like calculateWeightedScore, NaN outside', () => {
    const s = scoreCells(g, equal, DISTRICTS);
    // cell 0: eight local 10s + rent 2 + safety 8 → 90 / 10
    expect(s[0]).toBe(9);
    expect(Number.isNaN(s[5])).toBe(true);
    const onlyRent = { ...Object.fromEntries(Object.keys(DEFAULT_WEIGHTS).map((k) => [k, 0])), rent: 1 } as unknown as WeightConfig;
    expect(scoreCells(g, onlyRent, DISTRICTS)[2]).toBe(9);
  });

  it('anchors follow resident weight', () => {
    const s = scoreCells(g, equal, DISTRICTS);
    const a = gridAnchors(g, s);
    expect(a.p5).toBeLessThanOrEqual(a.p50);
    expect(a.p50).toBeLessThanOrEqual(a.p95);
    // Cell 2 (weight 0.1) is the lowest score but barely counts.
    expect(a.p5).toBeGreaterThan(s[2]);
  });

  it('applies rent, commute and category minimums', () => {
    const d = CITIES.bangkok.defaultFilters;
    const all = passMask(g, { ...d, categoryMins: {} }, d, DISTRICTS);
    expect(countPassing(g, all).cells).toBe(5);
    const cheap = passMask(g, { ...d, maxRent: 20_000, categoryMins: {} }, d, DISTRICTS);
    expect(Array.from(cheap)).toEqual([0, 0, 1, 1, 1, 0]);
    const fast = passMask(g, { ...d, maxCommute: 30, categoryMins: {} }, d, DISTRICTS);
    expect(Array.from(fast)).toEqual([1, 1, 0, 1, 0, 0]);
    const foodie = passMask(g, { ...d, categoryMins: { food: 7, safety: 7 } }, d, DISTRICTS);
    expect(Array.from(foodie)).toEqual([1, 0, 0, 0, 0, 0]);
    expect(countPassing(g, foodie).km2).toBeCloseTo(0.04);
  });

  it('picks separated, built-up best spots', () => {
    const s = scoreCells(g, equal, DISTRICTS);
    const pass = passMask(g, { ...CITIES.bangkok.defaultFilters, categoryMins: {} }, CITIES.bangkok.defaultFilters, DISTRICTS);
    expect(gridHotspots(g, s, pass, 10, 0)).toEqual([0, 3, 1, 4]); // cell 2 is sparse
    // 250 m apart: 0 and 1 are neighbours (200 m), 0 and 4 are diagonal (283 m).
    expect(gridHotspots(g, s, pass, 10, 250)).toEqual([0, 4]);
  });
});

describe('the committed grid file', () => {
  const file = resolve(__dirname, '../../../public', GRID_HEADER.file.replace(/^\//, ''));
  const packed = readFileSync(file);
  const grid = decodeGrid(new Uint8Array(gunzipSync(packed)), GRID_HEADER);

  it('matches its header', () => {
    expect(packed.length).toBe(GRID_HEADER.bytes);
    expect(grid.cells.length).toBe(GRID_HEADER.cells);
    expect(GRID_HEADER.cells).toBe(meta.grid_cell_count);
    expect(GRID_HEADER.districts).toEqual(getBangkokMapDistricts().map((d) => d.slug));
    expect(GRID_HEADER.stations).toEqual(rail.stations.map((s) => s.id));
    expect(GRID_HEADER.areas).toEqual(areas.map((a) => a.id));
  });

  it('holds ratings 1–10 in every inside cell', () => {
    for (const key of ['food', 'transport', 'crowd', 'green'] as const) {
      const plane = grid.planes[key];
      for (const i of grid.cells) {
        expect(plane[i]).toBeGreaterThanOrEqual(1);
        expect(plane[i]).toBeLessThanOrEqual(10);
      }
    }
  });

  it('puts Siam station in the Siam area of Pathum Wan, next to the Siam hub', () => {
    const siam = rail.stations.find((s) => s.id === 'siam')!;
    const i = cellAt(grid, siam.lat, siam.lng);
    const districts = getBangkokMapDistricts().map((d) => ({ ratings: d.ratings!, rent_1k: d.rent_1k }));
    const info = cellInfo(grid, i, districts)!;
    expect(info.districtSlug).toBe('pathum-wan');
    expect(info.areaId).toBe('siam');
    expect(info.stationId).toBe('siam');
    expect(info.stationDistanceM!).toBeLessThanOrEqual(200);
    expect(info.hubMinutes.siam).toBeLessThanOrEqual(5);
    expect(info.ratings.food).toBeGreaterThanOrEqual(9);
  });
});
