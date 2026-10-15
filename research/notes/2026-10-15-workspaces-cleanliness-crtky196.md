# CRTKY-196: coworking publication gate and cleanliness verdict

Checked against main `c21b0dcdede3a39250c11c13ee3e3aee4d0fa6ae`, 2026-10-15.
Plane issue `ea9322cd-ac0e-40db-a7b4-a190ff6c1401`, project
`1165669e-97b9-4f0d-a0a2-245f691d9bc4`. The issue explicitly accepts
“coworking facts live (or rejected with cause)” and a written, implemented or
rejected cleanliness verdict. This is that rejection path, with reproducible
evidence; it does not claim a new public feature.

## Result

- **Coworking proximity: reject publication from the present snapshot.** No
  existing accepted policy clearly grants the whole-snapshot exception needed
  for derived spatial counts. The coordinates are also incomplete and heavily
  concentrated in selected providers. No names, addresses, locator rows or
  derived proximity numbers are exported to the app.
- **Cleanliness: reject both a score and an `estimate` cleanliness fact.** The
  acquired measure is historical solid-waste tonnage, not observed street
  cleanliness. Retain it as research context about waste volume only. Do not add
  an empty availability panel or an unrelated tonnage row to neighborhood facts.
- No app, translations, schema, weights, categories, crowd/quietness, WorldPop
  outputs or existing institution implementation change. This verdict supplies
  source attribution below; no public slice means no new locale strings.

## Coworking: record and coordinate reconciliation

The [offline audit](../../scripts/audit_workspaces_cleanliness.py) reads the two
actual JSON files, validates declared counts, complete finite coordinate pairs,
address/source presence, and emits only aggregates. Its [committed result](2026-10-15-workspaces-cleanliness-audit.json)
includes input SHA-256 hashes, not locator records.

| Snapshot | Records | With address and HTTPS source | With coordinates | Without coordinates |
|---|---:|---:|---:|---:|
| Tokyo | 105 | 105 | 31 | 74 |
| Bangkok | 54 | 54 | 5 | 49 |
| Total | 159 | 159 | 36 | **123** |

There are no partial lat/lng pairs. These are acquired rows, not a verified
inventory of distinct, operating workspaces. Coordinate presence is not a
geocoding accuracy or address-completeness guarantee. The earlier **74** missing
count is Tokyo-only; it omits Bangkok's **49**.

Tokyo's 31 geocoded rows are 30 WeWork and one JustCo. Its 74 missing rows are
73 Regus and one Global Business Hub Tokyo. Bangkok's five geocoded rows are
three WeWork, one JustCo and one the Hive; 49 missing are 47 Spaces, one Regus
and one the Hive. Using only geocoded rows would measure provider coverage,
not general proximity. Missing locations cannot become zero nearby facilities.
The source note also leaves the requested “CCOC” provider unidentified.

### Publication basis: what is and is not established

1. [ADR acquisition policy](../decisions/2026-10-14-discovery-adoption.md)
   authorized one-off acquisition. It explicitly leaves graduation from
   `research/snapshots/` into `data/` to a later per-item decision.
2. CRTKY-196 proposes limited factual counts/names with links and forbids
   scraping republication beyond that scope. This is a product brief, not
   evidence of source permission or a blanket override of the snapshot policy.
3. The [coworking LICENSE.txt](../snapshots/2026-10-14/coworking/LICENSE.txt)
   marks **the whole seven-provider snapshot INTERNAL ONLY — not for site
   publication**, with no open license found. It explicitly disallows public
   lists/addresses without permission. Unlike the [JNTO snapshot policy](../snapshots/2026-10-14/medicine-jnto/LICENSE.txt),
   it contains no express counts/links publication exception.
4. A link-only directory of provider homepages would avoid exporting locator
   rows, but would not establish nearby workspace availability or satisfy the
   proposed proximity feature. Publishing a token subset of names would have
   the same relevance/coverage problem. Neither is presented as implementation.

