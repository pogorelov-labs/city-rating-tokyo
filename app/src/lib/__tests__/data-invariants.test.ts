/**
 * Invariants over the real build-time data (CRTKY-43 follow-ups).
 *
 * These run against the actual JSON/TS data files, not fixtures: they exist
 * because each one was silently violated on the live site before.
 */
import { describe, expect, it } from 'vitest';

import { getStations } from '../data';
import { isStationLevelRent } from '../scoring';
import { DEMO_RATINGS } from '@/data/demo-ratings';
import rentAverages from '@/data/rent-averages.json';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';

const stations = getStations();

describe('rent provenance and caps', () => {
  it('keeps the real source of every rent-averages row (was hardcoded to suumo)', () => {
    const rows = rentAverages as Record<string, { source: string }>;
    for (const s of stations) {
      const row = rows[s.slug];
      if (row) expect(s.rent_avg?.source, s.slug).toBe(row.source);
    }
  });

  it('never recomputes area-level rent: those stations keep the backend (capped) rating', () => {
    let checked = 0;
    for (const s of stations) {
      if (!s.rent_avg || isStationLevelRent(s.rent_avg) || !s.ratings) continue;
      expect(s.ratings.rent, s.slug).toBe(DEMO_RATINGS[s.slug].ratings.rent);
      checked++;
    }
    expect(checked).toBeGreaterThan(500); // ~826 e-Stat stations today
  });

  it('shows affordability 10 only for station-level rent (source-quality cap)', () => {
    // Read provenance from the source file, not from s.rent_avg: when provenance
    // was erased, s.rent_avg claimed 'suumo' and this check could not see the bug.
    const rows = rentAverages as Record<string, { source: string }>;
    const offenders = stations
      .filter((s) => s.ratings?.rent === 10)
      .filter((s) => rows[s.slug] && !['suumo', 'homes'].includes(rows[s.slug].source))
      .map((s) => s.slug);
    expect(offenders).toEqual([]);
  });
});

describe('source labels', () => {
  const emitted = new Set<string>();
  for (const entry of Object.values(DEMO_RATINGS)) {
    for (const list of Object.values(entry.sources ?? {})) {
      for (const key of list ?? []) emitted.add(key);
    }
  }

  it.each([
    ['en', en],
    ['ja', ja],
    ['ru', ru],
  ])('every source key in the data has a %s label (else the raw key is shown)', (_, dict) => {
    const labels = (dict as { sources: Record<string, string> }).sources;
    const missing = [...emitted].filter((k) => !(k in labels));
    expect(missing).toEqual([]);
  });
});
