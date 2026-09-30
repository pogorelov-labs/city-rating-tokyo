'use client';

import { useEffect, useSyncExternalStore } from 'react';
import gridHeader from '@/data/bangkok/grid.json';
import type { FilterState, StationRatings, WeightConfig } from './types';
import type { PercentileAnchors } from './scoring';

/**
 * Bangkok's 200 m grid in the browser (the finest of the three levels).
 *
 * scripts/bangkok/build.py packs ~39k cells into one gzip'd binary under
 * app/public (≈ 140 KB, content-hashed file name) plus a small JSON header
 * bundled here. It is fetched only when someone opens the grid level.
 *
 * Layout: one uint8 plane per field over the whole nx × ny bounding box,
 * rows north → south, 0 = outside Bangkok, each row delta-coded mod 256.
 * The grid is regular in latitude / longitude (the build uses a local
 * equirectangular projection), so a cell index is plain arithmetic.
 *
 * Eight categories are rated per cell (resident-weighted percentile across
 * the city); rent and safety are the cell's district estimates.
 */

export interface GridHeader {
  version: number;
  file: string;
  bytes: number;
  cell_m: number;
  nx: number;
  ny: number;
  west: number;
  south: number;
  east: number;
  north: number;
  cells: number;
  fields: string[];
  scales: { weight: number; station_dist_m: number };
  districts: string[];
  stations: string[];
  areas: string[];
  medians: Record<keyof StationRatings, number>;
  default_anchors: PercentileAnchors;
  data_date: string;
}

export const GRID_HEADER = gridHeader as unknown as GridHeader;

/** A cell is "near" a station within this straight-line distance (≈ 14 min
 *  on foot) — the same radius that bounds a station area. */
export const NEAR_STATION_M = 800;

/** Rated per cell; `rent` and `safety` come from the district. */
export const GRID_LOCAL_KEYS = [
  'transport',
  'daily_essentials',
  'food',
  'green',
  'gym_sports',
  'vibe',
  'nightlife',
  'crowd',
] as const satisfies readonly (keyof StationRatings)[];

export interface BangkokGrid {
  header: GridHeader;
  planes: Record<string, Uint8Array>;
  /** Row-major indices of the cells inside Bangkok. */
  cells: Uint32Array;
}

/** What the grid needs to know about a district: its index in `header.districts`. */
export interface GridDistrict {
  ratings: StationRatings;
  rent_1k: number | null;
}

// ─── decoding ────────────────────────────────────────────────────────────

export function decodeGrid(raw: Uint8Array, header: GridHeader): BangkokGrid {
  const { nx, ny, fields } = header;
  const size = nx * ny;
  if (raw.length !== size * fields.length) {
    throw new Error(`Bangkok grid: ${raw.length} bytes, expected ${size * fields.length}`);
  }
  const planes: Record<string, Uint8Array> = {};
  fields.forEach((name, k) => {
    const src = raw.subarray(k * size, (k + 1) * size);
    const out = new Uint8Array(size);
    for (let r = 0; r < ny; r++) {
      const o = r * nx;
      let acc = 0;
      for (let c = 0; c < nx; c++) {
        acc = (acc + src[o + c]) & 0xff;
        out[o + c] = acc;
      }
    }
    planes[name] = out;
  });
  const district = planes.district;
  const inside: number[] = [];
  for (let i = 0; i < size; i++) if (district[i]) inside.push(i);
  return { header, planes, cells: Uint32Array.from(inside) };
}

