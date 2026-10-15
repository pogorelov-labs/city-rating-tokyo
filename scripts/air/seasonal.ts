/** Offline normalized DAILY input only; never auto-publishes restricted archives.
 * packages/schema/node_modules/.bin/tsx scripts/air/seasonal.ts input.json 2026
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dailyInputs, summarizeSeason } from '../../app/src/lib/air/model';
const [path, yearText] = process.argv.slice(2);
const year = Number(yearText);
if (!path || !Number.isInteger(year) || year < 2000 || year > 2100) throw new Error('Usage: input.json seasonStartYear');
const raw = readFileSync(path);
const input = JSON.parse(raw.toString());
if (!Array.isArray(input.eligibleStations) || !input.eligibleStations.every((v: unknown) => typeof v === 'string' && v.length > 0)
    || input.unit !== 'µg/m³' || input.period !== 'daily_local_mean' || !Array.isArray(input.daily) || typeof input.sourceUrl !== 'string' || !input.sourceUrl.startsWith('https://')) throw new Error('Invalid input contract');
const {accepted, excluded} = dailyInputs(input.daily);
console.log(JSON.stringify({ ...summarizeSeason(accepted, input.eligibleStations, `${year}-12-01`, `${year+1}-03-31`),
  sourceUrl: input.sourceUrl, inputSha256: createHash('sha256').update(raw).digest('hex'),
  excludedInvalidOrInsufficientHours: excluded,
  publication: 'INTERNAL_ONLY_REQUIRES_SOURCE_CLEARANCE',
  rule: 'station-day >=18 valid hours; city-day >=50% selected monitors; equal station means; denominator valid city-days',
}, null, 2));
