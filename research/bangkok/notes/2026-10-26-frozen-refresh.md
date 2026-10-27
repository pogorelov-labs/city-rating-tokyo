# Bangkok frozen snapshot refresh — remediation evidence

Prepared 2026-10-26 against `d7e2ddf5c5d906e155e0f310015f45441360fa06`.
This is a separate proposed data refresh, not a code release or an amendment to
v0.1.0. No merge, tag, release or v0.1.0 release-note change is part of this work.

## Frozen inputs and acquisition

The committed [input manifest](../../../data/bangkok/refresh-inputs.json) records
90 files with byte lengths and SHA-256 hashes, the complete Geofabrik source
manifest, Overture release/source inventory, and all **547** Wikidata entity or
Commons page revision IDs/timestamps. Build date is frozen to **2026-10-26**.
Raw files remain gitignored; the full cache, PBF and manifest are also retained
in the city-rating-16 AO artifact archive (archive details below).

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `thailand.osm.pbf` | 329,280,467 | `e8373240cf0be47cc641f2c8627e674064d8c47f4ff2a11f6a33fcbfc9a50949` |
| `overture_places.parquet` | 16,706,966 | `4d387194906eb0c6350d86ed017fd7e4339271c626dc605d8834cb6470dc3040` |
| `wikidata.json` | 1,594,260 | `441ddd4c7fc321ed9fb3fb426b126b90ff99ed5af6a8d3b26a5cd1b3b804ac56` |
| `commons.json` | 267,561 | `91850764e76218ed61d2274065aaf436b82fb792c3da87f99f2d844872722e56` |
| `station_wikidata.json` | 2,364,493 | `d7407f5f5a4746d99d24e80e105b3a40da259da0e24916b151933d3628f35887` |
| `station_commons.json` | 810,311 | `a59044007a34cc8139ba0664d5c6a13208adadfe7f6393449f17169c9fb46931` |
| `tha_ppp_2020_constrained.tif` | 28,878,233 | `400dc5435e15e78ce6b5e510327ec863c62d209011ce1b03cad4445773753d42` |
| `thaifloodrisk.zip` | 68,400 | `8ce4a1c95771f56204d979dafcb61df44f4f2aee4e19fbf40adc75ebbb8b8ddf` |

- Geofabrik URL: `https://download.geofabrik.de/asia/thailand-261024.osm.pbf`.
  Replication timestamp **2026-10-24T20:20:51Z**; HTTP Last-Modified
  `Sat, 24 Oct 2026 23:00:29 GMT`. Retrieved 2026-10-26T05:57:31.941867Z;
  extraction completed 06:01:45.570875Z in **382.1 s**, including the download.
  The existing PR #145 extractor produced all 12 OSM JSONs. No Overpass query
  was used. The prior evidence archive was read before implementation.
- Overture **2026-09-23.1**, **309,704** rows, confidence >=0.6 and open/null
  operating status, unchanged bbox/category rules. Acquisition completed at
  2026-10-26T06:04:17Z. Output is sorted by ID; its parquet byte hash differs
  from the previous unsorted extract, while the generated grid matches it.
- Wikidata/Commons acquisition: **06:02:30Z–06:02:56Z**, 50 district entities,
  50 image pages, 232 station entities, 215 station image pages. `info` and
  `revisions` are requested in the same calls as the consumed data. Commons
  image timestamps and SHA-1s are recorded separately. Fetches remain live;
  exact local payload hashes, not HTTP revision replay, are the reproducibility
  contract. Page revision IDs cannot freeze transcluded Commons extmetadata or
  externally hosted thumbnail bytes. No missing revision was invented.
- WorldPop is the authorized **2020** constrained raster, unchanged; flood is
  the authorized ThaiFloodRisk ZIP plus the committed `flood.json`, unchanged.
  Copies came from city-rating-4 and the human checkout respectively. The full
  builder reads `flood.json`, not the ZIP. Their exact known hashes match.

## Reproduction and repeatability

```sh
uv run scripts/bangkok/fetch-geofabrik.py --url https://download.geofabrik.de/asia/thailand-261024.osm.pbf
uv run scripts/bangkok/fetch.py --only wikidata commons station_wikidata station_commons overture_places
# Restore the two authorized population/flood caches; verify against the manifest.
uv run scripts/bangkok/freeze-inputs.py --verify
/usr/bin/time -p uv run scripts/bangkok/build.py --inputs-manifest data/bangkok/refresh-inputs.json
uv run scripts/bangkok/apply-enrichments.py
```

For an exact replay, restore the archived raw files instead of fetching live
Wikimedia again. The builder verifies all 90 file hashes before computation and
uses the manifest's date. A mismatched/missing input fails before output writes.
`freeze-inputs.py` refuses to overwrite a manifest. Baseline capture similarly
refuses to overwrite an existing current baseline; historical files were never
rewritten. The committed artifacts are the final reviewed baseline, not an
attempt to reuse the old adoption signatures for new geometry.