async function gunzip(data: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([data as BlobPart]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function fetchGrid(): Promise<BangkokGrid> {
  const res = await fetch(GRID_HEADER.file);
  if (!res.ok) throw new Error(`Bangkok grid: HTTP ${res.status}`);
  let bytes: Uint8Array = new Uint8Array(await res.arrayBuffer());
  // The file is gzip'd by the build; a proxy that also compresses in transit
  // is undone by fetch itself. Check the magic rather than trusting headers.
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) bytes = await gunzip(bytes);
  return decodeGrid(bytes, GRID_HEADER);
}

// ─── loading (one fetch per page, shared by the map and the side panel) ───

interface GridSnapshot {
  grid: BangkokGrid | null;
  error: boolean;
}

const SERVER_SNAPSHOT: GridSnapshot = { grid: null, error: false };
let snapshot: GridSnapshot = SERVER_SNAPSHOT;
let loading: Promise<void> | null = null;
const listeners = new Set<() => void>();

function publish(next: GridSnapshot) {
  snapshot = next;
  listeners.forEach((l) => l());
}

export function ensureBangkokGrid(): Promise<void> {
  if (snapshot.grid) return Promise.resolve();
  if (!loading) {
    loading = fetchGrid().then(
      (grid) => publish({ grid, error: false }),
      (err) => {
        console.error(err);
        loading = null; // allow a retry on the next request
        publish({ grid: null, error: true });
      },
    );
  }
  return loading;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The decoded grid once loaded; starts the download when `enabled`. */
export function useBangkokGrid(enabled: boolean): GridSnapshot {
  const state = useSyncExternalStore(subscribe, () => snapshot, () => SERVER_SNAPSHOT);
  useEffect(() => {
    if (enabled) void ensureBangkokGrid();
  }, [enabled]);
  return state;
}

// ─── geometry ─────────────────────────────────────────────────────────────

export type LatLngPair = [number, number];

/** Cell index under a point, or -1 outside the grid / outside Bangkok. */
export function cellAt(grid: BangkokGrid, lat: number, lng: number): number {
  const h = grid.header;
  const c = Math.floor(((lng - h.west) / (h.east - h.west)) * h.nx);
  const r = Math.floor(((h.north - lat) / (h.north - h.south)) * h.ny);
  if (c < 0 || c >= h.nx || r < 0 || r >= h.ny) return -1;
  const i = r * h.nx + c;
  return grid.planes.district[i] ? i : -1;
}

export function cellBounds(h: GridHeader, i: number): [LatLngPair, LatLngPair] {
  const r = Math.floor(i / h.nx);
  const c = i % h.nx;
  const dLat = (h.north - h.south) / h.ny;
  const dLng = (h.east - h.west) / h.nx;
  const north = h.north - r * dLat;
  const west = h.west + c * dLng;
  return [
    [north - dLat, west],
    [north, west + dLng],
  ];
}

export function cellCenter(h: GridHeader, i: number): LatLngPair {
  const [[s, w], [n, e]] = cellBounds(h, i);
  return [(s + n) / 2, (w + e) / 2];
}

/** Straight-line distance between two cells in metres. */
function cellDistanceM(h: GridHeader, a: number, b: number): number {
  const dr = Math.floor(a / h.nx) - Math.floor(b / h.nx);
  const dc = (a % h.nx) - (b % h.nx);
  return Math.hypot(dr, dc) * h.cell_m;
}

// ─── per-cell values ──────────────────────────────────────────────────────

export interface CellInfo {
  index: number;
  ratings: StationRatings;
  districtSlug: string;
  districtIndex: number;
  /** 0.1 (empty land / water) … 1 (fully built-up), the resident weight. */
  weight: number;
  hubMinutes: Record<string, number>;
  minCommute: number;
  /** Nearest rail station (any, also just outside Bangkok) and its distance. */
  stationId: string | null;
  stationDistanceM: number | null;
  /** Station area this cell belongs to (≤ 800 m from its nearest rated station). */
  areaId: string | null;
}

export function gridHubs(h: GridHeader): string[] {
  return h.fields.filter((f) => f.startsWith('hub_')).map((f) => f.slice(4));
}

export function cellInfo(grid: BangkokGrid, i: number, districts: readonly GridDistrict[]): CellInfo | null {
  const p = grid.planes;
  const d = p.district[i];
  if (!d) return null;
  const district = districts[d - 1];
  const h = grid.header;
  const hubMinutes: Record<string, number> = {};
  for (const hub of gridHubs(h)) hubMinutes[hub] = p[`hub_${hub}`][i];
  const stationRaw = p.station[i];
  const distRaw = p.station_dist[i];
  const ratings = {} as StationRatings;
  for (const k of GRID_LOCAL_KEYS) ratings[k] = p[k][i];
  ratings.rent = district?.ratings.rent ?? 5;
  ratings.safety = district?.ratings.safety ?? 5;
  return {
    index: i,
    ratings,
    districtSlug: h.districts[d - 1],
    districtIndex: d - 1,
    weight: p.weight[i] / h.scales.weight,
    hubMinutes,
    minCommute: Math.min(...Object.values(hubMinutes)),
    stationId: stationRaw ? h.stations[stationRaw - 1] : null,
    stationDistanceM: distRaw === 255 ? null : distRaw * h.scales.station_dist_m,
    areaId: p.area[i] ? h.areas[p.area[i] - 1] : null,
  };
}

// ─── scoring, filtering, ranking ──────────────────────────────────────────

/**
 * Weighted score for every cell, rounded like `calculateWeightedScore`
 * (NaN outside Bangkok). ~40k cells × 10 categories: a few milliseconds.
 */
export function scoreCells(grid: BangkokGrid, weights: WeightConfig, districts: readonly GridDistrict[]): Float32Array {
  const size = grid.header.nx * grid.header.ny;
  const out = new Float32Array(size).fill(NaN);
  let total = 0;
  for (const w of Object.values(weights)) if (w > 0) total += w;
  if (total === 0) {
    for (const i of grid.cells) out[i] = 0;
    return out;
  }
  const local = GRID_LOCAL_KEYS.filter((k) => weights[k] > 0).map((k) => [grid.planes[k], weights[k]] as const);
  const districtPart = districts.map(
    (d) => (weights.rent > 0 ? d.ratings.rent * weights.rent : 0) + (weights.safety > 0 ? d.ratings.safety * weights.safety : 0),
  );
  const dist = grid.planes.district;
  for (const i of grid.cells) {
    let sum = districtPart[dist[i] - 1] ?? 0;
    for (const [plane, w] of local) sum += plane[i] * w;
    out[i] = Math.round((sum / total) * 10) / 10;
  }
  return out;
}

/**
 * p5 / p50 / p95 of the cell scores by cumulative resident weight — the grid
 * counterpart of `computeCompositeAnchors`. Scores come in 0.1 steps, so a
 * 101-bucket histogram replaces sorting.
 */
export function gridAnchors(grid: BangkokGrid, scores: Float32Array): PercentileAnchors {
  const hist = new Float64Array(101);
  const weight = grid.planes.weight;
  let total = 0;
  for (const i of grid.cells) {
    const s = scores[i];
    if (Number.isNaN(s)) continue;
    const w = weight[i];
    hist[Math.max(0, Math.min(100, Math.round(s * 10)))] += w;
    total += w;
  }
  if (total === 0) return { p5: 1, p50: 5.5, p95: 10 };
  const pick = (p: number) => {
    let acc = 0;
    for (let b = 0; b <= 100; b++) {
      acc += hist[b];
      if (acc >= total * p) return b / 10;
    }
    return 10;
  };
  return { p5: pick(0.05), p50: pick(0.5), p95: pick(0.95) };
}

/**
 * 1 where a cell passes the dealbreakers, 0 where it fails (and outside).
 * Same semantics as `dealbreakerReasons`: rent is the district estimate,
 * commute the cell's fastest hub, category minimums use the cell's ratings.
 */
export function passMask(
  grid: BangkokGrid,
  filters: FilterState,
  defaults: FilterState,
  districts: readonly GridDistrict[],
): Uint8Array {
  const size = grid.header.nx * grid.header.ny;
  const out = new Uint8Array(size);
  const p = grid.planes;
  const hubs = gridHubs(grid.header).map((hub) => p[`hub_${hub}`]);
  const rentMax = filters.maxRent < defaults.maxRent ? filters.maxRent : Infinity;
  const rentMin = filters.minRent > defaults.minRent ? filters.minRent : -Infinity;
  const commuteMax = filters.maxCommute < defaults.maxCommute ? filters.maxCommute : Infinity;
  const commuteMin = filters.minCommute > defaults.minCommute ? filters.minCommute : -Infinity;
  const mins = Object.entries(filters.categoryMins).filter(([, v]) => v != null) as [keyof StationRatings, number][];
  const districtOk = districts.map((d) => {
    if (d.rent_1k !== null && (d.rent_1k > rentMax || d.rent_1k < rentMin)) return false;
    return mins.every(([k, min]) => (k === 'rent' || k === 'safety' ? d.ratings[k] >= min : true));
  });
  const localMins = mins.filter(([k]) => k !== 'rent' && k !== 'safety').map(([k, min]) => [p[k], min] as const);
  const checkCommute = commuteMax !== Infinity || commuteMin !== -Infinity;
  for (const i of grid.cells) {
    if (!districtOk[p.district[i] - 1]) continue;
    let ok = true;
    for (const [plane, min] of localMins) {
      if (plane[i] < min) {
        ok = false;
        break;
      }
    }
    if (ok && checkCommute) {
      let best = 255;
      for (const hp of hubs) if (hp[i] < best) best = hp[i];
      ok = best <= commuteMax && best >= commuteMin;
    }
    if (ok) out[i] = 1;
  }
  return out;
}

/** Passing cells and the area they cover (each cell is cell_m²). */
export function countPassing(grid: BangkokGrid, pass: Uint8Array): { cells: number; km2: number } {
  let n = 0;
  for (const i of grid.cells) n += pass[i];
  return { cells: n, km2: (n * grid.header.cell_m * grid.header.cell_m) / 1e6 };
}

/**
 * The best places to live under the current weights: the top-scoring
 * built-up cells that pass the dealbreakers, at least `minSeparationM`
 * apart so the list names different neighbourhoods instead of ten adjacent
 * cells of one. Sparse cells (weight < 0.5 — fields, water) are skipped.
 */
export function gridHotspots(
  grid: BangkokGrid,
  scores: Float32Array,
  pass: Uint8Array,
  count = 10,
  minSeparationM = 1500,
): number[] {
  const buckets: number[][] = Array.from({ length: 101 }, () => []);
  const weight = grid.planes.weight;
  const dense = grid.header.scales.weight * 0.5;
  for (const i of grid.cells) {
    if (!pass[i] || weight[i] < dense || Number.isNaN(scores[i])) continue;
    buckets[Math.round(scores[i] * 10)].push(i);
  }
  const picked: number[] = [];
  for (let b = 100; b >= 0 && picked.length < count; b--) {
    // Denser cells first within a score step: they are where people live.
    const bucket = buckets[b].sort((x, y) => weight[y] - weight[x]);
    for (const i of bucket) {
      if (picked.every((j) => cellDistanceM(grid.header, i, j) >= minSeparationM)) {
        picked.push(i);
        if (picked.length >= count) break;
      }
    }
  }
  return picked;
}
