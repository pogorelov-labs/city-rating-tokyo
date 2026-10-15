import { emptyAir, SOURCES, summarizeLive, type AirCity, type Reading } from './model';
import { NATIONAL_TOKYO, parseTokyo, parseBangkok, bangkokMonitors } from './providers';
const HOUR = 3600000;
type Snapshot = { rows: Reading[]; ids: string[] };
/** Hard-coded HTTPS providers only. No caller URL, API key or TLS bypass. */
export async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url, { signal: AbortSignal.timeout(8000), redirect: 'error', cache: 'no-store' });
  if (!response.ok) throw new Error('Upstream unavailable');
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Missing upstream body');
  const chunks: Uint8Array[] = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > 2000000) throw new Error('Oversized upstream body');
      chunks.push(value);
    }
  } finally { await reader.cancel(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes));
}
export async function loadProvider(city: AirCity, now: number, get = fetchJson): Promise<Snapshot> {
  if (city === 'tokyo') {
    // Include previous month to retain last observation at month rollover.
    const local = new Date(now + 9*HOUR);
    const ym = (d: Date) => `${d.getUTCFullYear()}${String(d.getUTCMonth()+1).padStart(2,'0')}`;
    const previous = new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth()-1, 1));
    const url = new URL('https://soramame.env.go.jp/soramame/api/data_search');
    url.search = new URLSearchParams({ Start_YM: ym(previous), End_YM: ym(local), TDFKN_CD: '13', SKT_CD: NATIONAL_TOKYO.join(','), REQUEST_DATA: 'PM2_5' }).toString();
    return { rows: parseTokyo(await get(url.href)), ids: NATIONAL_TOKYO };
  }
  const end = new Date(now + 7*HOUR).toISOString().slice(0,10);
  const start = new Date(now + 7*HOUR - 2*24*HOUR).toISOString().slice(0,10);
  const ids = bangkokMonitors(await get('https://air4thai.pcd.go.th/webV2/history/api/station.php'), end);
  if (!ids.length) throw new Error('No verified Bangkok monitors');
  const url = new URL('https://air4thai.pcd.go.th/webV2/history/api/data.php');
  url.search = new URLSearchParams({stationID: ids.join(','), param:'PM25', type:'hr', sdate:start, edate:end, stime:'00', etime:'24', format:'json'}).toString();
  return { rows: parseBangkok(await get(url.href)), ids };
}
/** Per-process bounded cache + single-flight, failure cooldown; no stale-as-fresh. */
export function createLiveService(load = loadProvider, clock = Date.now) {
  const cache = new Map<AirCity, { checked: number; fetched?: number; data?: Snapshot; pending?: Promise<void> }>();
  return async (city: AirCity) => {
    const now = clock();
    if (!SOURCES[city].permitted) return emptyAir(city, now, true);
    let entry = cache.get(city);
    if (!entry) { entry = { checked: -Infinity }; cache.set(city, entry); }
    if (!entry.pending && now-entry.checked >= HOUR) {
      const current = entry;
      current.checked = now;
      current.pending = load(city, now).then(data => { current.data = data; current.fetched = clock(); }).catch(() => { /* Preserve last observation, never convert failure to zero. */ }).finally(() => { current.pending = undefined; });
    }
    await entry.pending;
    const result = entry.data ? summarizeLive(city, entry.data.rows, entry.data.ids, clock()) : emptyAir(city, clock());
    result.checkedAt = new Date(entry.checked).toISOString();
    result.fetchedAt = entry.fetched == null ? null : new Date(entry.fetched).toISOString();
    return result;
  };
}
export const getLiveAir = createLiveService();