Final full build: **6.21 s wall** (**5.8 s** reported by the builder).
Repeat: **6.22 s wall** (**5.9 s** reported). All seven app Bangkok JSONs,
`signals.json` and the binary reproduced **byte for byte**. Reapplying enrichment
was also a byte-identical no-op. Python dependency ranges are not a complete
package lock; the raw-input determinism claim is for this recorded environment,
not every future GEOS/numpy/rasterio version.

## A. Enrichment preservation

`build.py` calls `enrichments.apply_enrichments` automatically after the spatial
calculation and before writing outputs. The standalone command uses the same
function. It validates source SHA-256s, exact 133-area/50-district joins and all
required fields before mutation. Missing sources/joins fail; no zero fallback
is used. The committed [enrichment baseline](../../../data/bangkok/enrichments-baseline.json)
records preservation source hashes, dates and metric definitions.

| Observation | Preserved result | Source/metric |
| --- | --- | --- |
| Station tourism | all **133** areas have all 3 fields; nonzero hotels **99**, attractions **66**, badges **19** | `data/tourism/proximity.json`, OSM fetched **2026-10-15**, counts within 800m of station; badge >=50 hotels OR >=8 attractions |
| Nana / Asok | **197/3/true**, **156/4/true** | exact retained tourism snapshot |
| Michelin | all **9** district field pairs; sums **8 stars / 12 Bib** | `data/michelin/proximity.json`, computed **2026-10-15**, Guide **2026**; `stars` and `bib_gourmand` mapped exactly |
| Legacy district embassy field | **5** districts, sum **16** | release-commit district facts, generated **2026-09-30**; observation date unknown |

Embassy values are exactly **Bang Rak 3, Khlong Toei 1, Pathum Wan 9, Sathon 2,
Watthana 1**. Institutions documentation calls these legacy district-center
fields; the original calculation/center is not independently proven. The
institutions snapshot has a different metric, `embassies_inside_district`
(Bang Rak **11**, Pathum Wan **23**, total **79**), and has not been remapped.
The provenance gap is retained explicitly. The original institutions sources'
2026-10-14 snapshot date, source dates and input hashes are preserved in the
baseline. Separate institution counts remain unchanged.

Tests strip all enrichment fields before mutation, compare every result against
the retained source/release baseline, assert the exact counts above, run twice,
and check missing-source/join failures leave both documents unchanged.

## B. All ten original validation gates

| Original gate | Resolution |
| --- | --- |
| Population committed snapshot/scope (1) | New `population-baseline-refresh-2026-10-24.json` pins new geometry, precise POI terms, crowd raw and non-crowd signatures; current comparison regenerated from it. Historical `population-baseline.json` unchanged. |
| Population original adoption/idempotent replay (1) | Historical release files are frozen in `scripts/fixtures/bangkok-population/adoption/`. Both historical and refresh cases run the original adoption/replay contract; no signature relaxation. |
| Six incompatible-snapshot guards (6) | Both baselines test POI, crowd, rating, provenance, anchor and original-checksum mutations and prove no writes. Geometry mismatch and missing explicit baseline are also rejected. |
| Normalization golden (1) | Original `bangkok-golden.json` unchanged and tested against frozen historical signals. Added current `bangkok-refresh-2026-10-24-golden.json`. |
| Transport resident-weighted median (1) | Header medians and composite anchors use the exact uint8 weight units published in the grid. Cell normalization retains full precision weights. Regression covers quantization crossing 50%. |

`rebuild-population.py --baseline adoption|refresh-2026-10-24` requires an
explicit selection. The refresh freezes the precise POI log term, avoiding the
old four-decimal reconstruction error (e.g. Bang Bon **6.5281 -> 6.5280**).
WorldPop total stays **10,887,568.273106098**; all district crowd ratings stay
unchanged. Current replays preserve published snapshot bytes and formatting.

The [complete aggregate review](2026-10-26-frozen-refresh-review.json) records
**all 489 changed rounded raw aggregates** and **all 54 golden changes**, each
with before/after values and an acceptance reason. Tests require complete
coverage of the golden diff. The 54 changes comprise **49 rating values**, four
confidence/source pairs and the unweighted harness p5 anchor **4.1 -> 4.2**.
Confidence changes: Nong Chok essentials and Thawi Watthana food gain OSM;
Victory Monument sports gains OSM and culture loses OSM at existing thresholds.
No normalization formula or threshold was changed.

