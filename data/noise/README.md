# Day/night quietness (CRTKY-189, ADR #4)

Standalone station-page **estimates**, 1–10 with higher = quieter, for Tokyo
(1,493 stations) and Bangkok (133 station areas). No rating category, weight,
filter, crowd score, district or grid changes. Only measured references are
shown in dB. The existing Quietness rating remains the crowd-based score.

## Reproduce offline

From the repository root, Python 3.10+ (standard library only):

```sh
python3 scripts/noise/build.py          # regenerate all four products
python3 scripts/noise/build.py --check  # byte-for-byte drift check; no writes/network
uv run --with pytest --with pydantic --with-requirements scripts/requirements-ingest.txt python -m pytest scripts/ -q
```

Products:

- `app/src/data/noise/quietness.json`: station facts, proxy values, one nearest
  eligible roadside reference within 800 m, optional municipal complaint counts.
- `app/src/data/noise/calibration-summary.json`: localized methodology statistics.
- `data/noise/calibration.json`: coefficients, evaluation IDs, exclusions,
  baseline comparison, source paths and SHA-256 hashes.
- `data/noise/tmg-matched.json`: every matched reading, exact source CSV row,
  original address/road/dates, archival coordinate and computed proxy features.

Run `npm run gen --prefix packages/schema` after changing the JSON schema.
New noise types are generated for Python and TypeScript; only these new types
are vendored with original snake_case field names for the app-only Docker build.
No manual edits to generated types or data.

## Inputs, lineage and licenses

`raw/*.source.json` pins source URLs, original Overpass queries and bounding
boxes, retrieval times, source timestamps, compressed-file SHA-256 and license.
The builder verifies raw OSM and H25 hashes before use. All consumed inputs,
including station coordinates, ward mapping and pipeline source, are hashed
in `calibration.json`. OSM geometry totals: Tokyo 47,718 road ways / 13,652
nightlife objects; Bangkok 7,552 / 860. Geometry is committed as deterministic
gzip (~10.5 MB combined), allowing a clean checkout to rebuild without Overpass.

- **OSM, ODbL 1.0, © OpenStreetMap contributors.** Acquired 2026-10-15 with the
  existing tourism script's mirror rotation. Tokyo nightlife came from a
  mirror dated **2026-06-01**, Tokyo roads and both Bangkok extracts are dated
  **2026-10-15**. The page shows the oldest input date, not the download date.
  These are mapped objects, not an exhaustive inventory of actual venues or
  traffic. No credentials or token-backed ratings refresh are involved.
