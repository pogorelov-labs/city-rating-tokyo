import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createTranslator } from 'next-intl';
import { describe, expect, it, vi } from 'vitest';
import { dailyInputs, concentration, localHour, summarizeLive, summarizeSeason, type Reading } from './model';
import { parseTokyo, parseBangkok, bangkokMonitors } from './providers';
import { createLiveService, loadProvider, fetchJson } from './live';
import { GET } from '@/app/api/air/[city]/route';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';
import { AirLiveView, type AirLabels } from '@/components/AirLiveChip';
const localeState = vi.hoisted(() => ({ locale: 'en' as 'en'|'ja'|'ru' }));
vi.mock('next-intl/server', () => ({ getTranslations: async () => createTranslator({locale:localeState.locale,messages:{en,ja,ru}[localeState.locale],namespace:'air'}) }));
vi.mock('@/i18n/navigation', () => ({Link: ({children,href}: {children:React.ReactNode;href:string}) => createElement('a',{href},children)}));
import AirPanel from '@/components/AirPanel';
import AirMethodology from '@/components/AirMethodology';
const NOW = Date.parse('2026-10-15T10:00:00Z');
const row = (station: string, pm25: number, time='2026-10-15T09:00:00Z'): Reading => ({station,pm25,time});
describe('air provider semantics', () => {
  it('never treats blanks, sentinels or invalid numbers as clean air', () => {
    for (const v of ['', ' ', '-', null, undefined, -1, 9999, NaN, Infinity, false, '1e3']) expect(concentration(v)).toBeNull();
    expect(concentration(0)).toBe(0);expect(concentration('37.5')).toBe(37.5);
  });
  it('converts explicit local clocks, hour24 and invalid dates', () => {
    expect(localHour('2026/10/14',24,9)).toBe('2026-10-14T15:00:00.000Z');
    expect(localHour('2026-10-14',0,7)).toBe('2026-10-13T17:00:00.000Z');
    expect(localHour('2026-02-30',1,9)).toBeNull();
  });
  it('Tokyo only admits the permitted national subset', () => {
    expect(parseTokyo([{SKT_CD:'13104010',SKT_DATE:'2026/10/14',SKT_TIME:'22',PM2_5:'1'},
      {SKT_CD:'13101010',SKT_DATE:'2026/10/14',SKT_TIME:'22',PM2_5:'200'},
      {SKT_CD:'13104010',SKT_DATE:'2026/10/14',SKT_TIME:'21',PM2_5:'-'}])).toEqual([row('13104010',1,'2026-10-14T13:00:00.000Z')]);
    expect(()=>parseTokyo({error:'blocked'})).toThrow();
  });
  it('Bangkok selects provider-declared city, excludes metro ring and closed/future stations', () => {
    const station={ID:'02t',Area:'เขตธนบุรี, กรุงเทพฯ',OpenDate:'0000-00-00',CloseDate:'0000-00-00'};
    expect(bangkokMonitors([station,{...station,ID:'03t',Area:'นนทบุรี'}, {...station,ID:'04t',CloseDate:'2026-01-01'}, {...station,ID:'05t',OpenDate:'2027-01-01'}], '2026-10-15')).toEqual(['02t']);
  });
  it('Bangkok does not accept summary averages as hourly observations', () => {
    expect(parseBangkok({result:'OK',stations:[{stationID:'02t',summary:{PM25:{average:999}},data:[{DATETIMEDATA:'2026-10-15 16:00:00',PM25:10},{DATETIMEDATA:'2026-10-15 17:00:00',PM25:null}]}]})).toEqual([row('02t',10,'2026-10-15T09:00:00.000Z')]);
    expect(()=>parseBangkok({result:'ERROR',stations:[]})).toThrow();
  });
});
describe('same-hour summaries and missingness', () => {
  it('daily ingestion enforces 18-hour validity, units are not inferred from empty strings', () => {
    const good = {station:'a',date:'2026-12-01',pm25:'37.5',validHours:18};
    expect(dailyInputs([good,{...good,validHours:17},{...good,pm25:''},{...good,date:'2026-02-30'},null])).toEqual({accepted:[{station:'a',date:'2026-12-01',pm25:37.5}],excluded:4});
  });
  it('uses same-hour median and selected monitor denominator', () => {
    const result=summarizeLive('bangkok',[row('a',10),row('b',40),row('c',200,'2026-10-15T08:00:00Z')],['a','b','c','d'],NOW);
    expect(result).toMatchObject({value:25,reporting:2,eligible:4,status:'fresh'});
    expect(summarizeLive('bangkok',[row('a',10)],['a','b','c'],NOW)).toMatchObject({value:null,status:'unavailable',reporting:1});
  });
  it('deduplicates and excludes conflicting duplicates and future values', () => {
    expect(summarizeLive('bangkok',[row('a',10),row('a',10),row('b',30),row('b',50),row('c',900,'2026-10-15T11:00:00Z')],['a','b','c'],NOW).value).toBeNull();
  });
  it('yesterday22 JST is stale; expired values are absent and zero is a real measurement', () => {
    expect(summarizeLive('tokyo',[row('13104010',1,'2026-10-14T13:00:00Z')],['13104010'],NOW).status).toBe('stale');
    expect(summarizeLive('tokyo',[row('a',1,'2026-10-12T13:00:00Z')],['a'],NOW).value).toBeNull();
    expect(summarizeLive('tokyo',[row('a',0)],['a'],NOW).value).toBe(0);
  });
  it('retains calendar denominator and leap day; missing never means below threshold', () => {
    const season=summarizeSeason([{station:'a',date:'2023-12-01',pm25:37.5},{station:'b',date:'2023-12-01',pm25:37.5},{station:'a',date:'2024-02-29',pm25:0}],['a','b'],'2023-12-01','2024-03-31');
    expect(season).toMatchObject({calendarDays:122,validDays:2,missingDays:120,aboveDays:1,percent:50,status:'partial'});
  });
  it('season city-day denominator excludes poorly covered days and repeat rows', () => {
    const daily=[{station:'a',date:'2026-12-01',pm25:40},{station:'a',date:'2026-12-01',pm25:40},{station:'b',date:'2026-12-01',pm25:35},{station:'a',date:'2026-12-02',pm25:0}];
    expect(summarizeSeason(daily,['a','b','c'],'2026-12-01','2027-03-31')).toMatchObject({calendarDays:121,validDays:1,aboveDays:1,percent:100});
    expect(summarizeSeason([],['a'],'2026-12-01','2027-03-31')).toMatchObject({percent:null,mean:null,status:'unavailable'});
  });
});
describe('live API resilience', () => {
  it('single-flight cache keeps original retrieval time and recomputes staleness on server', async () => {
    let now=NOW;const load=vi.fn(async()=>({rows:[row('a',10)],ids:['a']}));const service=createLiveService(load,()=>now);
    const [a,b]=await Promise.all([service('tokyo'),service('tokyo')]);expect(load).toHaveBeenCalledTimes(1);expect(a).toEqual(b);
    now+=1800000;expect((await service('tokyo')).fetchedAt).toBe(new Date(NOW).toISOString());expect(load).toHaveBeenCalledTimes(1);
    now+=4*3600000;expect((await service('tokyo')).status).toBe('stale');
  });
  it('failure is unavailable with cooldown; gated sources never fetch', async () => {
    const load=vi.fn(async()=>{throw new Error('TLS failure');});const service=createLiveService(load,()=>NOW);
    expect((await service('tokyo')).value).toBeNull();await service('tokyo');expect(load).toHaveBeenCalledTimes(1);
    expect((await service('bangkok')).status).toBe('permission_pending');expect(load).toHaveBeenCalledTimes(1);
  });
  it('an outage preserves the original fetch date but cannot keep expired values available', async () => {
    let now=NOW; let fail=false;
    const service=createLiveService(async()=>{if(fail) throw new Error('offline'); return {rows:[row('a',10)],ids:['a']};},()=>now);
    const first=await service('tokyo'); fail=true; now+=4*3600000;
    expect(await service('tokyo')).toMatchObject({status:'stale',value:10,fetchedAt:first.fetchedAt});
    now+=48*3600000;
    expect(await service('tokyo')).toMatchObject({status:'unavailable',value:null,fetchedAt:first.fetchedAt});
  });
  it('rejects unknown API city without an upstream request', async () => {
    expect((await GET(new Request('https://example.test/api/air/unknown'),{params:Promise.resolve({city:'unknown'})})).status).toBe(404);
  });
  it('request uses only national monitor and handles month rollover', async () => {
    const get=vi.fn<(url: string) => Promise<unknown>>().mockResolvedValue([]);await loadProvider('tokyo',Date.parse('2027-01-01T00:00:00Z'),get);
    const url=new URL(get.mock.calls[0][0]);expect(url.searchParams.get('Start_YM')).toBe('202612');expect(url.searchParams.get('SKT_CD')).toBe('13104010');
  });
  it('rejects HTTP errors and oversized bodies', async () => {
    vi.stubGlobal('fetch',vi.fn(async()=>new Response('bad',{status:502})));
    await expect(fetchJson('https://example.test')).rejects.toThrow();
    vi.stubGlobal('fetch',vi.fn(async()=>new Response('x'.repeat(2000001))));
    await expect(fetchJson('https://example.test')).rejects.toThrow('Oversized');vi.unstubAllGlobals();
  });
});
for (const [locale, messages] of Object.entries({en,ja,ru})) {
  it(`${locale}: panel, permission gap, stale chip and methodology render honestly`, async () => {
    localeState.locale=locale as 'en'|'ja'|'ru';
    const html=renderToStaticMarkup(await AirPanel({city:'tokyo'}));expect(html).toContain(messages.air.tokyoScope);expect(html).toContain(messages.air.historyUnavailable);expect(html).toContain(messages.air.pollenUnavailable);
    const method=renderToStaticMarkup(await AirMethodology());expect(method).toContain(messages.air.methodMissing);
    const stale=summarizeLive('tokyo',[row('a',1,'2026-10-14T13:00:00Z')],['a'],NOW);
    const chip=renderToStaticMarkup(createElement(AirLiveView,{data:stale,labels:messages.air as AirLabels}));
    expect(chip).toContain(messages.air.stale);expect(chip).toContain('1.0');expect(chip).toContain('UTC');expect(chip).not.toContain(messages.air.fresh);
    const bkk=renderToStaticMarkup(await AirPanel({city:'bangkok'}));expect(bkk).toContain(messages.air.bangkokScope);expect(bkk).not.toContain('0.0');
  });
}
