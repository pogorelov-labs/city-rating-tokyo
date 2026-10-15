# Factual context — CRTKY-195 (partial)

This layer publishes two dated, metropolitan factual citations on
`/{locale}/methodology#safety-context`, in EN/JA/RU. It does not join stations,
districts, ratings, confidence, weights or composite calculations.

## Public scope and provenance

- **Road traffic:** Keishicho statistics, calendar 2025, Table 10: 30,176 accidents
  and 134 fatalities, covering MPD jurisdiction including expressways and islands.
  Counts have no exposure denominator; they are not per-capita rates or station
  catchment risks. Kanagawa, Saitama and Chiba are outside this source's scope.
  The official annual-book introduction confirms calendar-year coverage unless
  otherwise indicated. We quote the table's reported fatalities without
  inventing a 30-day or other fatality definition.
- **Welfare survey:** Fukushi's January 2026 rough count, 507 people including
  307 in the 23 wards, 18 in Tama and 182 on nationally managed rivers. Both
  pages of the pinned PDF were visually checked on 2026-10-15. Page 1 explicitly
  excludes national rivers; page 2 includes them in the grand total. The public
  brief quotes only the total and scope, not ward rows or personal attributes.
  This is not a census of everyone experiencing homelessness, a service directory,
  service capacity, or a safety proxy. No facility proximity is inferred.

`sources.json` pins the workbook, independent digest, survey PDF and manually
verified survey summary by SHA-256. Official source and document URLs, periods,
units, geographic scope and verification date accompany the output. Verification
date is not observation date; the January period records month-level precision,
not a claim that every day was surveyed. The source-page check date is not the
publisher's update date.

The snapshot `tokyo-misc/LICENSE.txt` permits **factual citation only**. Neither
the workbook/PDF nor extracted local rows are republished in app assets. This is
not an open-data licence or a general right to redistribute the internal snapshots.
The builder explicitly emits only the two reviewed citations and provenance.

## Reproduction

From the repository root, with Python 3.10+ and no extra dependencies/network:

```sh
python3 scripts/safety/build_context.py
python3 scripts/safety/build_context.py --check
pytest scripts/test_safety_context.py
```

The builder parses the original XLSX total using the standard library and checks
it against the digest and reviewed citation. It never sums hierarchical totals.
The image-only survey PDF is hash-checked; the summary is the input after visual
verification, not falsely described as automated OCR. A changed source hash,
inconsistent total or publication policy fails before output is written. Review
new periods, scope and citation permission before updating the manifest.

## Outstanding acceptance: Bangkok

| Required work | Evidence / boundary | Exact withheld output or next action |
|---|---|---|
| 216-point BMA registry brief and editorial validation | `research/bangkok/notes/2026-10-13-safety-crtky150.md` documents `ced0066` / `aa1d9beb-3b71-4f5c-b7c3-d3af6b5399ca`, `14-69.csv`, 216 records, 50 districts, no coordinates. The referenced raw CKAN snapshot/manifest is absent from the repository. Bounded GET of the documented BMA metadata endpoint failed on 2026-10-15; the national catalogue returned HTTP 403. | Missing **source evidence**, not a new policy choice. Recover the full official snapshot with resource identity/date/hash; validate district names/counts and administrative category coverage against editorial briefs. Do not claim this pass completed from the research note. Proposed brief: district / registry year / registered-place count / administrative-category caveat / citation; no proximity or score input. |
| Bangkok road-risk points and clusters | `accidents-bangkok/LICENSE.txt`: INTERNAL ONLY; explicit licence absent, `isopen=false`; Google My Maps / Longdo reuse unclear. 50 risk locations and 126 clusters are a different source from the 216-point registry. | **Owner publication decision** remains required per source. Withhold point names, coordinates, district counts, maps and derived local accident briefs. A future approved brief needs separate registry year (2025) and underlying count year (2023), not a single misleading date. |
| Per-point fatalities/injuries | Not verified in the retained accident materials. | Missing fields cannot become zeros or invented facts. Remain absent even if publication is later cleared. |
| Services proximity | Survey totals do not locate services; earlier curated lists have separate publication/revalidation questions. | No facility list or nearest-service claim in this slice. A separately verified and approved service directory is required for such output. |

Bangkok's public paragraph only explains the existing editorial/road-coverage
limit and that missing evidence is not zero risk. It publishes no blocked values.
The 2026-10-14 ADR #11 permits registry facts/validation; it does not substitute
for missing primary evidence or waive the accident snapshot's publication gate.

## UI and validation contract

Use the existing methodology typography and spacing: Inter/Japanese system
fallback, white background, gray-900 headings, gray-700 body, gray-600 dates and
blue-700 underlined source links, 44px link targets. A plain sequence of road,
welfare and Bangkok scope sections preserves the product's reading layout;
statistic cards/maps or danger colours would imply local comparisons not supported
by this evidence. No animation or new UI dependency is needed.

Verify real localized rendering, links, narrow-screen layout and keyboard focus.
The unit tests render the async component using real ICU translations/formatters;
pipeline tests check pinned inputs, negative provenance cases, aggregate scope
and exclusion of blocked records. Check ratings/composite inputs remain unchanged
against the branch base. Record browser/paint/build checks in the PR; this document
does not claim a check merely because it is listed here.

CRTKY-195 remains partial until the missing source/validation and publication
decision are addressed. No new owner approval is needed for the citation-only
slice already authorized by the orchestration instructions.
