# Institution facts (CRTKY-190)

This offline pipeline publishes aggregate counts on existing Tokyo station and
Bangkok station-area/district pages. It does not change ratings, categories,
weights, or the population/noise pipelines. Bangkok English-service medicine is
**incomplete**, not zero: no suitable publishable source has been verified.

The owner accepted **2 km straight-line medical-facility proximity**, superseding
the original issue's 800 m acceptance. Embassy/diplomatic-office station counts
retain 800 m straight-line circles. Bangkok district counts use containment in
committed district boundaries, not a circle around the district center. No Tokyo
district pages or schools are introduced.

## Reproduce and verify

Python with Shapely >=2.1 is required; the existing pipeline CI environment already
provides it. No network access, raw acquisition, or database writes are involved.

```sh
python scripts/institutions/compute-institutions.py
python scripts/institutions/compute-institutions.py --check
pytest scripts/test_institutions.py
```

The command writes the same deterministic JSON bytes to `data/institutions/` and
`app/src/data/institutions/`. `--check` fails on either missing/stale copy without
writing. The regression suite rebuilds from the actual committed inputs and
compares both copies. SHA-256 provenance records the input snapshots, licenses,
QA summary, anchors and boundaries. No timestamps from the execution environment
are used. A changed input requires deliberate regeneration and diff review.

`getInstitutions()` is the public accessor; existing pages render
`InstitutionFacts`. Old `embassies_800m` district-center fields remain only in the
frozen Bangkok population baseline and are not public institution consumers.
The former NaturalEnvironment institution rows are removed to avoid presenting
stale embedded counts. The new overlay is independent of broad environment and
Bangkok rebuilds; its check catches changed anchors/boundaries before publication.

## Geometry and coverage

- Tokyo: all 1,493 canonical station slugs. Pipeline and app anchor coordinates
  must agree exactly. Positive counts match the previously shipped values,
  including Hiroo: 40 diplomatic records and 61 medical facilities.
- Bangkok: all 133 canonical station-area IDs and all 50 district slugs. Station
  circles use each published area representative point, not every platform.
- Distances use the haversine formula with Earth radius 6,371,000 m and an
  inclusive threshold. These are not walking routes or travel-time estimates.
- District polygons come from `app/src/data/bangkok/geometry.json` (published,
  simplified OSM boundaries). Input coordinates are latitude/longitude and are
  explicitly converted to longitude/latitude; holes and multipolygons survive.
  A point on a shared boundary is assigned once to the lexicographically first
  district slug. Overlapping interiors fail rather than double count. There are
  no shared-edge or outside points in this pinned 79-record snapshot. Simplified
  boundaries remain a limitation for future near-edge records.
- A computed zero means no matching **snapshot records**, not proof of absence.
  A missing canonical join is unavailable; Bangkok medicine is explicitly null.
- JNTO counts use the existing 508 Tokyo-prefecture records. Other prefectures
  are not included, including near-border stations. The UI discloses this scope
  and advises confirming language support and opening hours with the facility.

## Sources and QA lineage

The embassy snapshot is dated 2026-10-14; upstream OSM timestamps are 2026-06-01
(Bangkok) and 2026-07-24 (Tokyo). OSM is ODbL 1.0, Wikidata CC0. The UI links both
licenses. These are diplomatic offices, including embassies; the input's
`office=diplomatic` selection is broader than embassies alone. Citywide
OSM/Wikidata matching does **not** establish two-source validation for every
record, and no strong confidence badge is assigned.

The pinned `embassies/summary.json` is the QA lineage, not a nonexistent
per-feature `properties.qa` field:

- Ireland in Bangkok and Armenia in Tokyo are retained with corrected country
  names; original OSM `IR`/`AR` disagreements are recorded in the summary.
- Fictional Syldavia is excluded. Tokyo's two defunct records and duplicate
  French embassy are excluded. Unnamed records stay excluded.
- 10 Bangkok and 21 Tokyo Wikidata-only records without coordinates remain
  excluded; no coordinates are inferred.
- All 79 Bangkok and 167 Tokyo retained records have validated Point coordinates.
  New exact duplicate records, invalid/missing coordinates, broken corrections,
  and reintroduced excluded named records fail validation.

JNTO's `medicine-jnto/LICENSE.txt` permits aggregate counts and links, not row
republication. Public outputs contain no facility names, addresses, telephone
numbers, coordinates, or inferred categories. The UI uses **medical facilities**
and links the live [JNTO directory](https://www.jnto.go.jp/emergency/eng/mi_guide.html)
with © Japan Tourism Agency / JNTO attribution. No Bangkok hospital tag is treated
as evidence of English-language service.

## Observed Bangkok result

All 79 retained records are assigned once; 10 of 50 districts have positive
counts. The other 40 explicitly have zero snapshot records. Station-area circle
counts are unchanged (26 positive areas out of 133).

| District | Old center-circle count (800 m) | District containment count |
| --- | ---: | ---: |
| Pathum Wan | 9 | 23 |
| Watthana | 1 | 16 |
| Sathon | 2 | 15 |
| Bang Rak | 3 | 11 |
| Khlong Toei | 1 | 6 |
| Din Daeng | absent | 2 |
| Huai Khwang | absent | 2 |
| Wang Thonglang | absent | 2 |
| Lak Si | absent | 1 |
| Ratchathewi | absent | 1 |

These shifts correct the spatial question; they do not indicate new missions or
source refreshes. The complete 50-district table is the generated
`data/institutions/district-institutions.json`.

CRTKY-190 remains partial until Bangkok English-service medicine has a verified
publishable source and a reviewed join. No separate owner preference is needed
to show the missing-data state, and no source entitlement is inferred from this
implementation authorization.
