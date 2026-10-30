import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { getInstitutions } from './institutions';
import stations from '@/data/stations.json';
import districts from '@/data/bangkok/districts.json';
import areas from '@/data/bangkok/stations.json';

const source = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

describe('institution consumers and joins', () => {
  it('joins every public station, station area and district by canonical ID', () => {
    expect(stations).toHaveLength(1493);
    expect(districts.districts).toHaveLength(50);
    expect(areas.areas).toHaveLength(133);
    for (const row of stations) expect(getInstitutions('tokyo', 'station', row.slug)).toBeDefined();
    for (const row of districts.districts) expect(getInstitutions('bangkok', 'district', row.slug)).toBeDefined();
    for (const row of areas.areas) expect(getInstitutions('bangkok', 'station', row.id)).toBeDefined();
  });
  it('uses polygon counts despite preserved legacy center counts', () => {
    expect(getInstitutions('bangkok', 'district', 'pathum-wan')).toEqual({ city: 'bangkok', scope: 'district', embassies: 23, medicine: null });
    expect(getInstitutions('bangkok', 'district', 'bang-rak')?.embassies).toBe(11);
    expect(getInstitutions('tokyo', 'district', 'pathum-wan')).toBeUndefined();
    expect(getInstitutions('bangkok', 'station', 'absent')).toBeUndefined();
  });
  it('wires existing routes to dedicated counts with no legacy consumer', () => {
    const district = source('app/[locale]/bangkok/district/[slug]/page.tsx');
    const station = source('app/[locale]/bangkok/station/[id]/page.tsx');
    const tokyo = source('app/[locale]/station/[slug]/page.tsx');
    const extras = source('components/area/AreaGuideExtras.tsx');
    for (const page of [district, station, tokyo]) expect(page).toContain('AreaGuideExtras area={area}');
    expect(extras).toMatch(/getInstitutions\(area\.city, area\.kind, area\.slug\)/);
    for (const page of [district, station, tokyo, extras, source('components/NaturalEnvironment.tsx')]) {
      expect(page).not.toMatch(/embassies_800m|english_medicine_2km/);
    }
  });
});
