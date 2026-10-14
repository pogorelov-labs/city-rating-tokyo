# Open 100 m population raster for Bangkok quietness + resident weighting (CRTKY-140)

Researched: **2026-10-13**, by the open-data research agent. Context: Bangkok
quietness is currently rated on **DOPA-registered** district density
(honesty note 5 in `research/bangkok/00-overview.md`: "Registered population
undercounts central districts"), and the 200 m resident weight is a POI proxy.
All network checks and computations below were run by me in this session;
commands and outputs are quoted. Nothing here is an implementation decision —
the owner adopts sources.

**TL;DR:** Both candidate rasters are real, open and easily downloadable.
WorldPop Thailand constrained 2020 is **one 28.9 MB country GeoTIFF** (WGS84,
3 arc-sec ≈ 100 m, CC-BY-4.0) — the whole country costs less than the repo's
existing raw cache (~50 MB). GHS-POP R2023A 2020 is a 1000 × 1000 km Mollweide
tile, **18.5 MB zipped** for tile R8_C28 (the one containing Bangkok), EU
reuse-with-acknowledgment. I downloaded both **in memory** and zonal-summed
them over the pipeline's own OSM district polygons: they agree with each other
(GHS/WorldPop district ratios 0.91–1.33) and both say the registered counts
understate central Bangkok by **~2.5–3×** — **Watthana 221–258 k de facto vs
81,623 registered (2.7–3.2×)**, while Nong Chok is only 1.14–1.26×. Simulating
the replacement in the existing crowd formula changes **20 of 50** district
quietness ratings by one point (Pathum Wan becomes the busiest, 2→1; Bang Rak
1→2; Watthana stays 2 but moves into the raw top-5). R2025A (2015–2030 with
2029) is served both as plain country GeoTIFFs via the WorldPop REST API and
via a working STAC API (`api.stac.worldpop.org`) — but it is labelled an
**alpha** release, so adopt the 2020 constrained file now and revisit.

---

## 1. What the pipeline does today (code refs)

- **District quietness** (`crowd` key): `scripts/bangkok/build.py:1093-1097` —
  `raw["crowd"] = 0.5 * ln(density) + 0.5 * ln(1 + places_per_km2)`, where
  `density` = registered population / official area
  (`facts["density"]`, `build.py:1064-1072`, population fetched from Wikidata,
  CC0 — `scripts/bangkok/fetch.py:15`, `build.py:244`; year 2020), and
  `places_per_km2` = all Overture places in the district per km².
  Percentile-normalised inverted → 1–10 (`scripts/bangkok/ratings.py:24-46`).
  Confidence "moderate ×50" (`research/bangkok/00-overview.md:57`).
- **Station-area / grid quietness**: POI-only — "every place within 400 m …
  inverted" (`build.py:1029-1031`); the overview states "no population raster
  at that scale" (`research/bangkok/00-overview.md:62-65`).
- **Resident weight** (`build.py:947-952`): a 200 m point counts
  `0.1 + 0.9 * min(1, activity / 10)` where `activity` = shops + eateries +
  clinics within 500 m (two POI sources summed); 0.1 floor for paddies/river.
  Packed as uint8 × 250 (`build.py:1520`).

## 2. Source A — WorldPop constrained 2020, 100 m (ADOPT candidate)

Record: `https://hub.worldpop.org/geodata/summary?id=49890` — "The spatial
distribution of population in 2020, Thailand", category "Constrained
Individual countries 2020 (100m resolution)". Verified via the REST API:

```
curl -sS "https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3=THA"
→ data[0]: id "49890", doi 10.5258/SOTON/WP00684,
  data_file "GIS/Population/Global_2000_2020_Constrained/2020/BSGM/THA/tha_ppp_2020_constrained.tif",
  files: ["https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/THA/tha_ppp_2020_constrained.tif"],
  license "https://hub.worldpop.org/data/licence.txt"
```

- **License:** CC-BY-4.0, read from
  `https://hub.worldpop.org/data/licence.txt` ("WorldPop datasets are licensed
  under the Creative Commons Attribution 4.0 International License"). STAC
  collection THA also reports `"license": "CC-BY-4.0"`.
- **Method** (record description): Random-Forest dasymetric disaggregation of
  2020 census/projection-based estimates, constrained to the Built-Settlement
  Growth Model (BSGM) settlement footprint; NoData = unsettled per BSGM.
- **Size / mechanics** (HEAD, 2026-10-13):
  `curl -sSI …/tha_ppp_2020_constrained.tif` → `HTTP/1.1 200`,
  `Content-Length: 28878233` (28.9 MB), `Content-Type: image/tiff`,
  `Accept-Ranges: bytes`.
  ⚠ **Range requests are advertised but ignored**: a
  `curl -H "Range: bytes=0-99"` probe returned `HTTP/1.1 200` with the full
  body (8.2 MB received before my 20 s cap). So GDAL `/vsicurl` lazy/partial
  reads will not work against `data.worldpop.org`; plan on a plain full-file
  download (which is fine at 29 MB; measured ~400 KB/s → ~70 s).
- **Raster verified by reading it** (downloaded to memory via
  `curl` + `subprocess`, opened with rasterio 1.5.2 in a
  `uv run --with rasterio` env — no files written to disk):
  `crs: EPSG:4326 | 9952 x 17816 | res ≈ 0.000833° (3 arc-sec ≈ 100 m) |
  nodata: -99999 | float32`. One file covers all of Thailand; Bangkok zonal
  stats in §4.

## 3. Source B — WorldPop "Global2" R2025A, 2015–2030 incl. 2029 (defer, alpha)

Same hub, new release. REST API (`…/rest/data/pop/G2_CN_POP_R25A_100m?iso3=THA`)
returns one record per year, ids 75653–…, DOI 10.5258/SOTON/WP00839, dated
2025-09-01, with URL pattern

```
https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/<year>/THA/v1/100m/constrained/tha_pop_<year>_CN_100m_R2025A_v1.tif
```

HEAD checks (2026-10-13): year 2020 → 120,943,989 B; 2024 → 121,237,133 B;
**2029 → 120,503,029 B**; all `HTTP/1.1 200`, `Accept-Ranges: bytes`
(same host as above, so expect the same no-Range behaviour). ~115 MiB per
country-year — 4× the 2020 file, still feasible but heavier.

**STAC is real and works** (the ticket asked): the browser front-end lives at
`https://stac.worldpop.org/`, its `config.js` points at the API
`https://api.stac.worldpop.org` — verified:

- `GET /` → Catalog "WorldPop STAC API", 3 arc-sec, WGS84, OGCAPI-features.
- `GET /collections/THA` → `license: CC-BY-4.0`, temporal 2015-01-01 →
  2030-12-31, years `[2015…2030]`, bbox `[97.34, 5.61, 105.64, 20.47]`.
- `GET /collections/THA/items/tha_pop_2029_CN_100m_R2025A_v1` → asset href =
  the same data.worldpop.org URL as the REST record; properties report
  `size: 114.92 MB`, `stats:max: 354.78` (people per 100 m cell; the 2020
  item reports max 356.04, mean 1.9 — a useful saturation ceiling, ≈35,600
  people/km²).

**Caveat that decides against adopting it now**: every R2025A record says
*"The dataset currently represents an alpha version (R2025A) product and may
change over the coming year"*. For projections to 2029 specifically this is
the right endpoint once it stabilises; for a 2020 snapshot the finished
Global1 constrained file is the safer primary.

## 4. Source C — GHS-POP R2023A, 100 m (verified; cross-check alternative)

Portal: `https://human-settlement.emergency.copernicus.eu/datasets.php` —
GHS-POP R2023A, "Mollweide; WGS84", resolutions incl. 100 m, epochs
1975–2030, 5-year steps; page-wide terms: *"© European Union, 1995-2025.
Reuse of this data is authorised with proper acknowledgment of the source."*;
DOI 10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE; citation Schiavina/Freire/
Carioli/MacManus (2023), method Pesaresi et al. (2024).

Files verified directly on the JRC server:

- Global zip `…/V1-0/GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0.zip` = **4.7G**
  (do not use); `…/V1-0/tiles/` lists **375** per-tile zips named
  `…_R<row>_C<col>.zip` (max R18, max C36 → ~1000 × 1000 km Mollweide tiles).
- **Bangkok tile = R8_C28** (computed Bangkok's Mollweide coords with the
  ESRI sphere: x = 9,882,149 m, y = 1,692,730 m; the tile's own bounds,
  read from the file, are x ∈ [8,959,000, 9,959,000], y ∈ [1,000,000,
  2,000,000] — inside):
  `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2020_GLOBE_R2023A_54009_100/V1-0/tiles/GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R8_C28.zip`
  → HEAD `HTTP/2 200`, `Content-Length: 18511929` (18.5 MB). No auth, plain
  GET. The zip contains the GeoTIFF plus `GHSL_Data_Package_2023_light.pdf`
  and an input-metadata xlsx.
- **Raster verified by reading it** (zip → memory): `crs: ESRI:54009 |
  10000 x 10000 | res: exactly (100.0, 100.0) m | nodata: -200 | float64`.
  Epochs 1975–2030 exist as separate products (I checked 2020 only).

Friction vs WorldPop: Mollweide projection needs reprojection against the
pipeline's EPSG:4326 grid, and a 4°-tile URL must be derived (the tiling doc
page `ghs_tiling.php` 404s today — I found the tile empirically from the
listing + bounds). Hence WorldPop is the lower-friction primary; GHS-POP stays
as the independent cross-check (which it just passed — §4.1).

### 4.1 Cross-check result

Both rasters, same polygons, same method (pixel-center mask, sum of float
counts), 2026-10-13:

| district | GHS-POP 2020 | WorldPop 2020 | GHS/WP | registered |
|---|---:|---:|---:|---:|
| watthana | 258,364 | 221,663 | 1.17 | 81,623 |
| nong-chok | 202,688 | 223,901 | 0.91 | 177,979 |
| khlong-toei | 213,619 | 215,644 | 0.99 | 93,193 |
| sathon | 184,470 | 180,451 | 1.02 | 75,735 |
| samphanthawong | 21,132 | 19,868 | 1.06 | 21,324 |
| pom-prap-sattru-phai | 57,331 | 53,404 | 1.07 | 41,524 |
| lat-krabang | 386,131 | 368,746 | 1.05 | 178,971 |
| bang-khun-thian | 357,274 | 343,381 | 1.04 | 186,144 |
| bang-kapi | 461,643 | 436,196 | 1.06 | 144,732 |
| bang-rak | 99,666 | 74,878 | 1.33 | 45,757 |

Two independent products (different census input handling, different dasymetric
models) land within ±10–17 % of each other on 8 of 10 districts — that mutual
agreement is what makes the de-facto numbers in §5 credible.

## 5. What replacing DOPA density gives (quantified)

Full 50-district zonal sums of `tha_ppp_2020_constrained.tif` inside the
pipeline's own OSM boundaries (`app/src/data/bangkok/geometry.json`), compared
with registered population (`app/src/data/bangkok/districts.json → facts`):

- **City total:** WorldPop 10,880,505 vs registered 5,588,222 → **1.95×**.
- **Ratio extremes:** bang-kapi 3.01, chatuchak 2.89, wang-thonglang 2.76,
  **watthana 2.72**, bang-phlat 2.69, pathum-wan 2.68, yan-nawa 2.65 … down to
  nong-chok **1.26**, bueng-kum 1.28, and samphanthawong 0.93 (the one district
  where WorldPop < registered — commercial Chinatown).
- **The asked contrast, Watthana vs Nong Chok** (registered numbers are the
  documented `facts`: 81,623 / 12.56 km² = 6,496 per km² vs 177,979 /
  236.26 km² = 753 per km²):

| | registered | WorldPop 2020 | GHS-POP 2020 |
|---|---:|---:|---:|
| Watthana | 81,623 (6,496/km²) | **221,663 (17,648/km²)** — 2.72× | 258,364 — 3.17× |
| Nong Chok | 177,979 (753/km²) | **223,901 (948/km²)** — 1.26× | 202,688 — 1.14× |

This is exactly the "center undercount" the honesty note flags: the registered
book puts Bang Rak (8,259/km²) *above* Watthana (6,496/km²); the de-facto
rasters put Watthana at ~17.6 k/km² vs Bang Rak ~13.5 k/km² — the order of the
two densest central districts flips, and Watthana's ~140 k invisible residents
(221.7 k − 81.6 k WorldPop delta; GHS says ~177 k) are 3× Nong Chok's entire
surplus. Registered-based quietness therefore overrates how residentially calm
the Sukhumvit corridor is relative to its built reality.

### 5.1 Simulated district crowd ratings (density term swapped, POI term kept)

I recovered the POI term exactly from the existing raw signals
(`data/bangkok/signals.json → districts.<slug>.raw.crowd`, inverting
`build.py:1094`), rebuilt `raw = 0.5·ln(wp_density) + 0.5·ln(1+ppk)` with
`wp_density = WorldPop_sum / facts.area_km2`, and re-ran the same
`percentile_normalize(invert=True)` (`ratings.py:24-46`; my reproduction of the
current ratings from raw values matched `signals.json` exactly — assertion
passed). Result: **20 of 50 districts move by one rating point**:

```
chatuchak        7.10 ->  7.63   5 -> 4      phasi-charoen   7.05 ->  7.41   5 -> 6
wang-thonglang   7.15 ->  7.65   5 -> 4      taling-chan     6.50 ->  6.86   8 -> 7
pathum-wan       7.80 ->  8.30   2 -> 1      lat-phrao       7.09 ->  7.43   5 -> 6
suan-luang       6.98 ->  7.44   6 -> 5      bang-kho-laem   7.15 ->  7.48   4 -> 5
lak-si           6.73 ->  7.19   7 -> 6      dusit           7.24 ->  7.52   4 -> 5
bang-na          7.00 ->  7.44   6 -> 5      khan-na-yao     6.56 ->  6.84   7 -> 8
bangkok-noi      7.43 ->  7.80   4 -> 3      nong-khaem      6.37 ->  6.62   9 -> 8
lat-krabang      5.62 ->  5.98  10 -> 9      bang-rak        7.97 ->  8.22   1 -> 2
bang-sue         7.44 ->  7.68   3 -> 4      khlong-sam-wa   5.62 ->  5.82   9 -> 10
                                             thung-khru      6.40 ->  6.55   8 -> 9
                                             bueng-kum       6.89 ->  7.01   6 -> 7
```

Headline shifts: **Pathum Wan becomes the busiest district (2→1)**, Bang Rak
drops 1→2, the mid-city donut (Chatuchak, Wang Thonglang, Suan Luang, Bang Na,
Lak Si, Lat Phrao) gets systematically busier (quieter ratings drop by 1), and
the outer quiet tier stays quiet (Nong Chok 10→10; bottom-5 order reshuffles
slightly). Watthana keeps rating 2 but its raw signal jumps 7.73 → 8.23,
moving from outside the top-5 to the 5th-busiest — i.e. the current scores
understate, not invert, the corridor. Interpretation: this is a *calibration*
change, not a redefinition — 30 of 50 districts don't move at all.

## 6. Fitting the raster into the 200 m grid (resident weighting + grid quietness)

The raster is a natural drop-in for the three places a population field can
enter; all are owner decisions, listed smallest-diff first:

1. **District quietness only** (minimal): keep `build.py:1094` formula, replace
   `facts["density"]` in the signal with the zonal WorldPop sum / official
   area. `facts.population` (Wikidata, displayed on the page) stays as-is.
   Effect = §5.1. Needs one per-district zonal sum at build time.
2. **Grid + station quietness** (closes a known gap): today those levels use
   Overture-POI density within 400 m only (`build.py:1031`; overview
   `00-overview.md:62-65` says "no population raster at that scale"). Sample
   the 100 m raster at each 200 m point (mean of the 4 underlying 100 m cells;
   `build.py` already does raster-style sampling for parks) →
   `pt_crowd_new = 0.5·L(pop_pt) + 0.5·pt_crowd`, mirroring the district
   blend. Makes the grid quietness resident-based instead of shop-based.
3. **Resident weight** (the `weight` plane, `build.py:947-952,1520`): replace
   or blend the POI proxy `0.1 + 0.9·min(1, activity/10)` with a population
   term, e.g. `0.1 + 0.9·min(1, pop_pt / POP_REF)`. Observed range for
   calibration: Thailand's densest 100 m cell ≈ 356 people (STAC stats),
   Watthana's mean ≈ 176 per 100 m cell ⇒ a 200 m cell in the densest blocks
   carries ~200–400 people; `POP_REF ≈ 150–250 people per 200 m cell` would
   saturate the cores like `activity/10` does today — that number is a
   suggestion to calibrate, not a decision. Keep the 0.1 floor for zero-pop
   cells (river/parks) — identical semantics to today. Packing is unchanged
   (uint8 × 250).

**Plumbing**: no rasterio at build time is needed if `fetch.py` pre-cuts the
Bangkok window at fetch time (bbox ≈ 50 × 30 km → ~500 × 300 100 m cells,
~1 MB as float32 `.npz`) into the gitignored `data/bangkok/raw/` cache; the
29 MB country file downloads in one `curl` with no auth (measured ~70 s) and
the repo cache is already ~50 MB (`00-overview.md:25`). `build.py` then reads
the npz with numpy only. Range reads (partial HTTP) are NOT usable on
data.worldpop.org (§2), so the fetch is whole-file — that's fine at this size.

**License cost**: WorldPop CC-BY-4.0 → add an attribution line (Bondarenko
et al. 2020, DOI 10.5258/SOTON/WP00684) to /methodology#bangkok and the
sources table in `00-overview.md` (GHS-POP would need the EU
acknowledgment form instead).

## 7. Honest caveats

- Both products are **modelled dasymetric estimates**, not counts. The 2.7×
  Watthana delta is "de-facto model vs household registration", corroborated by
  two independent models agreeing within ~±10–17 %; it is not a census
  measurement. My zonal sums use the repo's simplified OSM polygons and
  pixel-center masking (same boundaries the ratings already use).
- Epoch is **2020** on both sides of the comparison (registered `population_year`
  is also 2020), but the site is 2026 — six years of condo build-out since.
  R2025A has 2025/2026/…/2030 layers for when it leaves alpha (§3).
- Samphanthawong (WorldPop < registered, ratio 0.93) shows the models can sit
  below registration in commercial districts — percentile ratings are robust
  to that; absolute counts are not.
- `stats` quoted from STAC (max ≈ 356 people/cell) are the R2025A files', not
  the Global1 file's (I did not compute Global1's national total or its cell
  max — not run).
