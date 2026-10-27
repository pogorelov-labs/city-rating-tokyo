# Bangkok — overview (CRTKY-130, levels of detail CRTKY-135)

Second city on the site, launched Sept 2026. Rated at **three levels of
detail**, switchable on the map (`?lv=…`):

| Level | Unit | Count | Rated against |
|---|---|---|---|
| Districts (default) | **khet**, the administrative district | 50 | the other 49 districts |
| Stations (`lv=station`) | the walkable area of a rail station: land ≤ 800 m from it and nearer to it than to any other station; interchanges of different lines ≤ 450 m apart (Asok + Sukhumvit, Sala Daeng + Si Lom, Mo Chit + Chatuchak Park, Ha Yaek Lat Phrao + Phahon Yothin, Phetchaburi + Makkasan, Krung Thep Aphiwat + Bang Sue) are one area | 133 (from 139 stations inside Bangkok) | the other station areas |
| 200 m grid (`lv=grid`) | a 200 × 200 m cell | 39,149 | where residents live (resident-weighted percentile) |

Districts are the unit residents and listings use, and a quarter of them have
no rail at all; station areas are how expats actually choose ("near Phrom
Phong"); the grid shows the micro-geography inside both. Rail stations (179
on 10 lines, 139 inside Bangkok) are drawn on top at every level.

Routes: `/bangkok` (map), `/bangkok/district/<slug>` and
`/bangkok/station/<id>` (detail pages) in EN/JA/RU. Grid cells have no page;
the map popup links to the cell's district and station area. Tokyo stays at
`/` and `/station/<slug>` — no Tokyo URL changed.

## Pipeline

The [acquisition/build guide](../../scripts/bangkok/README.md) now includes
`scripts/bangkok/fetch-geofabrik.py`: a Geofabrik Thailand PBF path that replaces
the OSM Overpass tasks with a coherent, hashed snapshot. Fetch the remaining
Wikidata/Commons/Overture tasks separately as that guide describes. The existing
Overpass workflow below remains available; do not mix OSM snapshots.

**v0.1.0 excluded the full spatial refresh.** The separate [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147)
merged post-release on **2026-10-27** at [ba7aa47](https://github.com/pogorelov-labs/city-rating-tokyo/commit/ba7aa477fb3e06ceada1fad5df2dc5954428cdf4);
the refreshed data is now on **main**, not in the v0.1.0 tag/release.
v0.1.1 packages this post-v0.1.0 data refresh.
All **10 original validation gates are resolved**, with inputs pinned by the
[90-file frozen manifest](../../data/bangkok/refresh-inputs.json). All **133 tourism
areas** retain their fields (99 with hotels, 66 with attractions, 19 badges), as
do **9 Michelin districts** and **5 legacy embassy districts**. Ratings change
in **12/50 districts and 35/133 areas**; the same **50 districts, 133 areas,
179 rail stations and 39,149 cells** remain. The grid binary is now
`grid-1d6ed2ef00c3.bin` (**143,925 bytes**); grid rent/safety and crowd/hub-minute
planes are unchanged. See the [completed remediation](../../docs/DATA_REFRESH_REMEDIATION.md)
and [committed evidence note](notes/2026-10-26-frozen-refresh.md). The extract-specific
attribution/geometry review is complete with documented limits; source changes
do not establish real-world improvement or advance retained source epochs.

```
uv run scripts/bangkok/fetch.py      # network, cached in data/bangkok/raw/ (gitignored, ~50 MB)
uv run scripts/bangkok/fetch-population.py # pinned WorldPop country raster, 28.9 MB (cached, SHA checked)
uv run scripts/bangkok/build.py      # offline, ~15 s → app/src/data/bangkok/*.json, app/public/data/bangkok/grid-<hash>.bin, data/bangkok/signals.json
uv run --with pytest --with requests --with numpy --with shapely --with rasterio pytest scripts/bangkok
```

| Step | What |
|---|---|
| Boundaries | OSM `admin_level=6` relations inside Bangkok (`admin_level=4`), assembled with shapely; shared borders simplified once with `coverage_simplify` (18 m) so neighbours stay gap-free |
| Sample grid | 200 m points inside each district (39k total) |
| POI access | Each point: counts within 800–1200 m, via FFT convolution of 100 m rasters — cross-border access included |
| Resident weighting | A point counts fully once ≥ 10 eateries / shops / clinics are within 500 m; empty paddies and river water keep a 0.1 floor |
| District signal | Resident-weighted mean of the per-point signal |
| Normalisation | Percentile rank across the 50 districts with midpoint ties → 1–10 (same rule as Tokyo) |
| Commute | Door-to-door model to 5 hubs (Siam, Asok, Silom, Rama 9, Mo Chit): walk or motorbike taxi to a station, peak half-headway waits, average commercial line speeds calibrated on published end-to-end times, walking transfers ≤ 500 m, or a road trip with distance-dependent peak speed. District value = resident-weighted median |
| Station areas | Voronoi cell of each rated station ∩ an 800 m disc ∩ Bangkok (the polygons on the map); the grid points inside give a resident-weighted mean per signal → percentile across areas. Commute = from the station itself (the "door to hub" of the median resident is on the page too) |
| Grid | Each 200 m point's own signals → **resident-weighted** percentile across the city (a cell rates 8 when it beats ~75 % of the places people live) |
| Grid packing | One uint8 plane per field over the 330 × 257 bbox (8 ratings, district, resident weight, 5 hub commutes, nearest station + distance, station area), per-row delta, gzip → ~140 KB with a content hash in the name, header in `grid.json`. Fetched only when the grid level opens |
| Station names | JA from the stations' Wikidata items (label checked against the station name — OSM's Si Iam node points at Si La Salle's item), a few hand-written in `static_data.STATION_JA_FALLBACK`; RU keeps the Latin name that is on BTS / MRT signage |


### Reproducing the population replacement (CRTKY-197)

`uv run scripts/bangkok/fetch-population.py` downloads only the pinned WorldPop
country GeoTIFF; no Range requests, TLS exceptions, credentials or OSM refresh.
`data/bangkok/population-source.json` pins the URL, byte count, SHA-256, raster
contract, epoch, production date and license. Rasterio 1.x, NumPy and Shapely
are declared in the build/replay scripts' uv metadata. The ~29 MB raw raster
is cached under `data/bangkok/raw/`, never committed.

`uv run scripts/bangkok/rebuild-population.py` replays the adoption using the
committed district geometry, `population-baseline.json` and the raster. It
regenerates the all-50 `population-comparison.json`/`.csv` and changes only
district crowd ratings/source, signals and district composite anchors.
Before any write, the replay verifies every non-crowd snapshot signature and
requires crowd values to match the exact original snapshot or a recomputed,
verified previous replay. Changed POIs, provenance or anchors fail closed.
No other source dates are advanced. The historical raw OSM/Overture/Wikidata
cache was unavailable during adoption; **a full historical `build.py` replay
has not been verified**. Missing raw inputs still fail explicitly. With that
cache available, `build.py` invokes the same raster aggregation on its
published, simplified/rounded polygons and uses exact POI counts.

The replay retains the original rounded crowd signal's POI log term (maximum
±0.00005 raw uncertainty); it rejects results whose ratings could change
within that interval. It does not invent integer POI counts. Full builds
calculate the POI term directly and may differ in the fourth raw decimal.
Raster cells store **people**, not people/km². Sum pixel centers, excluding
polygon holes; NoData is BSGM-unsettled and contributes zero, with settled
and total pixel counts recorded. Validate all 50 joins, extent coverage,
no duplicate cell assignments and district-sum/union-total reconciliation.
Use the **official area** as before, not angular pixel area or OSM area.
The UTM 47N polygon area in the audit quantifies denominator mismatch only.

