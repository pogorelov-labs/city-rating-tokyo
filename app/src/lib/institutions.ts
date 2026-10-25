import tokyo from '@/data/institutions/station-institutions.json';
import bangkok from '@/data/institutions/district-institutions.json';

export interface InstitutionFact {
  embassies: number;
  medicine: number | null;
  scope: 'district' | 'station';
  city: 'tokyo' | 'bangkok';
}

type StationCounts = { embassies_within_800m: number; english_medicine_within_2km: number | null };
type DistrictCounts = { embassies_inside_district: number; english_medicine_within_2km: null };
export const institutionSources = tokyo._meta.source_urls;
export const institutionSnapshotDate = tokyo._meta.snapshot_date;

/** Undefined is a failed/missing join; zero is a computed count of source records. */
export function getInstitutions(city: 'tokyo' | 'bangkok', scope: 'station' | 'district', id: string): InstitutionFact | undefined {
  if (scope === 'district') {
    if (city !== 'bangkok') return undefined;
    const row = (bangkok.districts as Record<string, DistrictCounts>)[id];
    return row ? { city, scope, embassies: row.embassies_inside_district, medicine: row.english_medicine_within_2km } : undefined;
  }
  const rows: Record<string, StationCounts> = city === 'tokyo' ? tokyo.stations : bangkok.station_areas;
  const row = rows[id];
  return row ? { city, scope, embassies: row.embassies_within_800m, medicine: row.english_medicine_within_2km } : undefined;
}