- Download volume if adopted: +28.9 MB to `data/bangkok/raw/` (gitignored),
  ~1 MB derived npz; nothing new committed to the app payload (the grid `.bin`
  weight plane already exists).

## 8. Recommendation

**Adopt** WorldPop Thailand constrained 2020 (`tha_ppp_2020_constrained.tif`,
CC-BY-4.0) as the density input for district quietness, and — if the owner
wants the bigger win — as the population plane for grid/station quietness and
the resident weight, behind the integration options in §6. **Defer** R2025A
(alpha, ~115 MiB/year) until it stabilises; **keep** GHS-POP R2023A tile
R8_C28 as the documented cross-check (it already passed one).

## 9. Open questions for the owner

1. Replace the DOPA term outright, or blend registered + de-facto (the §5.1
   simulation is replace; a 50/50 blend would soften the 20 rating changes)?
2. Does `facts.population` (displayed "registered" number) stay Wikidata
   while only the signal changes — or does the fact card gain a de-facto
   figure too?
3. Grid/station quietness and the resident weight: both, or one, or neither
   (§6 items 2–3), and what `POP_REF`?
4. Attribution text for CC-BY-4.0 on /methodology and in `00-overview.md`.
5. Accept `fetch.py` gaining a 29 MB cached download (+ optional npz pre-cut)
   — and is rasterio acceptable as a build dependency if pre-cutting is
   rejected?
6. Revisit R2025A (2025 epoch + projections) when it stops being alpha.

## Appendix — exact commands run this session

```
curl -sS "https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3=THA"
curl -sS "https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_100m?iso3=THA"
curl -sSI "https://data.worldpop.org/.../tha_ppp_2020_constrained.tif"          # 200, 28878233 B
curl -sS -r 0-99 -o /dev/null -w "%{http_code} %{size_download}" <same url>     # 200 + full body (no range)
curl -sS "https://hub.worldpop.org/data/licence.txt"                            # CC-BY-4.0
curl -sS "https://api.stac.worldpop.org/collections/THA"
curl -sS "https://api.stac.worldpop.org/collections/THA/items/tha_pop_2029_CN_100m_R2025A_v1"
curl -sSI ".../GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R8_C28.zip"            # 200, 18511929 B
uv run --with rasterio --with numpy --with shapely python -  (3 runs:
  1) WorldPop in-memory zonal sums, 50 districts vs registered
  2) crowd-rating simulation (reproduced old ratings exactly, then swapped density term)
  3) GHS-POP R8_C28 zip in-memory zonal sums for 10 districts)
```

No files were created on disk during research except this note; both rasters
were held and processed in memory only.
