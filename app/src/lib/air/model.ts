/** CRTKY-188: monitor summaries, never neighbourhood interpolation or scores. */
export type AirCity = 'tokyo' | 'bangkok';
export type Reading = { station: string; time: string; pm25: number };
export type LiveAir = {
  city: AirCity; status: 'fresh' | 'stale' | 'unavailable' | 'permission_pending';
  value: number | null; observedAt: string | null; checkedAt: string;
  fetchedAt: string | null; reporting: number; eligible: number; unit: 'µg/m³';
  scope: 'national_monitor' | 'reporting_monitors';
};
export const SOURCES = {
  tokyo: { url: 'https://soramame.env.go.jp/', scope: 'national_monitor' as const, permitted: true },
  bangkok: { url: 'https://air4thai.pcd.go.th/', scope: 'reporting_monitors' as const, permitted: false },
};
export function concentration(value: unknown): number | null {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && !/^\d+(\.\d+)?$/.test(value.trim())) return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 && n <= 1000 ? n : null;
}
/** Explicit provider-local clock, including Soramame's hour 24 = next midnight. */
export function localHour(date: string, hour: number, offset: number): string | null {
  if (!/^\d{4}[-/]\d{2}[-/]\d{2}$/.test(date) || !Number.isInteger(hour) || hour < 0 || hour > 24) return null;
  const [y, m, d] = date.split(/[-/]/).map(Number);
  const base = new Date(Date.UTC(y, m - 1, d));
  if (base.getUTCFullYear() !== y || base.getUTCMonth() !== m - 1 || base.getUTCDate() !== d) return null;
  return new Date(base.getTime() + (hour - offset) * 3600000).toISOString();
}
export function emptyAir(city: AirCity, now: number, permission = false): LiveAir {
  return { city, status: permission ? 'permission_pending' : 'unavailable', value: null, observedAt: null,
    checkedAt: new Date(now).toISOString(), fetchedAt: null, reporting: 0, eligible: city === 'tokyo' ? 1 : 0,
    unit: 'µg/m³', scope: SOURCES[city].scope };
}
/** Deduplicate by station/hour. Conflicting duplicate readings are discarded. */
export function uniqueReadings(rows: Reading[]): Reading[] {
  const groups = new Map<string, Reading | null>();
  for (const row of rows) {
    if (!row.station || concentration(row.pm25) === null || !Number.isFinite(Date.parse(row.time))) continue;
    const time = new Date(row.time).toISOString();
    const key = `${row.station}|${time}`;
    if (!groups.has(key)) groups.set(key, { ...row, time });
    else if (groups.get(key)?.pm25 !== row.pm25) groups.set(key, null);
  }
  return [...groups.values()].filter((r): r is Reading => r !== null);
}
export function summarizeLive(city: AirCity, rows: Reading[], ids: string[], now: number): LiveAir {
  const result = emptyAir(city, now);
  const eligible = new Set(ids);
  result.eligible = eligible.size;
  const valid = uniqueReadings(rows).filter(r => eligible.has(r.station) && Date.parse(r.time) <= now);
  const latest = Math.max(...valid.map(r => Date.parse(r.time)));
  if (!Number.isFinite(latest) || now - latest > 48 * 3600000) return result;
  const values = valid.filter(r => Date.parse(r.time) === latest).map(r => r.pm25).sort((a,b) => a-b);
  result.observedAt = new Date(latest).toISOString();
  result.reporting = values.length;
  // Coverage is monitors at exactly the SAME hour, not geographical coverage.
  if (!eligible.size || values.length < Math.ceil(eligible.size / 2)) return result;
  const middle = Math.floor(values.length / 2);
  result.value = Math.round((values.length % 2 ? values[middle] : (values[middle-1]+values[middle])/2)*10)/10;
  result.status = now - latest <= 3 * 3600000 ? 'fresh' : 'stale';
  return result;
}
export type Season = { start: string; end: string; calendarDays: number; validDays: number;
  missingDays: number; aboveDays: number; percent: number | null; mean: number | null;
  status: 'complete' | 'partial' | 'unavailable'; eligible: number; threshold: number };
/** Each input is a DAILY station mean, not an hourly reading. Dates are local. */
export function summarizeSeason(rows: { station: string; date: string; pm25: number }[], ids: string[], start: string, end: string, threshold = 37.5): Season {
  const begin = localHour(start, 0, 0), finish = localHour(end, 0, 0);
  if (!begin || !finish || finish < begin || !Number.isFinite(threshold) || threshold < 0) throw new Error('Invalid season');
  const calendarDays = (Date.parse(finish)-Date.parse(begin))/86400000+1;
  if (calendarDays > 366) throw new Error('Maximum one year');
  const eligible = new Set(ids);
  if (!eligible.size || eligible.has('')) throw new Error('Explicit eligible monitor set required');
  const unique = uniqueReadings(rows.flatMap(r => {
    const time = localHour(r.date, 0, 0);
    return time && r.date >= start && r.date <= end ? [{ station: r.station, time, pm25: r.pm25 }] : [];
  }));
  const days = new Map<string, number[]>();
  for (const r of unique) if (eligible.has(r.station)) {
    const list = days.get(r.time) ?? []; list.push(r.pm25); days.set(r.time, list);
  }
  const means = [...days.values()].filter(v => v.length >= Math.ceil(eligible.size/2)).map(v => v.reduce((a,b)=>a+b,0)/v.length);
  const validDays = means.length, aboveDays = means.filter(n => n >= threshold).length;
  return { start, end, calendarDays, validDays, missingDays: calendarDays-validDays, aboveDays,
    percent: validDays ? Math.round(aboveDays/validDays*1000)/10 : null,
    mean: validDays ? Math.round(means.reduce((a,b)=>a+b,0)/validDays*10)/10 : null,
    status: !validDays ? 'unavailable' : validDays === calendarDays ? 'complete' : 'partial', eligible: eligible.size, threshold };
}

/** Normalize external station-day input before seasonal aggregation. */
export function dailyInputs(rows: unknown[]) {
  const accepted: { station: string; date: string; pm25: number }[] = [];
  for (const raw of rows) {
    if (!raw || typeof raw !== 'object') continue;
    const r = raw as Record<string, unknown>;
    const pm25 = concentration(r.pm25);
    if (typeof r.station !== 'string' || !r.station || typeof r.date !== 'string'
      || !/^\d{4}-\d{2}-\d{2}$/.test(r.date) || !localHour(r.date,0,0)
      || typeof r.validHours !== 'number' || !Number.isInteger(r.validHours)
      || r.validHours < 18 || r.validHours > 24 || pm25 === null) continue;
    accepted.push({station:r.station,date:r.date,pm25});
  }
  return {accepted, excluded: rows.length-accepted.length};
}
