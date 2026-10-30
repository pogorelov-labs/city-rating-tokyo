import { createTranslator } from 'next-intl';
import { describe, expect, it, vi } from 'vitest';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import { DEFAULT_WEIGHTS, PRESET_PROFILES } from './types';
import { CITIES } from './cities';
import { decodeParamsToState } from './url-state';
import { getMapStations, getStations } from './data';
import { getBangkokDistricts, getBangkokStationAreas } from './bangkok-data';
import { guideDetailHref, guideTraits, withGuideWeights } from './area-guide';

vi.mock('next-intl/server', () => ({
  getTranslations: async ({ locale, namespace }: { locale: 'en' | 'ja' | 'ru'; namespace: 'areaGuide' }) =>
    createTranslator({ locale, namespace, messages: { en, ja, ru }[locale] }),
}));

import { buildAreaGuide } from './area-guide-data';

describe('area guide data contracts', () => {
  it('normalizes every public area without missing geometry, invalid numbers or mixed-cohort peers', async () => {
    const cases = [
      ...getStations().map(station => ({ city: 'tokyo' as const, kind: 'station' as const, slug: station.slug })),
      ...getBangkokStationAreas().map(station => ({ city: 'bangkok' as const, kind: 'station' as const, slug: station.id })),
      ...getBangkokDistricts().map(district => ({ city: 'bangkok' as const, kind: 'district' as const, slug: district.slug })),
    ];
    expect(cases).toHaveLength(1676);
    for (const item of cases) for (const locale of ['en', 'ja', 'ru'] as const) {
      const area = await buildAreaGuide(item.city, item.kind, item.slug, locale);
      expect(area, item.slug).not.toBeNull();
      if (!area) continue;
      expect(area.name.length, item.slug).toBeGreaterThan(0);
      expect(area.summary.trim(), `${item.slug}: ${locale}`).not.toBe('');
      expect(area.summary, `${item.slug}: ${locale}`).not.toContain('areaGuide.');
      for (const value of Object.values(area.ratings ?? {})) expect(Number.isFinite(value) && value >= 1 && value <= 10, item.slug).toBe(true);
      for (const value of Object.values(area.commute)) expect(Number.isFinite(value) && value >= 0, item.slug).toBe(true);
      for (const fact of area.facts) expect(Number.isFinite(fact.value), `${item.slug}: ${fact.key}`).toBe(true);
      for (const rent of area.rent.values) expect(rent.value == null || (Number.isFinite(rent.value) && rent.value >= 0), item.slug).toBe(true);
      if (area.city === 'bangkok') expect(area.map.polygons?.length, item.slug).toBeGreaterThan(0);
      const prefix = item.city === 'tokyo' ? '/station/' : `/bangkok/${item.kind}/`;
      expect(area.peers.every(peer => peer.key !== area.key && peer.href.startsWith(prefix)), item.slug).toBe(true);
    }
  }, 45000);

  it('preserves Bangkok bedroom medians, sample sizes, zero-minute trips and the published catchment', async () => {
    const area = await buildAreaGuide('bangkok', 'station', 'asok', 'en');
    expect(area?.rent).toMatchObject({ provenance: 'bedroomMedian', samples: { one: 30, two: 18 } });
    expect(area?.rent.values.map(value => value.value)).toEqual([26500, 55000]);
    expect(area?.commute.asok).toBe(0);
    expect(area?.map.polygons?.length).toBeGreaterThan(0);
    expect(area?.peerCount).toBe(CITIES.bangkok.levelStats.station?.count);
  });

  it('uses the actual medians and counts for each rating cohort', async () => {
    const cohorts = [
      { records: getStations(), city: 'tokyo' as const, kind: 'station' as const, slug: 'kichijoji' },
      { records: getBangkokStationAreas(), city: 'bangkok' as const, kind: 'station' as const, slug: 'asok' },
      { records: getBangkokDistricts(), city: 'bangkok' as const, kind: 'district' as const, slug: 'bang-bon' },
    ];
    for (const { records, city, kind, slug } of cohorts) {
      const rated = records.flatMap(record => record.ratings ? [record.ratings] : []);
      const area = (await buildAreaGuide(city, kind, slug, 'en'))!;
      expect(area.peerCount).toBe(rated.length);
      for (const key of Object.keys(area.medians) as (keyof typeof area.medians)[]) {
        const values = rated.map(rating => rating[key]).sort((a, b) => a - b);
        const midpoint = values.length / 2;
        const median = values.length % 2 ? values[Math.floor(midpoint)] : (values[midpoint - 1] + values[midpoint]) / 2;
        expect(area.medians[key], `${city}:${kind}:${key}`).toBe(median);
      }
    }
  });

  it('keeps a mixed-size luxury sample distinct from a district blend', async () => {
    const skewed = await buildAreaGuide('bangkok', 'station', 'phrom-phong', 'en');
    const blend = await buildAreaGuide('bangkok', 'station', 'ari', 'en');
    expect(skewed?.rent).toMatchObject({ provenance: 'bedroomMedian', skewed: true });
    expect(blend?.rent).toMatchObject({ provenance: 'districtBlend', skewed: false, samples: null });
  });

  it('uses district medians and omits station noise estimates for districts without rail', async () => {
    const area = await buildAreaGuide('bangkok', 'district', 'bang-bon', 'en');
    expect(area?.stationCount).toBe(0);
    expect(area?.lines).toEqual([]);
    expect(area?.noise).toBeNull();
    expect(area?.map.polygons?.length).toBeGreaterThan(0);
    expect(area?.rent.provenance).toBe('estimate');
  });

  for (const locale of ['en', 'ja', 'ru'] as const) {
    it(`builds the full-dataset Tokyo adapter in ${locale}, with Tokyo rent cohorts and an explicit reference circle`, async () => {
      const area = await buildAreaGuide('tokyo', 'station', 'kichijoji', locale);
      expect(area?.rent.values.map(value => value.layout)).toEqual(['smallTokyo', 'largeTokyo']);
      expect(area?.map.polygons).toBeNull();
      expect(area?.peerCount).toBe(1493);
      expect(area?.summary).not.toContain('areaGuide.');
      expect(area?.summary).not.toBe('');
      expect(area?.peers.every(peer => peer.href.startsWith('/station/'))).toBe(true);
    });
  }

  it('does not add full category confidence or source arrays to the homepage payload', () => {
    const station = getMapStations().find(value => value.slug === 'kichijoji');
    expect(station?.rent_source).toBe('suumo');
    expect(station).not.toHaveProperty('confidence');
    expect(station).not.toHaveProperty('sources');
  });

  it('returns missing areas rather than a fabricated profile', async () => {
    expect(await buildAreaGuide('tokyo', 'station', 'missing-area', 'en')).toBeNull();
    expect(await buildAreaGuide('bangkok', 'district', 'missing-area', 'en')).toBeNull();
  });
});

