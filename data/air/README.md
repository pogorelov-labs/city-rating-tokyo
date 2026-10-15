# City air and seasonal context — CRTKY-188, ADR #3

**Partial acceptance.** This slice publishes a usable national Shinjuku monitor
reference, the shared panel/API, and a reproducible seasonal aggregation tool.
It does not complete Bangkok numerical publication, historical series or pollen.
No ratings, weights, district interpolation or monitor geocodes are added.

## Publication boundary (checked 2026-10-15)

| Slice | Publication state | Evidence / remaining action |
|---|---|---|
| Tokyo national monitor `13104010`, 国設東京（新宿） | Enabled: one monitor, not Tokyo city mean | [Soramame API manual §2-1](https://soramame.env.go.jp/data/apiManual/2.html) explicitly directs national-station data to [MOE rules](https://www.env.go.jp/mail.html), PDL1.0 with attribution and identification of processing. Other government/NIES data require contact. |
| Other Tokyo live monitors | Excluded | Same manual requires local-government/NIES contact; no blanket clearance recorded. |
| NIES Tokyo 2019–2023 archive | Excluded | `research/snapshots/2026-10-14/air-tokyo/LICENSE.txt`: INTERNAL ONLY. No raw or derived archive values/registry copied into app output. |
| Bangkok Air4Thai live | Adapter implemented, public numeric output gated | ADR adopts the shape, but no verified live-feed redistribution grant beyond ambiguous catalog “Open Data Common” is recorded. Owner/source clearance remains required. No automatic override or environment switch silently enables it. |
| Bangkok 2011–2020 archive | Excluded | `air-bangkok/LICENSE.txt`: INTERNAL ONLY pending applicability verification. 2021–2025 absent; no Thai egress or TLS changes made. |
| Tokyo pollen, Feb–Apr | No measurement integration | [TMG Allergy Navi policy](https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/about.html) requires prior permission to republish. Homepage link only; source/permission TBD. No pollen quantities or forecast capability claimed. |

The national-data clause is the basis for the narrow Tokyo subset, not an
inference that the entire Soramame network is open. The portal's consultation
language for service partnerships does not grant broader rights. This feature
attributes MOE and says City Rating processes the data. Term-page URLs, retrieval
date and content hashes are recorded in `sources.json`; copyrighted term pages
and internal measurement archives are not copied here.

Concrete owner options: retain this national-monitor subset while requesting
clearance for Tokyo local-government measurements; confirm Air4Thai live and
archive rights with PCD; obtain TMG pollen permission or select a demonstrably
reusable alternative. None of those decisions is replaced by this PR.

## Runtime and honest scope

`GET /api/air/tokyo` requests only `SKT_CD=13104010`, previous/current month,
`PM2_5`. No key, client secret, generic proxy URL or archive read. Soramame's
JST hour 24 is normalized to next midnight; the UI shows observation and actual
successful retrieval timestamps explicitly in UTC. Numbers are hourly,
preliminary µg/m³, not AQI, a 24-hour compliance reading, or an annual mean.
On the acquisition check, the latest returned row was 2026-10-14 22:00 JST;
that observation is **stale**, not “live now”. No copied observation is bundled.

The Bangkok adapter reads the current provider registry, selects exact Bangkok
address suffixes, excludes closed/future monitors, and parses hourly `data`,
never `summary.average`. It does not use geocodes or the INTERNAL ONLY registry.
The public endpoint currently returns `permission_pending` without upstream
requests. The UI says current observation unavailable and links the source.

One-hour per-process cache with single-flight deduplication and failure cooldown;
8-second timeout per upstream request; 2 MB body limit; redirects rejected;
HTTPS verification unchanged. No unbounded retry. Cache is ephemeral and is not
a historical archive. A restart or multiple runtime replicas each has its own
cache; deployment is currently a single app instance. Client API requests are
same-origin, refresh every five minutes while visible and on visibility return;
client time never decides freshness. No API requests occur in static builds.

Summary: deduplicate by station/hour, reject conflicting duplicates and invalid,
negative, sentinel (>1000), missing and future values. At the latest valid hour,
require at least half the explicitly selected monitors; report median and
reporting/eligible count. One-monitor Tokyo is explicitly a location reference.
Counts are availability, **not city-area coverage**. Recent: age ≤3h. Stale:
3–48h. Older: unavailable, value null. Failure never produces zero. Upstream
failure can retain a cached observation only within the 48-hour observation-age
limit; retrieval date remains old. A client fetch failure hides the numeric
value. Missing historical and pollen slices render explanatory missing states.

## Reproducible seasonal ingestion (offline, no implicit publication)

```sh
packages/schema/node_modules/.bin/tsx scripts/air/seasonal.ts input.json 2026 > /tmp/air-season.json
```

Requires existing schema dev dependencies (`npm ci --prefix packages/schema`).
Input contract (illustrative **synthetic fixture**, not acquired measurements):

```json
{
  "unit": "µg/m³",
  "period": "daily_local_mean",
  "sourceUrl": "https://example.org/synthetic-test-fixture",
  "eligibleStations": ["a", "b"],
  "daily": [
    {"station":"a", "date":"2026-12-01", "pm25":37.5, "validHours":18},
    {"station":"b", "date":"2026-12-01", "pm25":37.5, "validHours":24}
  ]
}
```

The tool consumes already verified **local-date daily station means**, requires
18–24 valid hourly observations, reports rejected inputs, and hashes the entire
input. It is not a converter for the restricted XLSX/ZIP snapshots, and does not
claim their columns or station universe have been approved. Explicit station IDs
must come from the selected source's verified city/date coverage. Do not mix
Bangkok metro-ring stations into Bangkok proper or change station selection
without recording it in the input. All output is marked INTERNAL_ONLY until its
source is cleared. No output path under `app/` is written automatically.

Season: December 1 through March 31 of the next year (121/122 calendar days).
City-day: equal-weight arithmetic mean of valid daily station means, only when
≥50% of the selected monitor set reports. Numerator: valid city days with mean
≥37.5 µg/m³. Denominator: **valid city days**, with calendar and missing counts
reported beside it. Duplicates do not inflate denominator; conflicting duplicate
station-days are excluded. No missing day becomes a below-threshold day; empty
input yields null, not 0%. Incomplete coverage is `partial`, never a complete
season. The threshold is ADR's reporting rule, not a diagnosis or legal finding.

This is the bounded ingestion path for a future cleared/accumulated series.
No cron is installed; December 2026 collection is a future operational step,
not an already running capability. Historical metrics and pollen remain ticket
acceptance gaps even when every page renders the new panel.

## Validation

`cd app && npm run test` covers provider shapes, sentinel/missing values,
JST/ICT and hour24, same-hour denominators, duplicate/future data, yesterday's
observation staying stale, leap days, missing season days, 18-hour daily gate,
cache deduplication/cooldown, blocked source making no request, HTTP/size errors,
and EN/JA/RU panel/stale/permissions text. TypeScript/lint/build are separate gates.