This is an application of the repository's recorded publication policy, not a
new legal determination about factual reuse. A bounded derived count might be
possible later, but its permitted use and evidence are not settled by these
records. No mass geocoding, provider requests or OSM substitution was attempted.
The prior OSM rejection remains: [Tokyo](2026-10-13-institutions-crtky180.md#6-coworking--reject-same-verdict-as-bangkok)
found 26 POIs with no major chains; [Bangkok](../bangkok/notes/2026-10-13-institutions-crtky145.md)
found five citywide.

**Reopen prerequisites:** document a provider-supported or otherwise reviewed
publication basis for a precisely bounded derived use; choose the public
consumer and coverage claim; resolve provider identity/duplicates/active status;
then verify all required coordinates and their reuse terms without guessing.
Any remaining missing coverage must be explicit. A newly licensed source or
demonstrably improved OSM coverage is a separate evidenced option, not an
automatic fallback. No new owner decision is invented here.

## Bangkok waste: exact semantics, coverage and quality

The saved `garbage-metadata.docx` dictionary describes
`ข้อมูลปริมาณขยะมูลฝอย จำแนกตามเขตการปกครองกรุงเทพมหานคร` — municipal
solid-waste quantity by Bangkok administrative district. `garbage53`…`garbage61`
are **tonnes for the reported year**; `garbageperday53`…`garbageperday61` are
**tonnes/day**. BE 2553–2561 converts to **2010–2018**. Dictionary revision
4 June BE 2563 is **2020-06-04**, not a newer observation year. The dictionary
does not establish street cleanliness, collection effectiveness, litter,
service satisfaction, or whether “year” is calendar versus fiscal year.

The audit checks every tidy value against the original wide CSV using decimal
arithmetic, all year conversions, unique district/year keys and exact slug joins:

- **459 rows = 450 district-years (50 × 9) + 9 other/unclassified rows.**
- Codes **1001–1050** join all 50 current district slugs one-to-one.
- **1000 = อื่นๆ (“other”), not a city total.** It has no district slug and is
  excluded from the 50-district sums. Do not label the 50-district sum as including
  all waste reported in the source.
- 2018 sum across the 50 districts is **3,692,869.44 tonnes**; code 1000 separately
  reports **219,418.80 tonnes**. These are historical source quantities, not new
  resident-adjusted or cleanliness estimates.
- Dusit 2012 reports **116.37 tonnes** but **317.96 tonnes/day**; no automatic
  ×1000 repair is justified. All **50 district daily values in 2017 are 0.00**
  despite positive annual quantities. Zero must not mean no waste.
- A diagnostic comparing annual tonnage with daily tonnage × 365/366 flags
  **1 district-year in 2012, 41 in 2016 and 50 in 2017** at >1% (and >1 tonne)
  difference. This diagnostic is not a fiscal-year validation or a correction.
  The underlying mismatches remain unresolved.

Higher tonnage could reflect population, commerce, collection coverage or other
activity; its relationship with street cleanliness has no established direction.
Dividing by population/area or labeling it `estimate` would not validate that
relationship. Even internally consistent 2018 observations are eight years old
at this review. A historical waste-management explainer could cite them with
these limits, but that would serve a different purpose from the requested
neighborhood cleanliness fact. Research-only context is the selected outcome.

### Attribution and alternative-source boundary

- Bangkok Metropolitan Administration, [national dataset 731a8cb0-d563-45ca-93ae-52e3de47e474](https://data.go.th/dataset/731a8cb0-d563-45ca-93ae-52e3de47e474),
  CSV resource `1c0a2c55-d28e-446d-bbdf-9b810b8c0035`; acquired 2026-10-14 via
  [Wayback 2023-12-20](https://web.archive.org/web/20231220151243/https://data.go.th/dataset/731a8cb0-d563-45ca-93ae-52e3de47e474/resource/1c0a2c55-d28e-446d-bbdf-9b810b8c0035/download/garbage.csv).
  **CC BY per saved national-catalog evidence**; a license version is not established
  here, so do not relabel it CC BY 4.0. [License/source record](../snapshots/2026-10-14/cleanliness-bangkok/LICENSE.txt).
- The saved district-code mapping uses Thai Wikipedia administrative codes
  (CC BY-SA 4.0 for source text). The audit checks identifiers and slug joins;
  it does not export Wikipedia prose.
- `alt-bma-garbage-service.csv` is a different fee/service dataset with unclear
  units and **License not specified**, explicitly INTERNAL ONLY. It is not a
  replacement cleanliness source and is not consumed by this audit.

**Reopen cleanliness** with a source measuring a defined relevant phenomenon
(e.g. dated litter inspections or clearly framed complaints), usable publication
terms, district coverage and validated interpretation. Fresh waste tonnage alone
does not establish cleanliness. No BMA safety data or CRTKY-195 work is included.

## Verification and acceptance boundary

Run from the repository root, offline:

```sh
python3 scripts/audit_workspaces_cleanliness.py
uv run --offline --with pytest pytest -q scripts/test_workspaces_cleanliness.py
```

Tests compare the saved aggregate evidence, reject partial/nonfinite coordinates,
duplicate/missing district-years, wrong codes/slugs/calendars and drift from raw
CSV values. No raw locator rows are emitted. The audit does not repair source
anomalies or assert legal clearance. The app is unchanged, so no app build or
public-layout validation is claimed for this research/rejection deliverable.
CRTKY-190 reconciliation is a separate read-only report to the orchestrator;
this PR does not close that issue, change its radii or add schools.