describe('score continuity and honest narrative', () => {
  it('round-trips the existing weight format through detail, locale and map links', () => {
    const weights = PRESET_PROFILES.find(profile => profile.id === 'family')!.weights;
    const href = guideDetailHref('bangkok', 'st.asok', weights);
    const params = new URL(href, 'https://city-rating.test').searchParams;
    expect(href).toMatch(/^\/bangkok\/station\/asok\?/);
    expect(decodeParamsToState(params, 'bangkok').weights).toEqual(weights);
    expect(withGuideWeights('/station/kichijoji?hub=tokyo&reference=mitaka#w', DEFAULT_WEIGHTS))
      .toBe('/station/kichijoji?hub=tokyo&reference=mitaka#w');
    expect(withGuideWeights('/bangkok?lv=station&s=st.asok&w=old', DEFAULT_WEIGHTS))
      .toBe('/bangkok?lv=station&s=st.asok');
  });

  it('does not turn an extreme relative safety score into a street-level narrative claim', () => {
    const median = CITIES.tokyo.medians;
    const ratings = { ...median, safety: 1, transport: 10, food: 9 };
    const result = guideTraits(ratings, median);
    expect(result.strengths).toContain('transport');
    expect([...result.strengths, ...result.tradeoffs]).not.toContain('safety');
    expect(guideTraits(null, median)).toEqual({ strengths: [], tradeoffs: [] });
  });
});

describe('every new locale message formats with its declared arguments', () => {
  function leaves(object: object, prefix = ''): string[] {
    return Object.entries(object).flatMap(([key, value]) => typeof value === 'string'
      ? [`${prefix}${key}`] : leaves(value, `${prefix}${key}.`));
  }
  it('has the same message keys and interpolation arguments in all locales', () => {
    const keys = leaves(en.areaGuide).sort();
    for (const messages of [ja, ru]) expect(leaves(messages.areaGuide).sort()).toEqual(keys);
    const lookup = (obj: object, key: string): string => key.split('.').reduce<unknown>(
      (value, part) => (value as Record<string, unknown>)[part], obj,
    ) as string;
    const args = (message: string) => [...message.matchAll(/\{\s*([\w]+)\s*(?:,|\})/g)].map(match => match[1]).sort();
    for (const key of keys) {
      for (const messages of [ja, ru]) expect(args(lookup(messages.areaGuide, key)), key).toEqual(args(lookup(en.areaGuide, key)));
    }
  });
  for (const locale of ['en', 'ja', 'ru'] as const) {
    const messages = { en, ja, ru }[locale];
    it(`formats all area-guide messages in ${locale} without fallback or ICU errors`, () => {
      const t = createTranslator({ locale, messages: messages.areaGuide, onError: error => { throw error; } });
      for (const key of leaves(messages.areaGuide)) {
        expect(t(key as Parameters<typeof t>[0], {
          count: 5, name: 'Test', city: 'Test', profile: 'Test', date: '2026-10-30',
          area: '1.5', difference: '-2', sources: 'OSM', one: 3, two: 4,
        })).not.toBe(key);
      }
    });
  }
});
