/**
 * Integrity of the generated Bangkok data (scripts/bangkok/build.py output).
 *
 * The app trusts these JSON files at build time; a broken join (a station
 * pointing at a missing line, a district without geometry, a description
 * missing a locale) would only surface as a blank UI element. Catch it here.
 */
import { describe, expect, it } from 'vitest';

import districtsData from '@/data/bangkok/districts.json';
import geometryData from '@/data/bangkok/geometry.json';
import railData from '@/data/bangkok/rail.json';
import meta from '@/data/bangkok/meta.json';
import { CITIES } from '../cities';
import { RATING_LABELS, type District, type RailLine, type RailStation, type StationRatings } from '../types';
import { getBangkokMapDistricts, getBangkokSnippets } from '../bangkok-data';

const districts = (districtsData as unknown as { districts: District[] }).districts;
const geometry = geometryData as unknown as Record<
  string,
  { polygons: [number, number][][][]; bbox: [[number, number], [number, number]]; label: [number, number] }
>;
const rail = railData as unknown as { lines: (RailLine & { paths: [number, number][][] })[]; stations: RailStation[] };
const RATING_KEYS = Object.keys(RATING_LABELS) as (keyof StationRatings)[];
const LEVELS = ['strong', 'moderate', 'estimate', 'editorial'];
const slugs = new Set(districts.map((d) => d.slug));
const stationIds = new Set(rail.stations.map((s) => s.id));
const lineIds = new Set(rail.lines.map((l) => l.id));

describe('Bangkok districts', () => {
  it('covers all 50 khet with unique slugs', () => {
    expect(districts).toHaveLength(50);
    expect(slugs.size).toBe(50);
    expect(meta.district_count).toBe(50);
  });

  it.each(districts.map((d) => [d.slug, d] as const))('%s is complete', (_slug, d) => {
    for (const name of [d.name_en, d.name_th, d.name_jp, d.name_ru]) expect(name.trim()).not.toBe('');
    expect(d.name_th).not.toMatch(/^เขต/); // "khet" prefix stripped

    for (const key of RATING_KEYS) {
      expect(Number.isInteger(d.ratings[key])).toBe(true);
      expect(d.ratings[key]).toBeGreaterThanOrEqual(1);
      expect(d.ratings[key]).toBeLessThanOrEqual(10);
      expect(LEVELS).toContain(d.confidence[key]);
      expect(Array.isArray(d.sources[key])).toBe(true);
    }
    // Rent and safety have no open source: they must say so.
    expect(d.confidence.rent).toBe('editorial');
    expect(d.confidence.safety).toBe('editorial');

    expect(d.rent.one_bed).toBeGreaterThan(0);
    expect(d.rent.two_bed!).toBeGreaterThan(d.rent.one_bed!);

    expect(Object.keys(d.transit_minutes).sort()).toEqual([...CITIES.bangkok.hubs].sort());
    expect(d.min_transit).toBe(Math.min(...Object.values(d.transit_minutes)));

    for (const id of [...d.station_ids, ...d.nearby_station_ids]) expect(stationIds.has(id), id).toBe(true);
    for (const id of d.line_ids) expect(lineIds.has(id), id).toBe(true);
    expect(d.neighbors.length).toBeGreaterThan(0);
    for (const n of d.neighbors) expect(slugs.has(n), n).toBe(true);
  });

  it('has symmetric neighbour relations', () => {
    const bySlug = new Map(districts.map((d) => [d.slug, d]));
    for (const d of districts) {
      for (const n of d.neighbors) expect(bySlug.get(n)!.neighbors, `${d.slug}↔${n}`).toContain(d.slug);
    }
  });

  it('has geometry with the label point inside each bbox', () => {
    for (const d of districts) {
      const g = geometry[d.slug];
      expect(g, d.slug).toBeDefined();
      expect(g.polygons.length).toBeGreaterThan(0);
      const [[s, w], [n, e]] = g.bbox;
      expect(d.lat).toBeGreaterThanOrEqual(s);
      expect(d.lat).toBeLessThanOrEqual(n);
      expect(d.lng).toBeGreaterThanOrEqual(w);
      expect(d.lng).toBeLessThanOrEqual(e);
      for (const poly of g.polygons) {
        for (const ring of poly) {
          expect(ring.length).toBeGreaterThanOrEqual(4);
          expect(ring[0]).toEqual(ring[ring.length - 1]); // closed ring
        }
      }
    }
  });

  it('keeps the published medians in sync with the data', () => {
    for (const key of RATING_KEYS) {
      const vals = districts.map((d) => d.ratings[key]).sort((a, b) => a - b);
      const mid = (vals[24] + vals[25]) / 2;
      expect(meta.medians[key], key).toBe(Math.floor(mid + 0.5));
    }
  });

  it('ships complete trilingual descriptions when present', () => {
    for (const d of districts) {
      if (!d.description) continue;
      for (const loc of ['en', 'ja', 'ru'] as const) {
        for (const field of ['atmosphere', 'landmarks', 'food', 'nightlife'] as const) {
          expect(d.description[loc][field].trim(), `${d.slug}.${loc}.${field}`).not.toBe('');
        }
      }
    }
  });

  it('credits every hot-linked image', () => {
    for (const d of districts) {
      if (!d.image) continue;
      expect(d.image.thumb).toMatch(/^https:\/\/(thumb|upload)\.wikimedia\.org\//);
      expect(d.image.hero).toMatch(/^https:\/\/(thumb|upload)\.wikimedia\.org\//);
      expect(d.image.thumb).not.toContain('utm_');
      expect(d.image.artist).not.toBe('');
      expect(d.image.license).not.toBe('');
    }
  });
});

describe('Bangkok rail overlay', () => {
  it('links every station to known lines and districts', () => {
    for (const s of rail.stations) {
      expect(s.lines.length).toBeGreaterThan(0);
      for (const l of s.lines) expect(lineIds.has(l), `${s.id}:${l}`).toBe(true);
      if (s.district) expect(slugs.has(s.district), s.district).toBe(true);
    }
  });

  it('draws every line with a hex colour and a path', () => {
    expect(rail.lines).toHaveLength(10);
    for (const l of rail.lines) {
      expect(l.color).toMatch(/^#[0-9A-Fa-f]{6}$/);
      expect(l.paths.length).toBeGreaterThan(0);
    }
  });
});

describe('Bangkok map payload', () => {
  it('maps districts to the shared MapStation shape', () => {
    const mapped = getBangkokMapDistricts();
    expect(mapped).toHaveLength(50);
    const w = mapped.find((m) => m.slug === 'watthana')!;
    expect(w.name_th).toBe('วัฒนา');
    expect(w.rent_1k).toBeGreaterThan(20_000);
    expect(w.station_count).toBeGreaterThan(3);
    // stations inside the district are searchable aliases
    expect(w.aliases?.some((a) => a.toLowerCase() === 'thong lo')).toBe(true);
    for (const m of mapped) expect(m.elevation_m).toBeNull();
  });

  it('truncates snippets to one line of tooltip text', () => {
    for (const s of Object.values(getBangkokSnippets('en'))) expect(s.length).toBeLessThanOrEqual(141);
  });
});