- **TMG Bureau of Environment, CC BY 4.0.** Original R1–R5 routine-monitoring
  CSVs are under `research/snapshots/2026-10-14/noise/`; CP932, day 06–22 and
  night 22–06 Leq. Only routine monitoring is used; request-limit tables,
  white-paper CSVs and Chofu data are excluded.
  [Annual source pages](https://www.kankyo.metro.tokyo.lg.jp/vehicle/noise/result/cyousakekka).
- **TMG H25, CC BY 4.0.** Official FY2013 JGD2011 coordinates in
  [`raw/tmg-h25.csv`](raw/tmg-h25.csv), downloaded 2026-10-15 from
  [H25_kekka.csv](https://www.opendata.metro.tokyo.lg.jp/kankyo/vehicle/noise/H25/H25_kekka.csv).
  H25 sound levels are **not** displayed or fitted: only its coordinates are
  used after exact full-address equivalence. JGD2011 is treated approximately
  as WGS84 for these coarse distances, without inventing geocodes.
- **TMG Statistical Yearbook 19-11, CC BY 4.0.** Committed 2022/2023/2024
  edition CSVs supply the corresponding fiscal year's municipality totals.
  They are contextual complaint counts, **not calibration inputs or levels**.
  Suppressed/non-numeric values stay absent. Joins require the canonical station
  prefecture code `13` (Tokyo), no conflicting ward-map prefecture, and an exact
  `city_name` municipality match. Tokyo special wards are municipalities here;
  the map's `ward_name` may be a smaller district and is not used for this join.
  Missing or outside-Tokyo identities are omitted, including names shared with
  Chiba, Saitama or Sagamihara wards.
- **PCD, catalog metadata only.** `pcd_resources_index.json` and its source
  `pcd_ckan_package_show.json` identify station/annual CSVs; the underlying files
  are absent. The station CSV retry on 2026-10-15 timed out in TLS handshake.
  No TLS bypass, alternate egress or owner-pending license decision was made.
  No measurement, station coordinate or coverage is inferred from metadata or
  transcribed from the research prose.

To intentionally refresh proxies (requires network):

```sh
python3 scripts/noise/fetch.py --city tokyo --refresh
python3 scripts/noise/fetch.py --city bangkok --refresh
python3 scripts/noise/build.py
```

Review changes in source timestamps, coverage, distributions and retrospective
errors before publishing a new model version. A fetch failure is fatal and
never written as zero venues/roads. Empty, truncated or hash-mismatched extracts
fail the build. A target whose full 2 km catchment is outside either bounding
box receives `missing_proxies` and null estimates. Even complete extract extent
does **not** establish complete OSM mapping. Distances use local metric
projections (35.6° Tokyo / 13.7° Bangkok), to line segments rather than road-way
centres. The fixed extract margin covers every current station catchment.

## Frozen model v1

```
R = max(exp(-primary_or_trunk_distance_m / 200),
        exp(-motorway_or_motorway_link_distance_m / 400))
V = ln(1 + OSM nightlife objects within 800 m)
internal_day   = 65.03403237 + 1.89732932 * R + 0.5 * V
internal_night = 58.74052490 + 3.96545326  * R + 1.5 * V
index = round(clamp(10 - 9 * (internal_prediction - 45) / 35, 1, 10), 1)
```

The intercept and shared non-negative road coefficient minimize squared error
on FY2019–2022 matched roadside readings. The road decay lengths, shared road
pressure, **fixed nightlife coefficients 0.5 / 1.5**, and index endpoints 45/80
are **heuristics**, not fitted acoustic propagation, measured entertainment
noise or legal limits. Roadside-only data cannot identify entertainment effects:
an earlier unconstrained fit set nightlife coefficients to zero. A pooled road
term avoids pretending to identify a separate expressway effect from this small
sample. Frozen coefficients are not tuned to the reported evaluation errors.
Both periods use the same display scale. More mapped venues or closer roads
cannot make the estimate quieter; night need not be quieter than day.

The fitted intercept comes from roadside data. Predictions for residential,
rural or other unsurveyed settings are extrapolations: the model does not
establish indoor noise, building shielding, sleep quality or residential
accuracy. Rail, aircraft, construction, actual traffic and venue opening hours
are omitted. Decimal index values express a continuous proxy, not 0.1-point
measurement accuracy. Cross-city equivalence has not been validated.

## Calibration and retrospective evaluation

Exact matching normalizes Unicode width, whitespace and address separators
(丁目/番/号). It does not remove house numbers, fuzzy-match addresses, geocode
place names, reuse station coordinates or assign municipal centroids. An old
address with conflicting coordinates is rejected. A matching block address
still does not establish the identical microphone location across a decade;
references and distances are labeled approximate.

| FY | Valid day/night readings | Exact address matches | Unmatched |
|---|---:|---:|---:|
| 2019 | 284 | 32 | 252 |
| 2020 | 284 | 23 | 261 |
| 2021 | 280 | 25 | 255 |
| 2022 | 273 | 19 | 254 |
| 2023 | 267 | 83 | 184 |

Training: **99 rows / 68 addresses** from FY2019–2022. Retrospective evaluation:
**76 FY2023 locations**, excluding the seven FY2023 addresses already present
in training. The committed split additionally has no evaluation coordinate
within 100 m of a training coordinate. No refit uses the evaluation rows.

| Target | Final predictor MAE | Training-mean baseline MAE |
|---|---:|---:|
| Roadside daytime Leq | **3.225 dB** | 3.304 dB |
| Roadside nighttime Leq | **4.296 dB** | 4.278 dB |

**The night model does not outperform the mean baseline.** Earlier fits were
inspected during development, so these are retrospective, geographically
separate errors, not untouched validation or prospective accuracy. Current
OSM (June/October 2026), FY2013 coordinates and FY2019–2023 noise observations
also have a substantial temporal mismatch. No error for the 1–10 index is
claimed: there is no measured index ground truth. These MAEs do not establish
accuracy away from the sampled roadside locations or validate the nightlife
heuristic.

103 Tokyo station pages have a nearest matched **FY2023** roadside reference
within 800 m. Each includes its original address, road, campaign dates, source,
day/night Leq, approximate distance and coordinate year. H25-only measurements
are never substituted. Remaining station pages explicitly say no reference was
matched in this dataset, without claiming that no measurement exists elsewhere.

## Bangkok acceptance limitation

All 133 station areas get an **uncalibrated transfer estimate** from the same
proxy model. **Zero acquired PCD anchors; no Bangkok MAE.** The five PCD stations
in the discovery note are a planned calibration source, not five acquired
measurements. The UI says this next to the pair. The 06–22 / 22–06 windows are
model conventions here, not measured Thai reporting periods. PCD 24-hour Leq or
a latest-hour sample cannot produce measured day/night means. No spatial
interpolation, invented levels or guessed monitor coordinates are used.

This implements the explicitly permitted estimate fallback. Full five-station
PCD calibration remains blocked on acquisition and valid matching; it must not
be recorded as completed by virtue of full estimate coverage.
