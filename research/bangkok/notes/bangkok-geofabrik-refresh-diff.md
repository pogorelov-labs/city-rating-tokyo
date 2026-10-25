# Bangkok Geofabrik refresh diff

**Acquisition and the full build succeeded. The fetch implementation is ready for code review; these regenerated data are not ready to publish.** No regenerated Bangkok data, Tokyo files, runtime code or scoring changes are included in the code PR. The refreshed outputs were archived, verified, then restored to main before committing code/docs/tests. No merge was performed.

Baseline: `3a8ac5212f0af76e9a42d648063a450486c0d324`. Written 2026-10-26T01:20:22.191295+03:00. Worker: [city-rating-14](ao://sessions/city-rating/city-rating-14); feature branch `ao/bangkok-geofabrik/fetch`.

## Result and decision boundary

All 17 acquisition outputs and both authorized caches were available. The 12 OSM outputs came from one Thailand PBF; no OSM input used Overpass. Full `uv run scripts/bangkok/build.py` exited **0** in **27.098 s wall time** (the builder reported **6.7 s**). A repeat exited 0 in **5.867 s** and reproduced every current Bangkok file byte for byte.

| Measure | Baseline → refreshed | What changed |
| --- | --- | --- |
| Districts | 50 → 50 | 50 objects differ; 12 have rating changes; 30 have fact changes |
| Station areas | 133 → 133 | 133 objects differ; 35 have rating changes; 14 have fact changes |
| Rail stations / lines | 179 / 10 → 179 / 10 | 0 station records; 3 line-path records |
| 200 m cells | 39,149 → 39,149 | Same 330 × 257 layout; no gained/lost cells |
| Tracked Bangkok files | 67 → 67 | 8 baseline paths differ (7 JSONs + removed old binary); 59 unchanged; 1 replacement binary added |
| Names / descriptions / rent / safety | Unchanged | All district and area names, district descriptions, rent objects, rent/safety ratings/confidence/sources retained |
| Code validation | 118 passed | After restoring all generated data; includes 35 new offline tests |
| Refreshed-data validation | 105 passed, 10 failed | 8 historical population checks, 1 normalization golden, 1 encoded-weight median check |

Data publication needs separate work: preserve/recompute tourism, Michelin and embassy enrichments; reconcile the transport median with the encoded weights; handle historical population fixtures and normalization goldens deliberately; review green outliers and source attribution. This report does not approve a refresh, and the code PR does not ship it.

## Source and extraction provenance

| Property | Observed value |
| --- | --- |
| Requested URL | https://download.geofabrik.de/asia/thailand-latest.osm.pbf |
| Resolved URL | https://download.geofabrik.de/asia/thailand-261024.osm.pbf |
| HTTP Last-Modified | Sat, 24 Oct 2026 23:00:29 GMT |
| OSM replication timestamp | 2026-10-24T20:20:51Z |
| Retrieved UTC | 2026-10-25T22:01:08.164634+00:00 |
| Bytes | 329280467 |
| SHA-256 | e8373240cf0be47cc641f2c8627e674064d8c47f4ff2a11f6a33fcbfc9a50949 |
| License | ODbL 1.0, © OpenStreetMap contributors; distribution by Geofabrik |
| BBox south / west / north / east | [13.47, 100.3, 13.98, 100.96] |
| Extraction | Exit 0; 273.034 s wall; 271.8 s reported by script; peak child RSS 846,479,360 bytes (~807 MiB) |

The [Geofabrik Thailand page](https://download.geofabrik.de/asia/thailand.html), [extract technical notes](https://download.geofabrik.de/technical.html), and [OSM attribution/license](https://www.openstreetmap.org/copyright) are the primary source references. The PBF, sidecar and all raw caches remain gitignored. A fresh download was made with a stdlib urllib streaming wrapper; the new script then verified its recorded byte count/hash before extracting. The implemented downloader uses the same public URL, redirect handling, User-Agent, streaming and length checks. Reuse verifies provenance; changing the requested URL requires an explicit refresh or local-file selection.

Four passes copied relation metadata, selected Bangkok nodes/ways with a libosmium location index, read the selected ways’ complete node references, then resolved the required nodes. The bbox pass selected **443 relations**; completion used **2,173 member ways** and **41,450 nodes**. Geometry outside the bbox was retained. All 20 configured route IDs exist. Bangkok’s province polygon selected 50 level-6 districts with unique Wikidata IDs; neighboring level-6 relations were excluded by an interior-point test. Unlike Overpass this does not depend on a separately updated area index.

`osm_filters.py` is shared by both fetchers. A direct comparison with `git show 3a8ac52:scripts/bangkok/fetch.py` confirmed that all six POI bodies and all six other OSM queries remain byte-identical. POI/station nodes provide lat/lon; ways and POI relations provide the [Overpass bounding-box center](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Print_(out)), not a centroid. Direct node/way members contribute; nested relation members remain references and do not contribute to centers. Green ways have geometry; relations preserve direct node coordinates and ordered complete way-member geometry, including roles. The builder itself handles direct way members only. Missing members, route IDs or district coverage fail before cache writes. `province.json` is emitted but is not read by build.py.

| OSM output | Elements | Nodes | Ways | Relations |
| --- | --- | --- | --- | --- |
| boundaries | 50 | 0 | 0 | 50 |
| green | 6963 | 102 | 6628 | 233 |
| pois_culture | 4664 | 2091 | 2526 | 47 |
| pois_essentials | 7521 | 4661 | 2805 | 55 |
| pois_food | 9261 | 7433 | 1822 | 6 |
| pois_nightlife | 1280 | 1070 | 207 | 3 |
| pois_sports | 1456 | 262 | 1189 | 5 |
| pois_transit_other | 5172 | 5170 | 2 | 0 |
| province | 1 | 0 | 0 | 1 |
| rail_routes | 20 | 0 | 0 | 20 |
| rail_stations | 449 | 394 | 55 | 0 |
| rail_stops | 311 | 311 | 0 | 0 |

Validation found zero duplicate type/ID pairs, zero shared-selector mismatches, zero missing POI/station point-or-center values, and complete geometry for every direct way member of green/boundary/province/route relations. Every OSM JSON records the same replication timestamp and PBF hash. The station API tasks were run only after `rail_stations` existed; all required raw files were checked nonempty before building.

### Food cross-check and category spot-checks

The prior feasibility run fetched **9,264** food elements from Overpass at OSM base `2026-10-25T20:57:47Z`; this PBF has **9,261** at `2026-10-24T20:20:51Z`: **−3 (-0.0324%)**. This is a total-count cross-check across snapshots about 24 h 37 m apart. The prior raw cache was removed, and the prior report has no element-ID or food-subcategory breakdown, so the three differing elements and per-tag historical deltas cannot be identified. No new Overpass query was used.

| Food primary tag (amenity, else shop) | Current count |
| --- | --- |
| restaurant | 5376 |
| cafe | 2553 |
| fast_food | 787 |
| bakery | 185 |
| food_court | 170 |
| ice_cream | 119 |
| coffee | 39 |
| pastry | 32 |

Food contains 7,433 nodes, 1,822 ways and 6 relations; every non-node has a full-bounds center. Synthetic tests explicitly check an outside-bbox center for a way with an inside vertex, repeated member roles, direct node coordinates, nested relation references, and missing geometry failures. The extraction preserves exact tag matching (including key-existence `historic`), way-only pedestrian selectors and node-only bus stops; access restrictions stay with the existing builder.

- `pois_nightlife` spot-check: nwr:amenity=bar: 670; nwr:amenity=pub: 101; nwr:amenity=nightclub: 93; nwr:amenity=karaoke_box: 9; nwr:tourism=hostel: 401.
- `pois_essentials` spot-check: nwr:shop=convenience: 2584; nwr:shop=supermarket: 488; nwr:shop=laundry: 301; nwr:shop=mall: 291; nwr:amenity=school: 1021; nwr:amenity=bank: 778; nwr:amenity=marketplace: 452; nwr:amenity=pharmacy: 372.
- `pois_sports` spot-check: nwr:leisure=swimming_pool: 894; nwr:leisure=sports_centre: 276; nwr:leisure=fitness_centre: 174; nwr:leisure=fitness_station: 67.
- `pois_culture` spot-check: nwr:amenity=place_of_worship: 1251; nwr:amenity=library: 97; nwr:amenity=theatre: 61; nwr:amenity=cinema: 37; nwr:tourism=attraction: 356; nwr:tourism=museum: 152; nwr:tourism=gallery: 48; nwr:shop=books: 91; nwr:shop=antiques: 25; nwr:shop=art: 22; nwr:shop=musical_instrument: 18; nwr:historic=wayside_shrine: 1067; nwr:historic=tomb: 503; nwr:historic=monument: 81; nwr:historic=memorial: 80; way:highway=pedestrian: 518.
- `pois_transit_other` spot-check: nwr:amenity=ferry_terminal: 194; node:highway=bus_stop: 4978.
- `green` spot-check: nwr:leisure=garden: 3431; nwr:leisure=park: 773; nwr:leisure=nature_reserve: 1; nwr:landuse=forest: 627; nwr:landuse=recreation_ground: 235; nwr:landuse=village_green: 3; nwr:natural=wood: 1901.
- `rail_stations` spot-check: node:railway=station: 214; node:public_transport=station: 394; way:public_transport=station: 55.

These spot-checks describe current matches; selectors can overlap and are not additive totals. Historical counts for those seven categories were not available in the prior Overpass report. Relative to committed main, the non-overlapping district OSM counts used for source-confidence signals change as follows (these are not the padded raw-cache totals):

| Signal | Old district total | New district total | Delta |
| --- | --- | --- | --- |
| culture | 1511 | 1521 | 10 |
| essentials | 6960 | 7019 | 59 |
| food | 8043 | 8190 | 147 |
| nightlife | 834 | 834 | 0 |
| sports | 399 | 404 | 5 |

### Other inputs and dates

The existing fetch.py API tasks completed without modification: district Wikidata 50 entities, district Commons 50 pages with imageinfo; station Wikidata 232 entities, station Commons 215 pages with imageinfo and no missing page records. The four tasks took 29.174 s. WD/Commons were fetched on `2026-10-25T22:08:34Z`–`22:09:00Z`; exact entity revision IDs/modification dates are not requested by the existing API path, so retrieval is not a fact observation date.

Overture acquisition took 26.006 s wall (23 s reported), using pinned `2026-09-23.1`, confidence ≥0.6, open/null operating status, and the existing bbox-minimum filters. The extract has **309,704 distinct IDs / rows**, confidence 0.6000032424926758–1.0, 13,909 null basic categories (4.49%), 14,391 null hierarchies (4.65%), and coordinates lon 100.30001068115234–100.96000671386719 / lat 13.471654891967773–13.979995727539062. Its SHA-256 is byte-identical to the prior feasibility extract; the release was not advanced.

| First source | License in extract | Rows |
| --- | --- | --- |
| meta | CDLA-Permissive-2.0 | 291546 |
| Foursquare | Apache-2.0 | 8356 |
| AllThePlaces | CC0-1.0 | 7417 |
| Microsoft | CDLA-Permissive-2.0 | 2302 |
| PinMeTo | CDLA-Permissive-2.0 | 65 |
| DAC | CDLA-Permissive-2.0 | 18 |

The existing application attribution mentions CDLA-Permissive-2.0 while this extract also contains Apache-2.0 and CC0-1.0 rows. That pre-existing limitation needs review before a later data publication. See [Overture Places](https://docs.overturemaps.org/guides/places/) and [attribution guidance](https://docs.overturemaps.org/attribution/). No attribution UI/runtime behavior was changed here.

The authorized WorldPop cache was copied from the city-rating-4 AO worktree and the flood ZIP from the human checkout. Exact hashes below match the committed pinned manifests. WorldPop remains the **2020** model (10,887,568 modelled people across the current district masks), DOI `10.5258/SOTON/WP00684`, CC BY 4.0. Flood remains the retained CC BY 4.0 ThaiFloodRisk v1.0.0 bundle (2021–2026 reported episodes and 2011 flood shares), DOI `10.5281/zenodo.23260465`; the full builder reads committed `flood.json`, not the ZIP. Neither source was advanced. The source contract and production date are recorded in committed population-source.json and the prior feasibility report.

All 50 district and 133 station-area `data_date` values become `2026-10` from `2026-09` because build.py stamps the build month. District rent observations remain **2026-09**, their audit and station overrides retain **2026-10-25**, safety remains editorial, displayed Wikidata population facts remain **2020**, and descriptions are retained. This monthly stamp must not be presented as refreshed observations for those categories. The prior stale July Overpass province payload is absent; every OSM output here shares the October 24 PBF date.

## Semantic output comparison

Districts are joined by `slug`, station areas by `id`, geometries by object key, rail items by `id`. All IDs and entity counts are retained. JSON equality ignores formatting for semantic comparisons; SHA-256 compares exact bytes. Unequal-length arrays are recorded as one recursive change record, while matching-length arrays recurse by index. Git’s very large line counts for districts/stations mostly reflect indent/format differences between the full builder and prior output writers; semantic counts below are the useful measure.

| Rating | Districts changed / 50 | Max absolute step | Areas changed / 133 | Max absolute step |
| --- | --- | --- | --- | --- |
| crowd | 0 | 0 | 0 | 0 |
| daily_essentials | 0 | 0 | 0 | 0 |
| food | 2 | 1 | 0 | 0 |
| green | 11 | 3 | 24 | 5 |
| gym_sports | 0 | 0 | 4 | 1 |
| nightlife | 0 | 0 | 0 | 0 |
| rent | 0 | 0 | 0 | 0 |
| safety | 0 | 0 | 0 | 0 |
| transport | 0 | 0 | 2 | 1 |
| vibe | 0 | 0 | 6 | 1 |

### Confidence, sources and facts

Two districts gain one source/confidence level: Thawi Watthana food and Nong Chok daily essentials move moderate → strong and `[overture]` → `[overture, osm]`. Victory Monument station area changes sports moderate → strong with OSM added, while vibe moves strong → moderate with OSM removed. Other confidence/source entries—including rent and safety—are unchanged. There are no new scoring formulas.

| Fact | Districts changed | Areas changed | Largest changes / removals |
| --- | --- | --- | --- |
| area_km2 | 0 | 0 | — |
| cafes | 0 | 0 | — |
| convenience | 0 | 0 | — |
| culture | 0 | 0 | — |
| density | 0 | 0 | — |
| embassies_800m | 5 | 0 | bang-rak: 3 → <MISSING>; khlong-toei: 1 → <MISSING>; pathum-wan: 9 → <MISSING> |
| essentials | 0 | 0 | — |
| food | 0 | 0 | — |
| markets | 3 | 0 | lat-krabang: 17 → 21; nong-chok: 3 → 5; sai-mai: 12 → 13 |
| michelin_bib | 9 | 0 | bang-kapi: 0 → <MISSING>; bang-rak: 3 → <MISSING>; khlong-toei: 2 → <MISSING> |
| michelin_stars | 9 | 0 | bang-kapi: 1 → <MISSING>; bang-rak: 3 → <MISSING>; khlong-toei: 0 → <MISSING> |
| nightlife | 0 | 0 | — |
| park_ha | 25 | 14 | min-buri: 1.7 → 10.4; lat-krabang: 39.1 → 44.9; don-mueang: 25.9 → 31.3 |
| park_share | 17 | 0 | phra-nakhon: 6.7 → 7.2; ratchathewi: 2.1 → 2.5; bangkok-noi: 0.6 → 0.8 |
| piers | 0 | 0 | — |
| population | 0 | 0 | — |
| population_year | 0 | 0 | — |
| sports | 0 | 0 | — |
| temples | 0 | 0 | — |

Other facts—including food, nightlife, convenience, essentials, sports, culture, temples, piers, district area, displayed population/year and density—are unchanged. Market counts increase Lat Krabang 17→21, Nong Chok 3→5 and Sai Mai 12→13. Park area changes in 25 districts and 14 station areas. Nong Chok park hectares decrease 25.1→19.9 despite increased markets and stronger essentials coverage.

**Enrichment regressions:** all 133 station areas lose `hotels_800m`, `attractions_800m`, and `tourist_badge`. The committed dataset has nonzero hotels in 99 areas, nonzero attractions in 66, and 19 true badges; Nana’s 197 hotels and Asok’s 156 are examples of information that disappears. District facts also lose `michelin_stars` and `michelin_bib` in 9 districts each (summed stored values 8 and 12), plus `embassies_800m` in 5 districts (summed stored values 16). These fields are omitted by the existing full builder, not zero observations from Geofabrik. They were not recomputed or preserved with a scraper in this task. Other separate entertainment/enrichment files remain unchanged.

### Largest rating and composite shifts

**Districts.** Composite values here are unrounded default-weighted means of the exported integer ratings; UI display/anchors may round to one decimal. Ranks use average positions for ties. 11 entities change tied rank, including entities whose own score is unchanged.

| ID | Composite before → after | Delta | Tied rank before → after |
| --- | --- | --- | --- |
| nong-khaem | 4.28 → 4.52 | +0.24 | 45.0 → 44.0 |
| rat-burana | 5.26 → 5.06 | -0.20 | 34.0 → 37.0 |
| thon-buri | 7.28 → 7.44 | +0.16 | 13.0 → 11.0 |
| don-mueang | 5.20 → 5.32 | +0.12 | 35.5 → 34.0 |
| bangkok-noi | 7.18 → 7.26 | +0.08 | 14.0 → 14.0 |
| khlong-sam-wa | 3.78 → 3.70 | -0.08 | 49.0 → 49.0 |
| lat-phrao | 6.02 → 5.94 | -0.08 | 27.0 → 27.0 |
| phra-khanong | 5.58 → 5.66 | +0.08 | 32.0 → 32.0 |
| prawet | 5.04 → 4.96 | -0.08 | 38.5 → 38.5 |
| sai-mai | 5.04 → 4.96 | -0.08 | 38.5 → 38.5 |

**Station areas.** Composite values here are unrounded default-weighted means of the exported integer ratings; UI display/anchors may round to one decimal. Ranks use average positions for ties. 93 entities change tied rank, including entities whose own score is unchanged.

| ID | Composite before → after | Delta | Tied rank before → after |
| --- | --- | --- | --- |
| setthabutbamphen | 4.16 → 4.56 | +0.40 | 128.5 → 120.0 |
| bang-khun-non | 5.58 → 5.84 | +0.26 | 78.5 → 72.0 |
| phasi-charoen | 5.68 → 5.50 | -0.18 | 76.0 → 84.5 |
| bang-chan | 3.90 → 4.06 | +0.16 | 131.0 → 131.0 |
| punnawithi | 5.22 → 5.38 | +0.16 | 95.5 → 89.0 |
| ban-thap-chang | 3.76 → 3.68 | -0.08 | 132.0 → 133.0 |
| bang-son | 5.68 → 5.60 | -0.08 | 76.0 → 77.0 |
| ekkamai | 6.02 → 6.10 | +0.08 | 65.0 → 60.0 |
| fai-chai | 5.40 → 5.48 | +0.08 | 88.0 → 86.5 |
| huai-khwang | 6.34 → 6.26 | -0.08 | 55.0 → 56.0 |

The biggest green jump is Setthabutbamphen 2→7, with park hectares 0.0→6.4. In the current PBF, [Bueng Krathiam Park relation 21083246](https://www.openstreetmap.org/relation/21083246) is a valid park multipolygon of 7.4385 ha about 105 m from that station. This is a plausible contributor to the current catchment signal; without old raw inputs it does not prove when or how the park entered the data. Nong Khaem green 2→5 and Thon Buri 2→4 also warrant review before adopting a refresh. The changed green rankings should be assessed as source/geometry evidence, not assumed improvements in real-world access.

All district EN/TH/JA/RU names and all area EN/TH/JA names are unchanged. Descriptions, aliases, image records and image attribution are unchanged. Talat Phlu’s Thai Wikipedia link changes to the BTS-disambiguated article. One district label latitude changes (Wang Thonglang). Nong Chok’s aggregated Siam commute changes 101→100 min; all encoded per-cell hub-minute values stay identical. Kan Kheha’s district blend rounds 0.761/0.239→0.762/0.238; all rent objects, including the 10 researched overrides and their provenance, remain exactly equal.

District geometry changes for Bang Kapi, Bang Khae, Huai Khwang, Nong Khaem, Thawi Watthana and Wang Thonglang (6/50). Station-area geometry is byte-identical for all 133 areas. All 179 rail station records and line sequences stay identical. Paths change only for BTS Sukhumvit, BTS Silom and ARL; no line or station was added/removed. BTS Sukhumvit’s simplified geometry changes from three to two path parts; route geometry is retained completely rather than clipped to the Bangkok bbox.

## Grid binary and header

| Property | Before | After |
| --- | --- | --- |
| Content-addressed file | /data/bangkok/grid-4ab45661dc7b.bin | /data/bangkok/grid-1d6ed2ef00c3.bin |
| Packed bytes | 143624 | 143925 |
| Packed SHA-256 | 4ab45661dc7ba331f84abd1cbd1d564cf09760aca62b47e71520193a2705cd8e | 1d6ed2ef00c3e72e199f3de6e896bf5ae1edb78ca3dc6da701bb5dbd0158e719 |
| Decompressed bytes | 1526580 | 1526580 |
| Decompressed SHA-256 | 88d7cb3953cccf4eda35dd02594a20017cefc31c84baae5abf440d8603e73a95 | 7ecb664853ad885d3016ac6e4d30bc143108bde106b22ac043e9e6e4f3482a23 |
| Transport median (header/meta) | 5 | 6 |
| data_date | 2026-09 | 2026-10 |

Version 1, 330 × 257, 200 m, 18 fields and bounds west 100.3278772 / east 100.9382547 / south 13.4907286 / north 13.9555757 are unchanged. District/station/area index lists, scales, encoding and rent policy are unchanged. All 39,149 inside cells align exactly; no cells are gained/lost. Gzip is decoded, then each row’s uint8 deltas are cumulatively summed modulo 256 before comparison. Semantic ID comparisons also confirm zero district/station/area reassignment. The replacement binary’s hash matches the header filename; both are archived together.

| Plane | Changed inside cells / 39,149 | Percent | Maximum absolute encoded delta |
| --- | --- | --- | --- |
| food | 1542 | 3.939% | 2 |
| nightlife | 27 | 0.069% | 1 |
| daily_essentials | 692 | 1.768% | 2 |
| gym_sports | 760 | 1.941% | 2 |
| vibe | 999 | 2.552% | 2 |
| green | 11177 | 28.550% | 8 |
| transport | 609 | 1.556% | 2 |
| crowd | 0 | 0.000% | 0 |
| district | 0 | 0.000% | 0 |
| weight | 153 | 0.391% | 90 |
| hub_siam | 0 | 0.000% | 0 |
| hub_asok | 0 | 0.000% | 0 |
| hub_silom | 0 | 0.000% | 0 |
| hub_rama9 | 0 | 0.000% | 0 |
| hub_mochit | 0 | 0.000% | 0 |
| station | 0 | 0.000% | 0 |
| station_dist | 0 | 0.000% | 0 |
| area | 0 | 0.000% | 0 |
| derived_rent | 0 | 0.000% | 0 |
| derived_safety | 0 | 0.000% | 0 |

The final two rows are rent/safety reconstructed through district indices; they are not additional binary planes. Green differs in 11,177 cells (28.550%); its largest increase is 1→9 near 13.8099718, 100.7153744 in Min Buri / Setthabutbamphen. Resident weight changes in 153 cells, with the largest encoded change +90 (= +0.36 at scale 250) around Nong Chok, e.g. 13.8262505, 100.8633447. Food/essentials/sports/vibe/transport have maximum 2-point changes, while nightlife changes by at most 1. Nearest station, station distance, catchment, district and every hub-minute field are unchanged. Source-weight changes can alter relative percentiles even where rail positions and commute observations are identical.

**Median inconsistency confirmed with a dry-run profile of the existing builder:** transport’s full-precision weighted median is 6, but its published-weight median is 5. Exact total weight is 28,154.78; weight in cells rated ≤5 is 14,076.79 (**49.9978689%**). Quantizing `round(weight × 250) / 250` produces total 28,159.18 and ≤5 weight 14,081.056 (**50.0052061%**), crossing the median threshold. Maximum rounding error per cell is 0.002. This is an encoding/metadata contract exposed by the new inputs, not evidence of a different normalization formula. It fails `test_grid_medians_are_resident_weighted`; no scoring or encoding fix was folded into this fetch PR.

Other metadata changes: district source agreement food 0.923→0.926, essentials 0.920→0.918, sports 0.765→0.756; nightlife 0.902 and vibe 0.930 unchanged. Station default p5 anchor changes 4.3→4.4; all other district/station/grid anchors and medians are unchanged, aside from grid transport 5→6. All counts and rent-audit metadata are retained.

## Warnings, tests and limits

The build printed the same nine polygon-versus-Wikidata area notices as the feasibility run. Polygon membership and population masks use spatial geometry, while official/Wikidata area remains the district density denominator. No scoring correction was made.

| District | Polygon km² (printed) | Wikidata km² (printed) |
| --- | --- | --- |
| bang-kho-laem | 8.4 | 10.9 |
| bang-rak | 3.9 | 5.5 |
| bang-sue | 12.9 | 11.5 |
| chom-thong | 22.3 | 26.3 |
| pom-prap-sattru-phai | 2.5 | 1.9 |
| rat-burana | 12.5 | 15.8 |
| sathon | 7.2 | 9.3 |
| taling-chan | 35.6 | 29.5 |
| yan-nawa | 12.5 | 16.7 |

Station-area `coverage_simplify` reported “coverage not edge-matched” and used independent polygon simplification. The resulting 133 station geometries still match main exactly. All in-Bangkok stations have Japanese names. No missing input was fabricated or skipped. Sampled free disk was approximately 12–15 GiB; disk did not block the run.

Against refreshed outputs the combined Bangkok/normalization run returned **105 passed, 10 failed in 23.27 s**:

- `test_grid_medians_are_resident_weighted`: transport 6 in header versus decoded weighted median 5, quantified above.
- `test_committed_population_snapshot_and_scope`: historical crowd raw 6.5281 versus refreshed rounded 6.5280; crowd ratings and the crowd grid plane remain unchanged.
- `test_main_original_adoption_and_idempotent_replay` and six parameterizations of `test_main_rejects_incompatible_snapshots_without_writes`: the historical replay rejects changed district geometry before its expected “Incompatible” guard. The replay contract must stay pinned to an immutable adoption fixture.
- `test_bangkok_committed_aggregate_golden`: new aggregates differ from the preserved normalization golden. A later data PR must review a new current baseline separately, rather than overwrite historical signatures to make checks green.

After archiving and restoring generated outputs, **118 tests passed in 1.13 s** across `scripts/bangkok` and `scripts/test_normalization.py`. The specifically requested tests also run individually: 35 focused extractor tests, 41 Bangkok contract tests and 15 normalization tests. The new tests are pure offline tests; pyosmium and PBF downloads are not added to CI dependencies. Existing CI discovers the focused test in the Bangkok suite.

The old raw build cache is unavailable. This is an end-to-end comparison with committed main, not a controlled same-snapshot Overpass-versus-Geofabrik numerical experiment. Boundary edits, later OSM tags, full geometry assembly, retained independent inputs and previously omitted enrichment composition can all affect the result. The same-input repeat proves determinism for these inputs/environment only. WD/Commons are not revision-pinned; Python ranges are not a complete lock. App lint, Vitest, TypeScript and production build were not run locally because runtime/generated app data are unchanged in the proposed PR; provider CI checks the code PR against committed data. The raw PBF/cache is local and subject to worktree lifecycle; the durable archive contains the exact refreshed outputs, structured comparisons and source hashes, not the 329 MB PBF or raw API payloads.

## Reproduction commands

```sh
git fetch origin
git rev-parse HEAD origin/main  # both 3a8ac5212f0af76e9a42d648063a450486c0d324
git switch -c ao/bangkok-geofabrik/fetch
# Initial fresh download: Python urllib.request streamed the requested URL to
# data/bangkok/raw/thailand.osm.pbf, recording redirect, headers, length, SHA-256.
uv run scripts/bangkok/fetch-geofabrik.py
uv run scripts/bangkok/fetch.py --only overture_places
uv run scripts/bangkok/fetch.py --only wikidata commons station_wikidata station_commons
# shutil.copy2 copied these authorized pinned caches into data/bangkok/raw/:
# city-rating-4/data/bangkok/raw/tha_ppp_2020_constrained.tif
# human checkout data/bangkok/raw/thaifloodrisk.zip
uv run scripts/bangkok/build.py
# Repeated once, hash-checking all 67 outputs for determinism:
uv run scripts/bangkok/build.py
git status --short
git diff --stat 3a8ac52 -- app/src/data/bangkok app/public/data/bangkok data/bangkok
git diff --numstat 3a8ac52 -- app/src/data/bangkok app/public/data/bangkok data/bangkok
git diff --name-status 3a8ac52 -- app/src/data/bangkok app/public/data/bangkok data/bangkok
uv run --with pytest --with pydantic --with requests --with 'numpy>=2' --with 'shapely>=2.1' --with 'rasterio>=1.4,<2' python -m pytest scripts/bangkok scripts/test_normalization.py -q --tb=short
# Full comparison used git-show baseline bytes, semantic ID joins and
# cumulative uint8 grid decoding. A profiled --dry-run diagnosed the median.
# Archive verified against every refreshed-file hash, then:
git restore --source=3a8ac52 -- app/src/data/bangkok app/public/data/bangkok data/bangkok
# Removed only the archived untracked replacement grid binary.
uv run --with pytest python -m pytest scripts/bangkok/test_fetch_geofabrik.py -q
uv run --with pytest python -m pytest scripts/bangkok/test_bangkok.py -q
uv run --with pytest --with pydantic python -m pytest scripts/test_normalization.py -q
# Re-ran the combined 118-test suite after restoration.
git diff --exit-code 3a8ac52 -- app/src/data/bangkok app/public/data/bangkok data/bangkok
git diff --check
```

The extraction and metadata/Overture commands were timed with Python subprocess wrappers; only independent Overture acquisition overlapped extraction. The metadata tasks ran in dependency order. The ordinary `fetch.py` without `--only` was never invoked in this worker. A fresh reusable acquisition can simply start with `uv run scripts/bangkok/fetch-geofabrik.py`; its downloader now performs the initial download itself.

Environment: macOS arm64, CPython 3.13.12, uv 0.11.21, Git 2.49.0. Resolved script dependencies: pyosmium/osmium 4.3.2, Shapely 2.2.0, NumPy 2.5.4, rasterio 1.5.2, DuckDB 2.0.0, requests 2.34.2. Fetch-only dependencies live in the new script’s PEP 723 metadata; no app or CI dependency was added.

## Complete input hash inventory

| Raw filename | Bytes | Elements / entities / pages | SHA-256 |
| --- | --- | --- | --- |
| boundaries.json | 656132 | 50 | 325924423c0fd5b96baf25d81d055aabe8e9edcf7e0a6fdd2220273ece468b08 |
| commons.json | 258209 | 50 | f656f64db30a064e0cfe0ace914e705f898501f027c9309baa5baebb3b1da0b0 |
| geofabrik-source.json | 885 | — | 346cfb9bd36e90db5e2c68923a8ea3227c89ad4a26e44987b83e99da332f5523 |
| green.json | 4615221 | 6963 | ebfb1b77da6ecc5723a44577d22bd02e6358d55834b351f8cda10c77b8cd4c51 |
| overture_places.parquet | 16751722 | — | 4fc739c07941b44da649b03e6627e4c702fc8c303a795a5b02d45e6aa9a69d48 |
| pois_culture.json | 1372910 | 4664 | b0aae81b5510e1791f180ab1d8e61b05d9ad1e50586addaf108766b815e0aa8b |
| pois_essentials.json | 2237059 | 7521 | 899e1d71480ee6953d61167f3df2c4e9f39a7a91aa202b1fb9a3e79d211af479 |
| pois_food.json | 2507530 | 9261 | c7cd2e6f1c1ca0752d03b4d5517618eb1477eaaa10bf9ed9de4fa605ed431c77 |
| pois_nightlife.json | 317814 | 1280 | 8abe8e46d75c499f9738f2a5ac63193f7fbeb0d7b1408773ce692eb58ea81842 |
| pois_sports.json | 281796 | 1456 | e470abc422dc27eca9d27885493105a39b7ce2150e5471288cfd4d5ba8027fcd |
| pois_transit_other.json | 1166974 | 5172 | 13a9c134c212e3343ae6b0ad63984b168664d0df33e9a62aade2d9a09360acf1 |
| province.json | 126431 | 1 | 8600565a72ffd97cfdbbb7037c516f79d9cb67b9343c1f22978fdfa61b33dcf1 |
| rail_routes.json | 295771 | 20 | 23100cc64c8a7d8fc1c61038df665e55a01ff030848aa5892701050a9b8d7037 |
| rail_stations.json | 227947 | 449 | 594b2a6d432cb8233720bfd64d501ef93580df5720905e31e3845b88faaab361 |
| rail_stops.json | 106999 | 311 | d15a8cc0ce7417e52c42218adf3af48a98ac9f3931251cace6d7630b4e36dd3e |
| station_commons.json | 770163 | 215 | b7c59e2e6c44bd3ff0c3fc1a44e526b5974d3e351c724299970c4d1459a47dd2 |
| station_wikidata.json | 2338535 | 232 | a6d59e2b5c46f8df8ac6f6b9200ccd172e9c9402f3da1fe0be1e315140249de2 |
| tha_ppp_2020_constrained.tif | 28878233 | — | 400dc5435e15e78ce6b5e510327ec863c62d209011ce1b03cad4445773753d42 |
| thaifloodrisk.zip | 68400 | — | 8ce4a1c95771f56204d979dafcb61df44f4f2aee4e19fbf40adc75ebbb8b8ddf |
| thailand.osm.pbf | 329280467 | — | e8373240cf0be47cc641f2c8627e674064d8c47f4ff2a11f6a33fcbfc9a50949 |
| thailand.osm.pbf.source.json | 511 | — | 1d535bef282aca95f7f6190ae7d34f6ffce9901fcf45efb0a860b55843ff984e |
| wikidata.json | 1588816 | 50 | 9796226186ab139d20aa24957fa98869148ba1ca5dfc6b46a587b73a73c28c68 |

The `geofabrik-source.json` and `.pbf.source.json` entries are provenance files, not additional source datasets. `_fetched_at` for all OSM JSONs is `2026-10-25T22:06:37.474760+00:00`; all use OSM replication `2026-10-24T20:20:51Z`. Overture is pinned as described above; copied cache file modification times do not establish their observation dates.

## Complete tracked Bangkok file audit

All 67 baseline tracked files are covered below, plus the one added replacement binary. A dash denotes absence. Full exact hashes appear for every path, including 59 unchanged files; abbreviated filenames are not used as a substitute for hash verification. `Changes` counts recursive JSON change records as defined above, not Git lines or individual coordinate values when list lengths differ.

| Path | Bytes before → after | Changes | SHA-256 before → after |
| --- | --- | --- | --- |
| app/public/data/bangkok/grid-1d6ed2ef00c3.bin | — → 143925 | binary | — → 1d6ed2ef00c3e72e199f3de6e896bf5ae1edb78ca3dc6da701bb5dbd0158e719 |
| app/public/data/bangkok/grid-4ab45661dc7b.bin | 143624 → — | binary | 4ab45661dc7ba331f84abd1cbd1d564cf09760aca62b47e71520193a2705cd8e → — |
| app/src/data/bangkok/districts.json | 338479 → 393055 | 138 | 8ef5b0fd4cae3e8ef70c5b4968130fcfdf0c39a4bfe9dc9c4e907758d8930f39 → 9a897f8112353e7a0b090e2264d31d041954554bdd1ef9fdf1ed382b45bbb3cf |
| app/src/data/bangkok/geometry.json | 141297 → 141358 | 14 | 50311bf3681294086ec930041e553d35bd8f0ad2764563920d4abe90f96b75af → 1cfd9ccb9afbe662b7ba9cd36a729778b9cac2a14f70364664f576be840adb43 |
| app/src/data/bangkok/grid.json | 7521 → 7521 | 4 | 1b649fe5d8be9620175c456dd84b55de72d133e8736678a7868d1dfdffdde781 → b9249806de00572b997a70d865590536e62da4fa912179ac25cad065b2b5a2fc |
| app/src/data/bangkok/meta.json | 1519 → 1520 | 6 | 043671bb768b3034666c7d80ee1b2596460bb93b59f5e08fbdd51b7bf85510d5 → 8a4149a98302b8219dca23ff763bb705949fada9b2c27740998604ad4a403ebf |
| app/src/data/bangkok/rail.json | 56271 → 56858 | 7 | 64b47fec710e0f14fbd0038315462c8517479ce7aacf7fb5b090da66e143deaa → 7b88268788363480ceb56c625a40013725c7ad34178a4f24ff05e8d5b6df8c9c |
| app/src/data/bangkok/station-geometry.json | 58699 → 58699 | 0 | fe5329fe983fd59b072494a0fdfdea41cc76523ef79cb902bfc9e626789ad0fb |
| app/src/data/bangkok/stations.json | 471160 → 579556 | 590 | 94ac162361a25ee64a092648f78d9fe5933726109ec9034472f20aa181562ea2 → d32ae74ef4a2ae43221efec293f138bc655521907ffc54953598f0cae26784e2 |
| data/bangkok/.gitignore | 125 → 125 | 0 | 297d7dee99de102ced7f70e94227e89a751bc2ec46e045f8cfd274d3765a41a7 |
| data/bangkok/descriptions/bang-bon.json | 2480 → 2480 | 0 | 21d9996a149c6bfd2433c0a60f6c514ea32ea12737b439dd7552dc57032e5715 |
| data/bangkok/descriptions/bang-kapi.json | 3150 → 3150 | 0 | b7dc515ca045e896c94dbcc40943eea17e969a39b2038a2190228c14beaaecee |
| data/bangkok/descriptions/bang-khae.json | 2819 → 2819 | 0 | 0fc44f52f61079775020bf1d42da86bf91016843ad1223567e30d40d7db7dc64 |
| data/bangkok/descriptions/bang-khen.json | 3111 → 3111 | 0 | 2f56a3518146d21cdcfd9aa897f4e6ede011aa07b1d7646127313bc74aca908e |
| data/bangkok/descriptions/bang-kho-laem.json | 2872 → 2872 | 0 | 0b12616ba9a4ff4ce21da86331f8098d244230dd75fc2fed6069ff62e114f7cf |
| data/bangkok/descriptions/bang-khun-thian.json | 2863 → 2863 | 0 | b620ef13ad2ee074585b582d27f25412981175158c7ce17630b4bbfcd8b24f07 |
| data/bangkok/descriptions/bang-na.json | 2859 → 2859 | 0 | 39573be97b72ed390313aca1a19c46619f1b2e0ba3a31e2393f00ae69bb29c8b |
| data/bangkok/descriptions/bang-phlat.json | 2963 → 2963 | 0 | 85443ec6a00496380902fe0c1271a6887e6baec37d3ab35c33510dc3e2e92c87 |
| data/bangkok/descriptions/bang-rak.json | 3129 → 3129 | 0 | 6cb5e51db6e637f7ae18b098fdb0fad8f4282ea9d6e3d4cd44bed5de7ded20d3 |
| data/bangkok/descriptions/bang-sue.json | 2967 → 2967 | 0 | 108fc4497d0d69bea0f39709069bf1e314d44cd98286a7e875266d6c8f29dba3 |
| data/bangkok/descriptions/bangkok-noi.json | 2912 → 2912 | 0 | f16ae2b7512f1dd619414352f5f37707de295267915bf4c6c6436c0017fd6042 |
| data/bangkok/descriptions/bangkok-yai.json | 3010 → 3010 | 0 | 9b03a10cf57dee0f86b0300259c60564e78db130c294ac7b247d17bcb3419546 |
| data/bangkok/descriptions/bueng-kum.json | 2938 → 2938 | 0 | 079c7fbd547aea443b541d9b19ea53c95030245e2050d7592dc320adc81e8884 |
| data/bangkok/descriptions/chatuchak.json | 3045 → 3045 | 0 | 8cc3d6b4c74b10e466a65ef529d3e74363fe3f54d0f190af219ea04899f41e76 |
| data/bangkok/descriptions/chom-thong.json | 2941 → 2941 | 0 | fb6b4e1cf88b15b3e183417f35b91d56821259b18a8c6ed553da56dfa7fc777f |
| data/bangkok/descriptions/din-daeng.json | 2889 → 2889 | 0 | bf6cfca895df934a2c31a21881f44a97ff920ca8f6374ff9f04498223a0c3c03 |
| data/bangkok/descriptions/don-mueang.json | 2776 → 2776 | 0 | ae267579c37192e79cc2c27668ed73cc109f10d9d6c3f285618338b0d1543bb5 |
| data/bangkok/descriptions/dusit.json | 3122 → 3122 | 0 | d99873cef880fedacd10b9f5aed185c8a2750ec54f01634c2371e3a953956bbc |
| data/bangkok/descriptions/huai-khwang.json | 2935 → 2935 | 0 | bcd7e3665f6e478323a375ec35e59645b0d099b5e7de9dd223916dff55cfd35d |
| data/bangkok/descriptions/khan-na-yao.json | 2749 → 2749 | 0 | 9ea38d0b5adc584150bc1ff549f9e38dc0d38e23b809cc573ff787f7a945ae6b |
| data/bangkok/descriptions/khlong-sam-wa.json | 2455 → 2455 | 0 | d61d04e608db09f293207281f34fd01528ec6ff644cbc12a12eedd436df1cf4f |
| data/bangkok/descriptions/khlong-san.json | 3156 → 3156 | 0 | 0ca2273dc0792f8df025b37e47aa0f84499b4c1c27d67149e3cae5460982e469 |
| data/bangkok/descriptions/khlong-toei.json | 2850 → 2850 | 0 | 303b38e47938d307ed9819839472b1cdc5abb6d89af79581464e886623b6d024 |
| data/bangkok/descriptions/lak-si.json | 2788 → 2788 | 0 | c395007eb442839adb289162b316cbade11727cc17cc7488e0b40f3e61e0b6bf |
| data/bangkok/descriptions/lat-krabang.json | 2717 → 2717 | 0 | 6ead0f5292754e0380d4677d0e13716fd916065c0284f6dbd32048ff0f8cbaab |
| data/bangkok/descriptions/lat-phrao.json | 3046 → 3046 | 0 | d7f394b34bd9bce7c11d7e5a8cf70e0d0c2f89a39a8e4e439f9b53d1263ccea0 |
| data/bangkok/descriptions/min-buri.json | 2782 → 2782 | 0 | 08535b3abfac976a90fe5aac7dcbcfb6ebf5234e9ff10bcb6dd3bd1e0f78c5d0 |
| data/bangkok/descriptions/nong-chok.json | 2848 → 2848 | 0 | 82d875c16cb7fd6d91bd81123dcebd696da9e06d605f43db5c566d2ccab7c9a4 |
| data/bangkok/descriptions/nong-khaem.json | 2712 → 2712 | 0 | ad369f1a279cf9ec30ca223ad09c0347cf75ebf3a1b68dc9b4bfe95d8bf389ab |
| data/bangkok/descriptions/pathum-wan.json | 3152 → 3152 | 0 | 49fae554713f6134999ec6c25d8242525b7b5df3bb9ccef925a924575e3d38a5 |
| data/bangkok/descriptions/phasi-charoen.json | 2754 → 2754 | 0 | 247f66e6dad15d3a057320202e3023b9d24bed01051d343124e34d510821a098 |
| data/bangkok/descriptions/phaya-thai.json | 3025 → 3025 | 0 | a1b58645284732fdaabac8485b5d244471519fbaec38cbe0b01ce4dfc5bb612b |
| data/bangkok/descriptions/phra-khanong.json | 2755 → 2755 | 0 | 44d0b917128c35ceac9b3a08eb143c0a41e6ece1de67293a2daf59cb7a99e5c0 |
| data/bangkok/descriptions/phra-nakhon.json | 3186 → 3186 | 0 | 1b6b07d6c3eba46ec5cbf223d41805c927e8bf0deaed840c952e07e189f948e3 |
| data/bangkok/descriptions/pom-prap-sattru-phai.json | 3412 → 3412 | 0 | ab58f8826276431545582c32d010255f3cc79f626f6b0e7452731fc525d6cf35 |
| data/bangkok/descriptions/prawet.json | 2760 → 2760 | 0 | 2f4fdd89360b474a7da6f6e21d94679e61cd2d0eacee1abd219a5804bb546cb0 |
| data/bangkok/descriptions/rat-burana.json | 2635 → 2635 | 0 | 58b21664c091f7bee9166d67d8efa90536ad2891a6186ac688aed394212f7a6a |
| data/bangkok/descriptions/ratchathewi.json | 3198 → 3198 | 0 | 5946f23ddf36695dd1c0ae31cd55df4267f493eb1a123ab888a7519fcae22211 |
| data/bangkok/descriptions/sai-mai.json | 2546 → 2546 | 0 | b25a44761db961e2ba2bd1147450bd1d8d72e7677e0b38f9f29db77417838083 |
| data/bangkok/descriptions/samphanthawong.json | 3350 → 3350 | 0 | 3373e230bbcc06dc15f6695029d1481bab6314d9cc2e9729971966e6ea8d67b5 |
| data/bangkok/descriptions/saphan-sung.json | 2812 → 2812 | 0 | 1d7446dc3d8b66619075322efe94507c3de3c4fa95bb8bfa3f527401ebd07416 |
| data/bangkok/descriptions/sathon.json | 3219 → 3219 | 0 | 53d718af35119fc25e9b75acf8fde7c5128fa9ba8dd73bb84cfda0136924e4dd |
| data/bangkok/descriptions/suan-luang.json | 3071 → 3071 | 0 | e8d107da2dfa68e270a143d9eb60a1900eb5f15ec95a942b03bc3e77876803da |
| data/bangkok/descriptions/taling-chan.json | 2767 → 2767 | 0 | 00a9b290a5d6d4d90d119467d43bd28bc32210e89751844ffdae362e1bdaa685 |
| data/bangkok/descriptions/thawi-watthana.json | 2795 → 2795 | 0 | affecaed4a97ee058cd7b200cb16e2cc2af067c0f827f3ecec5e7b898d836155 |
| data/bangkok/descriptions/thon-buri.json | 3262 → 3262 | 0 | c9c9dbd06410e6816c131113e12db4c474fc739e8b429c1440c6ab052dbd41ae |
| data/bangkok/descriptions/thung-khru.json | 2624 → 2624 | 0 | 76eb48f7eed9293e3d4913da10d3d70fb2bc6a74e394f22f2bb5127ff015354e |
| data/bangkok/descriptions/wang-thonglang.json | 3005 → 3005 | 0 | 280670e09758aee2ce23798c5682845fe515a85336974c49fa6874e2ec53b397 |
| data/bangkok/descriptions/watthana.json | 3261 → 3261 | 0 | 01869f2b232360bedc790a024cfc6f1d3eb69bd037d7da965363bf59beb0c964 |
| data/bangkok/descriptions/yan-nawa.json | 2719 → 2719 | 0 | 25c3a2649994038ab948feec9c502ab46b47db22a01d0f9cbb12a263aaa3c77d |
| data/bangkok/editorial.json | 16650 → 16650 | 0 | 1a8a8cd80f71d562b6e980c39ae22385e4a28b12e0b48aca9e38f980be370e10 |
| data/bangkok/flood.json | 16571 → 16571 | 0 | 0660511a59893488c99630983271037a30aa90a21662e457cbbab0300aa1a17f |
| data/bangkok/population-baseline.json | 12879 → 12879 | 0 | 031094eeb1c53401d462957a9e5058e58de881b5a59e30e167c0109ec5ffb1a4 |
| data/bangkok/population-comparison.csv | 11460 → 11460 | 0 | 8fd37cb17373e74d79cfdb039678a21bc420e144de7a5bcb3baee7705f78a064 |
| data/bangkok/population-comparison.json | 40269 → 40269 | 0 | 6306a2352c7c02a5e40ebadc08fdd8adb8e1e51b7bb2d6699fb7a14ce43abfa5 |
| data/bangkok/population-source.json | 1529 → 1529 | 0 | 5e85da5ba4c9b6cb165011e156fb1b7de3f3fe15286e4bc043cfdfc219cec950 |
| data/bangkok/rent-overrides.json | 17121 → 17121 | 0 | 926ec97af57547c9bffc1cb1406350245d774fa7c9703ac576768c8fe4382eb1 |
| data/bangkok/signals.json | 235292 → 235267 | 743 | 19f2fe9a38339a12f1e96bc5a6d38de6d772afac9b400e4320cad72f845cd13d → aae695664be3f516879a4a65b49fe641067a8dcdb820f5e75ff913f2816e85ce |

The data/description files, flood.json, editorial/rent inputs, population manifests/baseline/comparison documents and all station-area geometry are byte-identical. `signals.json` changes for 50/50 district signal objects and 101/133 station-area signal objects; the complete per-field records are in the evidence archive. All non-Bangkok generated paths remain unchanged.

### Exact generated-output Git evidence before restoration

```text
 M README.md
 D app/public/data/bangkok/grid-4ab45661dc7b.bin
 M app/src/data/bangkok/districts.json
 M app/src/data/bangkok/geometry.json
 M app/src/data/bangkok/grid.json
 M app/src/data/bangkok/meta.json
 M app/src/data/bangkok/rail.json
 M app/src/data/bangkok/stations.json
 M data/bangkok/signals.json
 M scripts/bangkok/fetch.py
?? app/public/data/bangkok/grid-1d6ed2ef00c3.bin
?? scripts/bangkok/README.md
?? scripts/bangkok/fetch-geofabrik.py
?? scripts/bangkok/osm_filters.py
?? scripts/bangkok/test_fetch_geofabrik.py
```

```text
 app/public/data/bangkok/grid-4ab45661dc7b.bin |   Bin 143624 -> 0 bytes
 app/src/data/bangkok/districts.json           |  9799 ++++++++++-
 app/src/data/bangkok/geometry.json            |     2 +-
 app/src/data/bangkok/grid.json                |    10 +-
 app/src/data/bangkok/meta.json                |    14 +-
 app/src/data/bangkok/rail.json                |     2 +-
 app/src/data/bangkok/stations.json            | 20848 +++++++++++++++++++++++-
 data/bangkok/signals.json                     |  1490 +-
 8 files changed, 31404 insertions(+), 761 deletions(-)
```

```text
-	-	app/public/data/bangkok/grid-4ab45661dc7b.bin
9798	1	app/src/data/bangkok/districts.json
1	1	app/src/data/bangkok/geometry.json
5	5	app/src/data/bangkok/grid.json
7	7	app/src/data/bangkok/meta.json
1	1	app/src/data/bangkok/rail.json
20847	1	app/src/data/bangkok/stations.json
745	745	data/bangkok/signals.json
```

`git diff` omits the untracked new binary, so its addition is shown by status, the audit table and the archive. The archive patch appends a binary-aware no-index addition for that path. New code/docs/tests were also untracked during this snapshot and are listed separately in status; none are data outputs.

## Complete changed rating list

| District | Category | Before | After | Delta |
| --- | --- | --- | --- | --- |
| don-mueang | food | 3 | 4 | 1 |
| rat-burana | food | 4 | 3 | -1 |
| nong-khaem | green | 2 | 5 | 3 |
| thon-buri | green | 2 | 4 | 2 |
| bangkok-noi | green | 6 | 7 | 1 |
| khlong-sam-wa | green | 3 | 2 | -1 |
| lat-phrao | green | 4 | 3 | -1 |
| phra-khanong | green | 1 | 2 | 1 |
| prawet | green | 7 | 6 | -1 |
| rat-burana | green | 5 | 4 | -1 |
| sai-mai | green | 3 | 2 | -1 |
| taling-chan | green | 4 | 3 | -1 |
| wang-thonglang | green | 2 | 1 | -1 |

| Station area | Category | Before | After | Delta |
| --- | --- | --- | --- | --- |
| setthabutbamphen | green | 2 | 7 | 5 |
| bang-chan | green | 3 | 5 | 2 |
| punnawithi | green | 2 | 4 | 2 |
| ban-thap-chang | green | 4 | 3 | -1 |
| bang-khun-non | green | 5 | 6 | 1 |
| bang-son | green | 5 | 4 | -1 |
| ekkamai | green | 1 | 2 | 1 |
| fai-chai | green | 3 | 4 | 1 |
| huai-khwang | green | 5 | 4 | -1 |
| khlong-san | green | 6 | 5 | -1 |
| lat-phrao-71 | green | 2 | 1 | -1 |
| pho-nimit | green | 3 | 2 | -1 |
| phra-khanong | green | 2 | 3 | 1 |
| ram-inthra-kor-mor-9 | green | 7 | 6 | -1 |
| sai-yud | green | 4 | 3 | -1 |
| sena-nikhom | green | 6 | 7 | 1 |
| si-iam | green | 3 | 2 | -1 |
| si-la-salle | green | 4 | 3 | -1 |
| surasak | green | 6 | 5 | -1 |
| tao-poon | green | 4 | 3 | -1 |
| thong-lo | green | 3 | 2 | -1 |
| udom-suk | green | 3 | 4 | 1 |
| wat-mangkon | green | 7 | 6 | -1 |
| yaek-lam-sali | green | 4 | 3 | -1 |
| chit-lom | gym_sports | 9 | 10 | 1 |
| chong-nonsi | gym_sports | 10 | 9 | -1 |
| phra-ram-9 | gym_sports | 9 | 8 | -1 |
| ratchaprarop | gym_sports | 8 | 9 | 1 |
| bang-khun-non | transport | 3 | 4 | 1 |
| phasi-charoen | transport | 4 | 3 | -1 |
| kalantan | vibe | 2 | 1 | -1 |
| kan-kheha | vibe | 1 | 2 | 1 |
| mahatthai | vibe | 4 | 5 | 1 |
| outer-ring-road-ram-inthra | vibe | 5 | 4 | -1 |
| sanam-pao | vibe | 8 | 7 | -1 |
| sena-ruam | vibe | 7 | 8 | 1 |

## Durable evidence

Primary report: `bangkok-geofabrik-refresh-diff.md` in the city-rating-14 AO artifact directory, with a copy committed as PR documentation. The [AO worker session](ao://sessions/city-rating/city-rating-14) exposes the report and **`bangkok-geofabrik-refresh-evidence.tar.gz`** attachment. The archive is **1,158,309 bytes**, SHA-256 **`1baf6a47b40fb01cc3bf44f5b3c2699d83222e0361928a80917f73a8ed3cd0d8`**. It contains all 67 refreshed output files, `comparison.json` with complete per-entity/per-field changes and input hashes, `bangkok-refresh.patch` including binary additions, and Geofabrik provenance. No PBF, regenerated data commit or merge is part of the code PR.

The archive was read back and each refreshed file verified against its SHA-256 before restoration. To inspect later, unpack outside the git workspace or into an ignored scratch directory; treat its `refreshed/` dataset as one coherent proposed refresh, with the known publication blockers above.
