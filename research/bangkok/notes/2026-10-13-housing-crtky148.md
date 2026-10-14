# Bangkok housing stock — condo inventory, towers, new-supply pipeline (CRTKY-148)

Researched: **2026-10-13**, by the open-data research agent. The ask: Overpass
inventory of `building=apartments|residential|dormitory` per khet,
`building:levels` distribution (≥20-floor towers), `building=commercial|mixed_use`
near stations; a numeric Watthana vs Bang Na contrast; link the OSM inventory to
the new-supply pipeline numbers already gathered in
`research/bangkok/notes/2026-10-13-rent-anchors-crtky141.md` (KF/JLL/C&W); and a
verdict on a **fact block** — "condo-dominant area, N towers 20+ floors,
X completions in pipeline" — on district/station pages, with no rating.

**TL;DR: adopt the fact block.** OSM can supply three per-district facts
(apartment-building count, 20+-floor tower count as a *mapped* lower bound,
commercial buildings near rail), but **no open source publishes a per-district
completions pipeline** — the consultants' completions/launches numbers are
citywide or submarket-level only, so the pipeline line of the fact block stays a
manual, citywide context figure from CRTKY-141's sources. `building=mixed_use`
is dead in Bangkok (0 uses city-wide) — do not build on it.

All Overpass numbers below were fetched live by me in this session (commands and
snapshots quoted in §1–§5). Nothing here is an implementation decision — the
owner adopts.

---

## 1. What was actually verified (live runs, 2026-10-13)

### 1.1 Infrastructure reality (recorded because it shaped the method)

- Four mirrors were used: `overpass-api.de`, `overpass.kumi.systems`,
  `overpass.private.coffee`, `overpass.monicz.dev`. Availability oscillated all
  session in ~10–30 min windows (timeouts, HTTP 504, and one IP-level TLS block
  on the main instance after a burst of ~6 requests). Every successful response
  was stamped with its `osm3s.timestamp_osm_base`; **snapshots seen ranged from
  2026-05-06 to 2026-10-13 depending on mirror and time** — the main instance
  served a same-day snapshot (2026-10-13T06:50Z and 21:2xZ) late in the session,
  the community mirrors trailed by 3–8 weeks (kumi 2026-05-31/2026-06-01,
  private.coffee 2026-07-15, monicz 2026-05-06…2026-07-28).
- POST requires a `User-Agent` header — without one overpass-api.de answers
  `406 Not Acceptable`.
- Query-format traps found by experiment (cost hours — do not repeat):
  - `out tags center;` returns **HTTP 400** on all mirrors; the working form is
    `out center;` (body mode + center geometry). Numeric filter
    `["building:levels">=20]` also 400'd; the regex form
    `["building:levels"~"^([2-9][0-9]|[1-9][0-9]{2,})$"]` works everywhere.
  - Overpass count tags arrive as **strings**; adding `tags["ways"]+tags["relations"]`
    in Python concatenates ("211"+"9" → "2119"). Convert with `int()` first. Two
    intermediate sweeps (v8/v9 logs) printed concatenated digits before this was
    caught; all numbers in this note come from the fixed parser (v10) or from
    unambiguous single-count queries.
  - `area(NNN)` ids are `3600000000 + relation_id` computed **as an integer**;
    string-concatenating a prefix silently produces wrong ids for 5–6-digit
    relations (zero counts, no error). First attempt used `area(3600{id})` —
    wrong for every khet.
- Local point-in-polygon (download khet rings + building centers) was attempted
  and abandoned: ring assembly from chunked `out geom` fails when member
  **sub-relations** are merged in (duplicate/offset boundary ways scramble the
  greedy chaining); from direct way members alone Bang Na assembles one clean
  231-point ring, but a full 50-khet local sweep needed >15 sequential fetches,
  which the mirrors could not sustain tonight. The server-side `area()` count
  route (§2) is the robust one.

### 1.2 Khet registry