The prior median crossing was full-precision total **28,154.78** with <=5 weight
**14,076.79** (49.9978689%), versus published weights **28,159.18** and
**14,081.056** (50.0052061%). Chosen canonical transport median is **5**, matching
binary decoding. Integer weight units avoid floating accumulation ambiguity.

## C. Geometry, attribution and quality review

All **25 district / 14 area** changed park-hectare facts were independently
reconstructed from the pinned green polygons, including the builder's original
unsimplified Voronoi/disc catchments. Every rounded result agrees. The JSON
review lists every contributing OSM ID, tags, area and polygon validity.

- **Nong Khaem, green 2 -> 5:** raw **0.4876 -> 0.9012**; current park-like
  geometry **15.1405 ha**, with equal sum/union area (no overlap inflation).
  `way/1482579416` is a valid **9.4990 ha** `leisure=garden` without restrictive
  access tags. Its recorded v1 is **2026-02-24T14:47:09Z**, so this is not
  evidence of a new park opening. The unchanged model accepts gardens >=2000m²
  without private/no tags; access is a mapping assumption, not a field visit.
- **Setthabutbamphen, green 2 -> 7:** raw **0.0550 -> 1.6667**. Valid multipart
  `relation/21083246` (Bueng Krathiam Park), **7.4385 ha** overall, lies
  **105.45 m** from the station. Exact unsimplified catchment intersection is
  **6.3615 ha -> 6.4 ha**. Its v1 is **2026-07-09T20:09:34Z**. Measuring against
  the simplified app polygon gives 6.3407 ha; facts correctly use the raw
  catchment. No source geometry or green scoring was manually changed.
- **Nong Chok, park 25.1 -> 19.9 ha:** current sum/union both **19.8878 ha**.
  Largest contributors are `way/1287037724` (**7.5631 ha**, v1
  2024-05-27T11:03:41Z), and Nong Chok Park `way/191550091` (**5.9559 ha**).
  The older raw cache is unavailable, so the 5.2ha historical difference cannot
  be assigned to a particular edit or treated as a measured loss of parks.
- **Thon Buri, green 2 -> 4:** current park sum/union **4.6176 ha**; contributors
  and access tags are listed in the review. Existing access/category assumptions
  remain. These ranks describe the source snapshot, not audited public access.

Nine polygon/area notices remain:

| District | Source polygon km² | Wikidata km² | Entity |
| --- | ---: | ---: | --- |
| bang-kho-laem | 8.4313 | 10.92 | Q806446 |
| bang-rak | 3.9352 | 5.54 | Q302711 |
| bang-sue | 12.9394 | 11.50 | Q166236 |
| chom-thong | 22.2715 | 26.27 | Q1019598 |
| pom-prap-sattru-phai | 2.5226 | 1.93 | Q1019440 |
| rat-burana | 12.5415 | 15.78 | Q1019633 |
| sathon | 7.2131 | 9.33 | Q45744 |
| taling-chan | 35.6482 | 29.48 | Q1759319 |
| yan-nawa | 12.4736 | 16.66 | Q1019651 |

**Density denominator:** retained official/Wikidata `facts.area_km2`, not the
OSM polygon area. WorldPop counts use pixel-center masks from the published,
rounded district geometry (holes excluded); numerator and denominator therefore
have different geographic provenance. Displayed population/density remains DOPA
registration via Wikidata, **2020**. Polygon area is retained as an audit in the
population comparison. No silent denominator substitution was made. The notices
remain limitations; no authoritative evidence justified changing the source.

**Station simplification:** coverage is not edge-matched, so the existing
fallback independently simplifies with topology preservation at **12m** and
filters tiny parts <=5000m² (retaining the largest if all are small). All 133 raw
catchments are valid; the published station-geometry file is **byte-identical**
to main (SHA-256 `fe5329fe983fd59b072494a0fdfdea41cc76523ef79cb902bfc9e626789ad0fb`).
District geometry changes in six districts, as in the original experiment.

