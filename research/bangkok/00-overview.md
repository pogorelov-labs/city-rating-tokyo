# Bangkok — district layer overview (CRTKY-130)

Second city on the site, launched Sept 2026. Unit of rating: the **khet**
(district), all **50**, not the station: a quarter of Bangkok's districts have
no rail at all, and districts are how residents and listings name places.
Rail stations (179 on 10 lines, 139 inside Bangkok) are drawn on top as
context and feed the transport/commute signals.

Routes: `/bangkok` (map), `/bangkok/district/<slug>` (detail) in EN/JA/RU.
Tokyo stays at `/` and `/station/<slug>` — no Tokyo URL changed.

## Pipeline

```
uv run scripts/bangkok/fetch.py      # network, cached in data/bangkok/raw/ (gitignored, ~50 MB)
uv run scripts/bangkok/build.py      # offline, ~5 s → app/src/data/bangkok/*.json + data/bangkok/signals.json
pytest scripts/bangkok/test_bangkok.py
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

## Sources and confidence (50 districts)

| Category | Sources | Confidence |
|---|---|---|
| Transport | OSM rail network (BTS Sukhumvit/Silom/Gold, MRT Blue/Purple/Yellow/Pink, ARL, SRT Dark/Light Red) + bus stops + boat piers + commute model | moderate ×50 |
| Rent | `data/bangkok/editorial.json` — researcher estimate of typical 1-bed / 2-bed condo asking rents | editorial ×50 |
| Daily essentials | Overture Maps Places + OSM | strong 49 · moderate 1 |
| Safety | `editorial.json` — researcher assessment | editorial ×50 |
| Food | Overture + OSM | strong 43 · moderate 7 |
| Green | OSM park / garden / woodland polygons (ha within 1 km + distance to a ≥ 1 ha park) | moderate ×50 |
| Gym & sports | Overture + OSM (pools weighted 0.3) | strong 27 · moderate 22 · estimate 1 |
| Vibe | Overture + OSM culture venues, cafés, temples, markets, pedestrian streets | strong 27 · moderate 22 · estimate 1 |
| Nightlife | Overture + OSM bars/pubs/clubs/live music, karaoke; hostels weighted only 0.05 | strong 16 · moderate 30 · estimate 4 |
| Quietness | DOPA registered population density (2020, Wikidata) + density of all Overture places, inverted | moderate ×50 |

`strong` = both POI sources well mapped in that district (Tokyo's "2+ sources"
rule). The two sources agree closely across districts — Pearson r of log
density per km²: food 0.92, nightlife 0.90, essentials 0.92, culture 0.93,
gyms 0.77 (`meta.json → source_agreement_r`).

Overture caveat: ~12k Bangkok rows typed `historic_site` are mis-classified
apartment buildings — that category is excluded (`build.py load_overture`).

## Honesty notes (read before quoting a Bangkok number)

1. **Relative scores.** Percentile across 50 districts: a Bangkok 8 ≠ a Tokyo 8.
   The UI says so in the filter panel, the district "How ratings work" box and
   /methodology#bangkok.
2. **Rent and safety are editorial** — no open district-level data exists
   (portals block automated access; the police publish no district crime
   statistics). Rent was calibrated by hand against published aggregates
   (see `editorial.json → _meta`). Safety excludes road traffic.
3. **Mapping bias.** Tourist and expat districts are better mapped in both OSM
   and Overture; outer-district food / nightlife is likely understated.
4. **Borders on roads.** Sukhumvit, Ratchadaphisek and Lat Phrao roads are
   district boundaries. Stations within 150 m of a boundary count for both
   sides; "nearby" = up to 800 m outside. Lat Phrao district has no station
   inside — the Yellow Line runs 0.5 km beyond its edge, in Wang Thonglang.
5. **Registered population** undercounts central districts (many residents
   are not registered where they live).
6. **Official vs OSM area.** Some riverside districts differ from the
   Wikidata/BMA areas (e.g. Bang Rak 3.9 km² in OSM vs 5.5 official) while
   the 50-district total matches (1,566 vs 1,569 km²). Densities use the
   official area.

## Descriptions

`data/bangkok/descriptions/<slug>.json`, EN/JA/RU × atmosphere / landmarks /
food / nightlife, written by parallel LLM agents from per-district data briefs
under `research/bangkok/description-rules.md`. Each agent checked named places
against the OSM boundaries and dropped anything it could not place or confirm
as operating in 2026 (e.g. Emporium and Benjakitti are Khlong Toei, not
Watthana; Esplanade and Jodd Fairs Ratchada are on the Din Daeng side).

## Follow-ups

- **Flood exposure (CRTKY-131).** BMA's Traffy Fondue complaints carry district + type
  (`น้ำท่วม` flood, `จุดเสี่ยง` risk spot, lighting…). The anonymous API does not
  filter by district, and the monthly CSV export requires a registration form
  (name / org / email) — the owner has to request it. Would give a real flood
  dealbreaker and a data-backed safety proxy.
- **Rent data.** Replace editorial rent with listing statistics if a portal
  offers an API or export (FazWaz, DDproperty, Hipflat all 403 scrapers).
- **Foursquare OS Places** is gated on Hugging Face since 2025 (accept terms
  while logged in) — a third POI source.
- **Lines under construction** (Orange East, Purple South, Grey) — add to the
  commute model when they open.
- **MCP server** still serves Tokyo only (CRTKY-132).