Source: WorldPop, University of Southampton; Bondarenko M., Kerr D.,
Sorichetta A. and Tatem A.J. (2020), constrained BSGM population dataset,
[doi:10.5258/SOTON/WP00684](https://doi.org/10.5258/SOTON/WP00684),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Adaptation: district aggregation and density scoring by City Rating.

## Sources and confidence (50 districts)

| Category | Sources | Confidence |
|---|---|---|
| Transport | OSM rail network (BTS Sukhumvit/Silom/Gold, MRT Blue/Purple/Yellow/Pink, ARL, SRT Dark/Light Red) + bus stops + boat piers + commute model | moderate ×50 |
| Rent | `data/bangkok/editorial.json` — researcher estimate of typical 1-bed / 2-bed condo asking rents | editorial ×50 |
| Daily essentials | Overture Maps Places + OSM | strong 50 |
| Safety | `editorial.json` — researcher assessment | editorial ×50 |
| Food | Overture + OSM | strong 44 · moderate 6 |
| Green | OSM park / garden / woodland polygons (ha within 1 km + distance to a ≥ 1 ha park) | moderate ×50 |
| Gym & sports | Overture + OSM (pools weighted 0.3) | strong 27 · moderate 22 · estimate 1 |
| Vibe | Overture + OSM culture venues, cafés, temples, markets, pedestrian streets | strong 27 · moderate 22 · estimate 1 |
| Nightlife | Overture + OSM bars/pubs/clubs/live music, karaoke; hostels weighted only 0.05 | strong 16 · moderate 30 · estimate 4 |
| Quietness | WorldPop constrained 2020 model population / official district area + density of all Overture places, inverted | moderate ×50 |

Station areas use the same sources with per-area thresholds (food ≥ 80
Overture and ≥ 20 OSM places …): strong / moderate / estimate is roughly
half / a third / a sixth for food and essentials, with far more `estimate`
for nightlife and culture in the outer station areas, where there is
little of either to count. Quietness at the station and grid levels is the
density of *all* Overture places within 400 m (the population raster is
not used at those levels), inverted. Grid cells carry no per-cell confidence; the popup says
which scores are district estimates.

`strong` = both POI sources well mapped in that district (Tokyo's "2+ sources"
rule). The two sources agree closely across districts — Pearson r of log
density per km²: food 0.92, nightlife 0.90, essentials 0.92, culture 0.93,
gyms 0.77 (`meta.json → source_agreement_r`).

Overture caveat: ~12k Bangkok rows typed `historic_site` are mis-classified
apartment buildings — that category is excluded (`build.py load_overture`).

### Station-area rent exception

The district table above is unchanged. **10 central station areas** use
DooAsset's published condominium asking-rent medians by bedroom count, across
**all floor areas**, at **estimate** confidence. `data/bangkok/rent-overrides.json`
records sources, dates and separate 1BR/2BR sample sizes. See the
[central rent audit](notes/2026-10-25-central-rent-audit-crtky141.md). These are
single-provider proxies with overlapping 800 m source radii, not fixed-size
representative samples or transaction prices; lease-duration/short-stay
exclusions are not established. The other 123 areas retain district blends,
including Ari and Siam; grid rents stay district-level editorial.
ComparePanel distinguishes proxies, blends and editorial district estimates.

## Honesty notes (read before quoting a Bangkok number)

1. **Relative scores.** Percentile across 50 districts: a Bangkok 8 ≠ a Tokyo 8.
   The UI says so in the filter panel, the district "How ratings work" box and
   /methodology#bangkok.
2. **District rent and safety are editorial** — no open district-level data exists
   (portals block automated access; the police publish no district crime
   statistics). Rent was calibrated by hand against published aggregates
   (see `editorial.json → _meta`). The 10 station-area rent proxies described
   above do not change district values or confidence. Safety excludes road traffic.
3. **Mapping bias.** Tourist and expat districts are better mapped in both OSM
   and Overture; outer-district food / nightlife is likely understated.
4. **Borders on roads.** Sukhumvit, Ratchadaphisek and Lat Phrao roads are
   district boundaries. Stations within 150 m of a boundary count for both
   sides; "nearby" = up to 800 m outside. Lat Phrao district has no station
   inside — the Yellow Line runs 0.5 km beyond its edge, in Wang Thonglang.
5. **Population model vs registration.** District quietness uses WorldPop
   constrained **2020**, produced **2020-09-16**, not a current census or daytime
   visitor count. Displayed population/density facts remain DOPA registration
   (2020 via Wikidata). The model-to-registration gap is evidence consistent
   with registration undercoverage, not a measured count of unregistered
   residents: model assumptions, boundaries and the six-year-old epoch matter.
   Measured adoption result: **10,887,568 modeled vs 5,588,222 registered**
   (1.9483×; registration 48.67% below the model); **20/50 scores change by
   one point**. The all-50 observed comparison and methodological caveats are in
   [the adoption comparison](population-comparison.md).
6. **Official vs OSM area.** Some riverside districts differ from the
   Wikidata/BMA areas (e.g. Bang Rak 3.9 km² in OSM vs 5.5 official) while
   the 50-district total matches (1,566 vs 1,569 km²). Densities use the
   official area.
7. **Grid rent and safety stay district-level.** A grid cell uses its own
   district's editorial estimates, so these categories step at district borders.
   Station-area safety and rents for 123 areas use resident-weighted district
   blends. Only the 10 researched rent overrides use station-area proxies;
   their metric differs from the editorial fixed-size reference. No value is
   extrapolated to neighboring areas or the grid.
8. **Station areas are not a partition.** Land farther than 800 m from any
   station (most of Nong Chok, Bang Khun Thian, Thawi Watthana …) is left
   unpainted at the station level; the district and grid levels cover it.
9. **Grid cells are 200 m samples, not parcels.** Each cell's signals count
   what is within walking range of its centre (800–1,200 m), so neighbouring
   cells share most of their POIs and the surface is smooth by construction.

## Descriptions

`data/bangkok/descriptions/<slug>.json`, EN/JA/RU × atmosphere / landmarks /
food / nightlife, written by parallel LLM agents from per-district data briefs
under `research/bangkok/description-rules.md`. Each agent checked named places
against the OSM boundaries and dropped anything it could not place or confirm
as operating in 2026 (e.g. Emporium and Benjakitti are Khlong Toei, not
Watthana; Esplanade and Jodd Fairs Ratchada are on the Din Daeng side).

## Follow-ups

All open work lives in the **Plane CRTKY-130 subtree (131–153)**, grouped and
kept current in [`backlog.md`](backlog.md). Highlights as of 2026-10-13:

- **Ready to start, no blockers:** CRTKY-139 (open flood data — ThaiFloodRisk
  per-district CSVs may unblock CRTKY-131 without the Traffy export),
  CRTKY-146 (Air4Thai PM2.5, new category), CRTKY-150 (BMA risk-area registry
  for safety), CRTKY-151 (PCD day/night noise), CRTKY-140 (WorldPop/GHS-POP),
  CRTKY-132 (MCP server, Bangkok districts).
- **Blocked / event-driven:** CRTKY-131 (Traffy export registration — owner
  action), CRTKY-136/137/138 (portal API, HF terms, line openings).
- **Category-enrichment research:** CRTKY-142–145, 147–149, 152–153 —
  Michelin and health food, fitness studios, markets, institutions,
  walkability, housing stock, tourist load, red-light zones; rent anchors in
  CRTKY-141.
