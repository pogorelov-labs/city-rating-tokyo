import { concentration, localHour, type Reading } from './model';
const object = (v: unknown): Record<string, unknown> => v && typeof v === 'object' && !Array.isArray(v) ? v as Record<string, unknown> : {};
export const NATIONAL_TOKYO = ['13104010']; // 国設東京（新宿）: explicitly national, no local-government data.
export function parseTokyo(payload: unknown): Reading[] {
  if (!Array.isArray(payload)) throw new Error('Unexpected Soramame response');
  return payload.flatMap(v => {
    const r = object(v), pm25 = concentration(r.PM2_5);
    const time = typeof r.SKT_DATE === 'string' && typeof r.SKT_TIME === 'string' && /^\d{2}$/.test(r.SKT_TIME)
      ? localHour(r.SKT_DATE, Number(r.SKT_TIME), 9) : null;
    return NATIONAL_TOKYO.includes(String(r.SKT_CD)) && time && pm25 !== null ? [{ station: String(r.SKT_CD), time, pm25 }] : [];
  });
}
/** Only a current, provider-declared Bangkok address; no inferred district/geocode. */
export function bangkokMonitors(payload: unknown, localDate: string): string[] {
  if (!Array.isArray(payload)) throw new Error('Unexpected PCD station registry');
  return [...new Set(payload.flatMap(v => {
    const r = object(v);
    return typeof r.ID === 'string' && /^[a-z0-9]{2,8}$/i.test(r.ID)
      && typeof r.Area === 'string' && /กรุงเทพ(?:ฯ|มหานคร)\s*$/.test(r.Area)
      && typeof r.OpenDate === 'string' && (r.OpenDate === '0000-00-00' || r.OpenDate <= localDate)
      && (r.CloseDate === '0000-00-00' || (typeof r.CloseDate === 'string' && r.CloseDate > localDate))
      ? [r.ID.toLowerCase()] : [];
  }))];
}
export function parseBangkok(payload: unknown): Reading[] {
  const root = object(payload);
  if (root.result !== 'OK' || !Array.isArray(root.stations)) throw new Error('Unexpected PCD data response');
  return root.stations.flatMap(v => {
    const station = object(v);
    if (typeof station.stationID !== 'string' || !Array.isArray(station.data)) return [];
    return station.data.flatMap(v => {
      const r = object(v), pm25 = concentration(r.PM25);
      const match = typeof r.DATETIMEDATA === 'string' ? /^(\d{4}-\d{2}-\d{2}) (\d{2}):00:00$/.exec(r.DATETIMEDATA) : null;
      const time = match ? localHour(match[1], Number(match[2]), 7) : null;
      return time && pm25 !== null ? [{ station: String(station.stationID).toLowerCase(), time, pm25 }] : [];
    });
  });
}