**Overture attribution review:** every source entry of all selected records,
including secondary entries, was inventoried before slimming. Only
CDLA-Permissive-2.0 (Meta, Microsoft, PinMeTo, DAC, Overture/Overture-signals),
Apache-2.0 (**8,356 Foursquare** entries), and CC0-1.0 (**7,417 AllThePlaces**)
appear. The manifest contains exact counts. App methodology, EN/JA/RU Bangkok
fact-source text and pipeline docs now name all three licenses/providers.
Public [notices](../../../app/public/data/bangkok/licenses/NOTICE.txt), full
Apache/CDLA license copies and the full Foursquare provider notice are retained.
The notice states the schema transformation and our filtering/aggregation.
Overture's 2024 Foursquare copyright and the currently linked 2026 provider
notice are both preserved, with retrieval context. References:
[Overture attribution](https://docs.overturemaps.org/attribution/#places),
[Places guide](https://docs.overturemaps.org/guides/places/),
[Foursquare NOTICE](https://opensource.foursquare.com/places-notice-txt/).
This completes the extract-specific three-license review, not a legal audit of
all upstream contributors or a fresh per-image Commons license audit.

## D. Data diff and scope

| Measure | Result |
| --- | --- |
| Entities | 50 districts, 133 areas, 179 rail stations / 10 lines; no ID gains/losses |
| District ratings | 12 districts; food 2, green 11; all other categories unchanged |
| Area ratings | 35 areas; green 24, sports 4, transport 2, vibe 6; other categories unchanged |
| Facts | 25 districts / 14 areas; all enrichments retained; park areas plus markets in Lat Krabang, Nong Chok and Sai Mai |
| Grid | same 39,149 inside cells, 330×257, 200m; no cell gain/loss or ID reassignment |
| Binary | `grid-4ab45661dc7b.bin` (143,624 B) -> `grid-1d6ed2ef00c3.bin` (143,925 B) |
| Changed cell planes | food 1542, nightlife 27, essentials 692, sports 760, vibe 999, green 11177, transport 609, weight 153 |
| Stable planes | crowd, district/station/area indices, station distance, all hub-minute planes; derived rent/safety unchanged |
| Metadata | transport header median remains 5 after contract fix; station default-weight p5 4.3 -> 4.4 |

The binary SHA-256 is
`1d6ed2ef00c3e72e199f3de6e896bf5ae1edb78ca3dc6da701bb5dbd0158e719`, identical
to the archived experiment. Thus its decoded grid diff is the same as that
[prior detailed report](bangkok-geofabrik-refresh-diff.md), with corrected header
summaries. Rating maxima are green +3 (Nong Khaem) / +5 (Setthabutbamphen);
all non-green rating changes are one point. Rent objects, safety, descriptions
and station names/positions remain unchanged. Talat Phlu's Thai wiki link and
three rail line path geometries update as documented in the prior report.
Build-month `data_date` becomes **2026-10**; rent observations remain **2026-09**,
rent audit **2026-10-25**, population **2020**, and safety remains editorial.

**Authorized narrow cross-city exception (city-rating-9):** normal institutions
and noise exporters update embedded Bangkok input hashes. The only Tokyo diff
is **three Bangkok input-hash provenance lines** in `station-institutions.json`,
in both `data/` and app copies. **No Tokyo count, rating, fact, station/district
value or noise value changes.** The shared noise calibration report changes only
its Bangkok station-input hash; Bangkok institution metadata updates its three
Bangkok fingerprints, with all institution counts unchanged. A regression pins
every other field to the release snapshot after excluding only those exact
hash fields. No legacy/fake fingerprint workaround was used. App build drift in
`next-env.d.ts` and sitemaps is reverted before staging.

## Validation

- Full Python pipeline/data suite: **649 passed** (`pytest scripts/`, **12.04s**).
- Bangkok suite: **141 passed** (`pytest scripts/bangkok`, **1.48s**).
- App: **24 files / 399 tests passed** (**6.79s**). An earlier run concurrently
  with pipeline/TypeScript/lint jobs hit the existing 5s exhaustive-grid timeout;
  a normal rerun passed without weakening/changing that test.
- TypeScript: `npx tsc --noEmit`, **exit 0**.
- Lint: **exit 0**, **0 errors / 18 existing warnings**.
- Production build: `npm run build`, **exit 0**, **5,045 pages**.
- Browser QA: methodology attribution inspected through the session browser;
  the public notices/licenses are served with the production app.

Python checks used a clean uv venv with CI's pytest/pydantic/requests/numpy/
shapely/rasterio dependencies plus `scripts/requirements-ingest.txt`; fetch/build
use their PEP 723 environments. No raw caches are required by the CI tests.

## Remaining limits

No old raw spatial cache exists for a controlled same-snapshot Overpass/PBF
comparison. Source/geometry changes are not proof of real-world improvement.
Wikimedia HTTP acquisition is live; exact archived payloads are required for
byte-identical replay, and thumbnail bytes remain external. Overture and the
2020 population/flood/enrichment epochs were retained, not advanced. Legacy
embassy calculation provenance remains incomplete. The nine area discrepancies
and the documented public-access assumptions remain explicit. No merge or
release approval is implied by passing tests.

## Durable archive

Exact raw inputs: `bangkok-frozen-inputs-2026-10-24.tar.gz` in
[city-rating-16](ao://sessions/city-rating/city-rating-16).
Bytes: **366,261,795**; SHA-256:
`1f90cdd3b54aeb33c1ad59c3ccd66f6548d13fced791f7c9ef06855b6ef0a4c3`. Every archived raw input was read back
and checked against the manifest. The archive is local AO storage, not a public
PBF/cache addition to git.