50 khets confirmed as `admin_level=6` boundary relations inside the project bbox
(13.4907–13.9556 N / 100.3279–100.9383 E), e.g. Watthana = relation **2938036**
("Khet Vadhana" in OSM `name:th-Latn`; the repo's "Watthana" spelling kept),
Bang Na = **3146412**, Khlong Toei = **2938033**. Area id used per khet:
`3600000000 + relation_id`. Full id↔name list is in the session script; the
relation set also picks up surrounding-province amphoe (Nonthaburi, Samut
Prakan…), which were excluded by name.

### 1.3 City-wide inventory (validated, complete)

Query (bbox = project bbox):

```
[out:json][timeout:300];
way["building"~"^(apartments|residential|dormitory|commercial|mixed_use)$"](13.4907,100.3279,13.9556,100.9383);
way["building"]["building:levels"~"^([2-9][0-9]|[1-9][0-9]{2,})$"](…);
node/way["railway"="station"]["station"~"^(subway|light_rail|monorail)$"](…);
out center;
```

Result (18,676 building ways + 170 transit stations; snapshot
**2026-05-31T22:37:44Z**, served by kumi):

| building type | ways (bbox) | share of tagged stock |
|---|---|---|
| apartments (condo proxy) | **3,080** | 16.5 % |
| residential (low-rise/townhouse) | **9,574** | 51.2 % |
| dormitory | **160** | 0.9 % |
| commercial | **5,618** | 30.0 % |
| mixed_use | **0** | 0 % |
| buildings with `building:levels` ≥ 20 | **615** | 3.3 % |

Cross-checks, all consistent:
- Independent `out count` probe on kumi (same snapshot window):
  residential **9,290**, commercial **5,464** (slightly lower because it counted
  ways only, no multipolygon relations) — same magnitude.
- Re-run of the same query ~6 h later on overpass-api.de with the fresh
  **2026-10-13** snapshot returned **19,780 elements** vs 18,846 (18,676
  buildings + 170 stations) on June-1 — OSM's Bangkok building inventory grew
  ≈ +5 % in 4.5 months; counts are a moving target, pin the snapshot.
- `building=mixed_use` = **zero** in the whole metro bbox: Thai mappers do not
  use the tag (mixed-use towers are `building=yes`/`retail` or untagged). Reject
  it for any Bangkok field.

## 2. Per-khet counts (server-side `area()` counts)

Method (per khet, one request; mirrors cycled per request; counts parsed as
integers):

```
[out:json][timeout:180];
area(3600000000+<rel_id>)->.a;
(way["building"="apartments"](area.a);relation["building"="apartments"](area.a););out count;
… same for residential, dormitory, commercial, mixed_use …
(way["building"]["building:levels"~"<towers regex>"](area.a);relation[…];);out count;
(node/way["railway"="station"]["station"~"^(subway|light_rail|monorail)$"](area.a););out count;
```

Status: **4 of 50 khets were swept with clean integer counts this session**
(infrastructure: only a minority of mirror request windows served a response
tonight; the sweep is one small request per khet — the command above — and can
be re-run to completion whenever the mirrors are healthy). Rows are exact
counts; snapshot per row:

| khet | apartments | residential | dormitory | commercial | mixed_use | towers ≥20 | stations | served by | snapshot |
|---|---|---|---|---|---|---|---|---|---|
| **Watthana** | **212** | 18 | 1 | 247 | 0 | **136** | 1 | overpass-api.de | **2026-10-13T22:20Z** |
| **Bang Na** | **36** | 15 | 0 | 22 | 0 | **10** | 5 | overpass-api.de | **2026-10-13T22:26Z** |
| Khlong Toei | 250 | 66 | 0 | 156 | 0 | 106 | 9 | kumi | 2026-07-15T15:22Z |
| Huai Khwang | 82 | 119 | 0 | 36 | 0 | 40 | 1 | monicz | 2026-07-15T15:22Z |

Cross-validation of the parser/id chain: Watthana apartments 212 (Oct-13) vs
**203** measured from monicz @2026-07-15 in an independent single-count query
earlier this session (+4 % in 3 months, consistent); Khlong Toei 9 stations and
Bang Na 5 stations match the dense rail geography; the decode of earlier
garbled sweeps also agrees (Khlong Toei 250 = 241 ways + 9 multipolygon
relations). Every row fits under the June city-wide totals of §1.3.

## 3. Height — `building:levels` distribution

City-wide (June-1 snapshot, §1.3): **615** buildings tagged ≥ 20 floors;
**309** ≥ 30 (50 % of towers); **94** ≥ 40 (15 %); tallest tagged **73**
(one each at 73/70/61/60/58, five at 50). **Zero** tagged buildings sit in the
10–19 band — mappers tag only true towers, so the ≥20 count is a **lower
bound**: untagged mid-rise towers exist, and OSM coverage of Bangkok buildings
overall is partial (9.5k residential ways vs ~1M+ real structures). Present the
number as "mapped towers 20+ floors", never as the district's true tower count.

## 4. Commercial buildings near rail

Within **500 m** of any of the **170** mapped BTS/MRT/ARL/monorail stations
(city-wide, June-1 snapshot, haversine on building centers):
- commercial buildings near a station: **1,854 of 5,618 (33 %)**;
- 20+-floor towers near a station: **324 of 615 (53 %)**.

Half the mapped towers sit within walking distance of rail — the "tower"
and "near-BTS" facts are largely the same buildings; on station pages the
commercial-near-rail count is the more informative of the two.

## 5. Watthana vs Bang Na — the contrast in numbers

Both khets fetched from the **same fresh snapshot** (overpass-api.de
2026-10-13T22:20Z / 22:26Z; one request each; the two runs bracket the
session's endpoint outage). This is the ticket's headline pair — the two
districts sit on the same BTS Sukhumvit line 8 stops apart and are the
canonical "mature condo corridor vs emerging frontier" pair:

| metric (OSM, khet polygon) | Watthana (rel 2938036) | Bang Na (rel 3146412) | ratio |
|---|---|---|---|
| apartments (condo proxy) | **212** | **36** | 5.9× |
| residential (low-rise) | 18 | 15 | 1.2× |
| condo share of mapped housing — apr/(apr+res) | **92 %** | **71 %** | — |
| towers ≥ 20 floors (mapped) | **136** | **10** | 13.6× |
| commercial buildings | 247 | 22 | 11.2× |
| dormitory | 1 | 0 | — |
| stations matched by the `station~subway\|light_rail\|monorail` filter | 1 | 5 | — |

Cross-checks and caveats:
- Watthana apartments 212 (Oct-13) vs 203 (monicz, Jul-15, independent query)
  — consistent growth, not a parsing artifact.
- Bang Na's 5 stations match `data/bangkok/signals.json →
  districts.bang-na.stations` exactly (bang-na, bearing, si-iam, si-la-salle,
  udom-suk). Watthana's 1 vs the repo's 9 station areas exposes patchy OSM
  `station=*` sub-tag coverage in the core (Asok/Nana/Phrom Phong/Thong Lo/
  Ekkamai are mapped, but not with the tag combination filtered here) — do not
  ship the per-khet *station* count as a fact until that is normalized.
- Market cross-reference (CRTKY-141): C&W puts Watthana in the Sukhumvit
  submarket — 48,467 condo units, launches ฿242,130/m², ~90 % of Q2 2026
  launches between Soi 34–63 at ≈฿183,875/m² — while Bang Na falls in the
  "Outer Area" blend at ฿94,302/m² (launch prices 2.6× apart). The editorial
  rent gap — `editorial.json` watthana `rent_1br` 32,000 vs bang-na 13,000
  (2.5×) — tracks the same structure. OSM's count ratios (5.9× condos,
  13.6× towers) exceed the price ratios because Bang Na's newer stock is
  under-mapped: direction consistent, magnitude coverage-limited.

Fact-block sentences these numbers produce:
- Watthana: *"condo-dominant area — 212 mapped condo buildings, 136 towers
  20+ floors; city pipeline: ~8.7k units completed H1 2026 (Knight Frank)."*
- Bang Na: *"condo-dominant area (newer, mid-rise) — 36 mapped condo
  buildings, 10 towers 20+ floors; city pipeline: ~8.7k units completed H1
  2026 (Knight Frank)."*

## 6. New-supply pipeline (from CRTKY-141) — and what it can and cannot feed

The consultancies publish **city/submarket supply and launches, never a
per-district pipeline** (all fetched and verified in
`research/bangkok/notes/2026-10-13-rent-anchors-crtky141.md` on 2026-10-13):

| Source (doc, created) | Number | Geography |
|---|---|---|
| Knight Frank, Bangkok Condominium Market Mid-Year 2026 (13028, 02.09.2026) | cumulative supply **797,995 units** H1 2026, **+1.1 % YTD** (⇒ ≈ **8,700 units** completed H1 2026, derived) | Bangkok, city-wide |
| Cushman & Wakefield MarketBeat Q3 2026 (06.10.2026) | total supply **524,433 units** (2008–Q3 2026); **Sukhumvit submarket 48,467 units**; launch prices 2024–Q2 2026: Sukhumvit **฿242,130/m²**, Outer Area **฿94,302/m²**; Q2 prose: **~90 % of Q2 launches between Sukhumvit Soi 34–63 (Watthana)** at ≈**฿183,875/m²** | 7 submarkets + blend |
| JLL APPD Q2 2026 (14.08.2026) | luxury stock **74,922 units**; luxury pipeline **~1,900 units**; vacancy **4.1 %**, gross yield **5.4 %** | CBA / "Central East" only |

Link to the OSM inventory (both sides are counts of *stock*, the pipeline is its
derivative):
- C&W's Sukhumvit submarket = Watthana + Khlong Toei ≈ **48,467 condo units**
  vs OSM **462 mapped apartment buildings** in those two khets (212 + 250, §2)
  → ≈ 105 units/building, which matches Thai condo typology (towers of
  300–800 units + low-rise condos). Good enough as a sanity check, not as a
  conversion factor.
- KF's ≈8,700 units completed H1 2026 vs OSM inventory growth +≈930 building
  ways over June→October — two different things (completions vs mapping
  activity), but both say the same thing: the stock is actively growing; a
  "pipeline" line on a district page must be dated and city-scoped, or it will
  rot.
- Per-khet "X completions in pipeline" is **not obtainable** from any open or
  quotable source found; the honest pipeline line is city-wide with the
  consultant attribution, plus C&W's Watthana-specific colour (Soi 34–63
  launches) as editorial prose, not a number column.

## 7. Verdict — fact block, not a rating

Following the pattern already recommended for institutions
(`research/bangkok/notes/2026-10-13-institutions-crtky145.md`: extend the `facts`
card in `data/bangkok/signals.json` — districts and station_areas both carry a
flat `facts` object, e.g. `watthana.facts.food = 3111`, `asok.facts.food = 729`):

Add to `facts` (rendered as one "Housing stock" row, numbers with source and
snapshot date, **no rating axis, no normalization impact**):

- `housing_apartments` — int, OSM `building=apartments` count per khet /
  station area. Label in UI: "mapped condo buildings".
- `housing_towers_20plus` — int, OSM `building:levels` ≥ 20. Label: "mapped
  towers 20+ floors" (lower bound by construction).
- `housing_commercial_rail` — int, commercial buildings ≤ 500 m of a transit
  station (station areas: recompute inside the repo's own station-area
  polygons — the 500 m radius here is the feasibility proof, not the final
  geometry). Label: "commercial buildings near rail".
- `housing_condo_dominant` — **derived flag, estimate-grade**, e.g.
  apartments ≥ 50 % of (apartments + residential) → "condo-dominant area".
  The count is a fact; the label is an inference from density — mark it like
  the Tokyo mirror note's estimate-grade labels.
- `housing_pipeline` — **manual, city-wide context only**, editorial.json-style
  with `updated:` stamp and citation URLs: "~8.7k units completed in Bangkok in
  H1 2026 (Knight Frank, +1.1 % YTD); luxury pipeline ~1,900 units (JLL Q2
  2026)". Never per-khet.

Example copy (Watthana district page, if §5 numbers are adopted):
*"Condo-dominant: 212 mapped condo buildings, 136 towers 20+ floors. City-wide
pipeline: ~8.7k units completed H1 2026 (Knight Frank). Sources: OSM 2026-10-13
snapshot; KF Mid-Year 2026."*

## 8. OSM vs manual — which fields are realistic

| Field | Source | Verdict |
|---|---|---|
| condo (apartment) building count per khet / station area | OSM `building=apartments` | **OSM, adopt** (dated snapshot; partial coverage, consistent per-khet bias) |
| towers 20+ floors | OSM `building:levels` ≥ 20 | **OSM, adopt as lower bound** ("mapped towers") |
| commercial near rail | OSM `building=commercial` + station distance | **OSM, adopt** (`mixed_use` = 0 city-wide — exclude) |
| condo-dominant label | derived ratio from OSM counts | **derived, estimate-grade flag** |
| completions pipeline (units) | KF / JLL / C&W reports | **manual only, city-wide**, ©-restricted figures with attribution |
| per-khet pipeline | — | **not available from any source found; reject the field** |
| condo *unit* count per district | — | **not feasible from OSM** (units untagged); reject |
| dormitory count | OSM `building=dormitory` (160 city-wide) | **drop** — student/dorm stock, not the condo market the ticket is about |

## 9. Adopt / reject summary

| Source | Verdict | Confidence |
|---|---|---|
| OSM `building=apartments` per khet (Overpass `area()` counts) | **adopt** | strong (two mirrors agree; monotone with known condo geography) |
| OSM `building:levels` ≥ 20 | **adopt** (labeled "mapped") | moderate (partial tagging; lower bound) |
| OSM commercial ≤ 500 m of rail | **adopt** | moderate (station set = 170 mapped nodes/ways) |
| OSM `building=mixed_use` | **reject** (0 uses in Bangkok bbox) | — |
| KF / C&W / JLL supply & pipeline figures | **adopt as manual city-wide context** (already vetted in CRTKY-141 §9) | editorial + © attribution |
| Per-district completions | **reject — no source publishes it** | — |
| Local PIP over downloaded rings | **reject for production** (sub-relation pollution; server-side `area()` counts are simpler and reproducible) | — |

## 10. Open questions for the owner

1. Threshold for `housing_condo_dominant` (50 % vs 60 % of apartments+residential)?
2. Snapshot pinning: recompute quarterly from one named mirror and stamp
   `osm3s.timestamp_osm_base` into `_meta`, or compute at build time?
3. Station-area geometry for `housing_commercial_rail`: repo's own station-area
   polygons (recommended) vs the 500 m radius used here?
4. Should the pipeline line appear on every district page (city-wide, identical)
   or only on pages where C&W gives a submarket/launch colour (Watthana's Soi
   34–63 note)?
5. C&W/KF publish quarterly — refresh cadence for the manual pipeline line?

## Sources (all fetched 2026-10-13 unless noted)

- Overpass mirrors: `overpass-api.de`, `overpass.kumi.systems`,
  `overpass.private.coffee`, `overpass.monicz.dev` (snapshot per table; ODbL —
  every response carries "The data included in this document is from
  www.openstreetmap.org … under ODbL").
- `research/bangkok/notes/2026-10-13-rent-anchors-crtky141.md` — KF 13028
  Mid-Year 2026 PDF, C&W MarketBeat Q1–Q3 2026 PDFs, JLL APPD Q2 2026 page
  (numbers quoted in §6 come from that note's verified fetches).
- `research/bangkok/notes/2026-10-13-institutions-crtky145.md` — fact-block
  pattern (§7 follows its recommendation shape).
- `data/bangkok/signals.json` — `districts.*.facts` / `station_areas.*.facts`
  structure (read this session; Watthana `facts` and `stations` fields quoted).
- `data/bangkok/editorial.json` — `watthana.rent_1br 32000`, `bang-na.rent_1br
  13000` (cross-references in §5).
