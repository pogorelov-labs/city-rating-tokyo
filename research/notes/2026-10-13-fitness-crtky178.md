# Fitness & movement in Tokyo — gym vs classes vs climbing: can `gym_sports` be split? (CRTKY-178)

Researched: **2026-10-13**, by the open-data research agent. Everything below was
fetched/run live in this session against the Overpass API over the Tokyo bbox
`35.5,139.2,36.0,139.9` (the project's extraction bounds per the ask), plus two
web searches for class-schedule open data. Commands and outputs are quoted;
raw dumps are in `/tmp/crtky178/*.json` (ephemeral). Nothing here is an
implementation decision — the owner adopts sources.

**TL;DR:** The ticket's query (`leisure=sports_centre` + `sport=climbing|yoga|
boxing|dance`) is live but **returns only 30 POI citywide** (23 climbing + 7
boxing; **zero** yoga, **zero** dance on sports_centre) — as written it cannot
differentiate 渋谷 vs 八王子 vs 流山 (each gets **0**). The real Tokyo tagging
lives elsewhere: **`leisure=fitness_centre` = 930 POI** (884 nodes + 46 ways;
cross-checked two independent ways), of which **chains are 44 %** (Anytime
133, chocoZAP 105, Curves 51…); **dance studios are tagged `leisure=dance` (72)
and `amenity=dancing_school` (36)** — keys the ticket did not name, while every
"dance-shaped" key it implies (`sport=dance`, `dance=*`, `leisure=dance_hall`,
`shop=yoga`, `shop=dance`, `amenity=gym`, `climbing=*`) is **0**; **`amenity=dojo`
= 98** is the real martial-arts signal. 快活CLUB is **not fitness**: all 50
brand-tagged POI are `amenity=internet_cafe` (ticket brand-list error). Split
volume, citywide: **gym ≈ 930 / classes ≈ 150–180 / climbing ≈ 32** — gym is a
strong signal, classes a viable thin one, climbing is **fact-level only**
(≪1 POI per station on 1493 stations). Class **schedules have no open source**
(web-verified); `opening_hours` covers only **139/930 (15 %)** of gyms. Verdict:
**promising** — OSM carries all three sub-signals, but only after replacing the
ticket's selector set with the discovered schema.

---

## 0. What was actually verified (method, date, live examples)

- All Overpass access ran today, **2026-10-13**, via `curl --data-urlencode
  "data=…"` POST; live DB stamp `"timestamp_osm_base": "2026-10-13T04:48:55Z"`
  (final cross-check query). Count outputs are quoted verbatim in the tables
  below; example verbatim fragment:
  ```json
  {"type": "count", "id": 0, "tags": {"nodes": "884", "ways": "46", "relations": "0", "total": "930"}}
  ```
- Local processing: Python 3 over saved JSON dumps (`/tmp/crtky178/fit_q*.json`,
  `sp_q*.json`, `aux_dumps.json`): dedup by `(type,id)` across quadrants,
  Counter groupings, regex matching over `name|brand|operator|name:en`.
- Big dumps were fetched **per quadrant** (2×2 split of the bbox) because the
  only working mirror times out on full-bbox dumps (§1); quadrant results were
  deduped locally. **Cross-check:** quadrant-derived fitness_centre total (930,
  dedup) == single full-bbox `out count` (930, 884n+46w) — exact match.
- Web searches (2) on class-schedule open data — §7.
- Not verified in this run (stated as such): Overture places cross-check,
  precision of name-regex matches (spot-checked via samples only), per-brand
  truthing, and any per-station radius aggregation (that is implementation).

## 1. Access problems (mirrors today) — same failure mode as the crtky149 run

| Endpoint | Result (2026-10-13) |
|---|---|
| `overpass-api.de` | **406** from Apache on every shape tried (POST, GET, browser UA) — edge-level block in this environment |
| `overpass.kumi.systems` | HTTP 000 (connection failed) |
| `overpass.private.coffee` | HTTP 000 |
| `overpass.osm.jp` | HTTP 000 |
| `overpass.openstreetmap.ru` | HTTP 000 |
| `overpass.osm.ch` | HTTP 200 but **0 elements** and garbage timestamp `"117692"` for a bbox that has 30 matches — **unreliable, excluded** (same as noted in `research/bangkok/notes/2026-10-13-healthfood-crtky149.md` §1) |
| **`maps.mail.ru/osm/tools/overpass`** | **works — all data in this note** |

mail.ru quirks to carry into any implementation (mirrors the crtky149 note):
(a) full-bbox **dump** queries 504 at the nginx front roughly every other try
(count queries never failed); per-quadrant dumps (~20–130 KB) succeeded in
1–4 tries; (b) two failure shapes to detect and retry: nginx `504 Gateway
Time-out` HTML, and `<?xml …><!DOCTYPE html…` wrappers — note that a
**missing `[out:json]` prefix makes Overpass return valid OSM XML** (caught
myself mid-run: a dump "failure" was actually well-formed XML); validation
should assert the body starts with `{` and contains `"osm3s"`.

## 2. The ticket's query, verbatim — and its decomposition

Run as four exact-value selectors on `leisure=sports_centre`, bbox
`35.5,139.2,36.0,139.9`:

```
[out:json][timeout:150];
(
  nwr["leisure"="sports_centre"]["sport"="climbing"](35.5,139.2,36.0,139.9);
  nwr["leisure"="sports_centre"]["sport"="yoga"](35.5,139.2,36.0,139.9);
  nwr["leisure"="sports_centre"]["sport"="boxing"](35.5,139.2,36.0,139.9);
  nwr["leisure"="sports_centre"]["sport"="dance"](35.5,139.2,36.0,139.9);
);
out count;
```

→ **total 30** (25 nodes + 5 ways).

Decomposition from the full `sports_centre`+`sport` dump (528 POI, dedup):

| sport on sports_centre | count | note |
|---|---|---|
| climbing | 23 | e.g. B-PUMP, T-Wall 江戸川橋店, Base Camp Tokyo - Kinshicho, Urban Base Camp 新宿/新橋, Spider Climbing Gym, Quail Climbing Gym (`climbing;bouldering`) |
| boxing | 7 | |
| yoga | **0** | all 45 `sport=yoga` sit on `leisure=fitness_centre` |
| dance | **0** | `sport=dance` is unused in the whole bbox (any object type) |
| Bouldering (capital B) | 1 | exact-match selector misses it; STONE MAGIC |
| climbing_adventure | 3 | substring regex `~"climbing\|…"` would catch these → 33 |
| martial_arts / judo / kendo / budo / brazilian_jiu-jitsu / sumo | 3 / 2 / 1 / 1 / 1 / 6 | ticket did not ask, but that is the sports_centre martial slice |
| tennis / swimming / golf / multi | 145 / 138 / 52 / 43 | the bulk of sports_centre — must be excluded from any gym signal |

Reconciliation: 23 + 7 = 30 ✓ (independent count query and dump agree).

## 3. Real tagging schema of "fitness & movement" in Tokyo (tag exploration)

Counts on the full bbox, all object types, live queries (osm_base
2026-10-13T03:38–04:40Z):

| Tag | Count | Reading |
|---|---|---|
| `leisure=fitness_centre` | **930** (884n+46w) | the gym signal; 39 unnamed, 300 with `brand=*` |
| `amenity=dojo` | **98** (64n+34w) | the real martial-arts signal (not `sport=*` on sports_centre) |
| `leisure=dance` | **72** (68n+4w) | **the real dance-studio signal** (often + `dance:teaching=yes`) |
| `amenity=dancing_school` | **36** (33n+3w) | second dance key, incl. 松山バレエ学校, 杉並バレエ |
| `dance:teaching=*` | 43 | qualifier on the above (subset-ish) |
| `leisure=sports_hall` | 279 (19n+255w) | mostly school/community halls — separate, not gyms |
| `sport=yoga` (any) | 45 | **all on fitness_centre** (incl. ホットヨガLAVA, ヨガ・オージャス) |
| `sport=pilates` | 8 | e.g. Pilates Mirror by Konami, ピラティススタジオB&B |
| `sport=boxing` (any) | 12 | 7 sports_centre + 5 fitness_centre |
| `sport=kickboxing` (on fitness) | 6 | B-Kick X, RIKIX, キックボクシング 治政館… |
| `sport=climbing` (any) | 30 | ≈ sports_centre set; `climbing=*` (wiki schema) = **0** |
| **Negative results (all 0)** | | `sport=dance`, `dance=*`, `dance:style` carries 12 but they are the leisure=dance POIs, `leisure=dance_hall`, `shop=yoga`, `shop=dance`, `shop=fitness`, `amenity=gym`, `amenity=fitness_centre` (nonstandard), `amenity=dojo` alternatives |

`shop=sports` = 425 (395n) — that is **sports retail**, a different signal;
keep out of gym_sports.

Name-pattern volumes inside the 930 fitness_centre (regex over
`name`, case-insensitive, JA+EN; raw hits, not deduped across patterns):
`yoga|ヨガ|ホットヨガ` 27 · `pilates|ピラティス` 11 · `boxing|kick|ボクシン
グ|キック` 18 · `climbing|bouldering|クライミング|ボルダリング` 5 ·
`dance|ダンス` 7 · `24` **74** (the 24-h-gym boom marker: 24/7 Workout, 24gym,
FASTGYM24…).

## 4. Brands (the ask's four + what is actually big)

Union match over `brand | name | operator`, `leisure=fitness_centre` dump:

| Brand | Count | Note |
|---|---|---|
| Anytime Fitness (エニタイムフィットネス) | **133** | brand-tagged 126 (JA 120 + EN 6) + name-only |
| chocoZAP (チョコザップ) | **105** | RIZAP-group 24-h micro-gyms; ∩RIZAP tags = 2 |
| Curves (カーブス) | **51** | women-only franchise |
| JOYFIT | 23 | |
| Konami Sports | 20 | incl. Pilates Mirror |
| Tipness | 18 | |
| HOT YOGA LAVA | 18 | brand/operator マークは LAVA International |
| Central Sports | 16 | |
| Renaissance | 15 | |
| Megalos | 8 | |
| **RIZAP** | **6** | personal-training studios, not the mass chain |
| **快活CLUB** | **0** | **not a gym at all** |

**快活CLUB correction:** `brand~快活CLUB` anywhere in the bbox = **50 POI, every
single one `amenity=internet_cafe`** (the aux dump's tag split shows
`internet_cafe: 50`). The ticket's brand list mixes an internet-café chain into
the fitness set — it will contribute exactly zero to gym counts, by construction.

## 5. Volume for the `gym_sports` split (gym / classes / climbing)

Citywide POI pools (bbox `35.5,139.2,36.0,139.9`, 1493 stations ⇒ bbox-wide
~0.62 POI/station for the whole category):

| Sub-signal | Selector set (discovered schema) | Citywide pool | Per-station avg | Verdict for split |
|---|---|---|---|---|
| **gym** | `leisure=fitness_centre` | **930** | 0.62 | **strong** — split-worthy; chains alone are 44 % of it |
| **classes** | `leisure=dance` ∪ `amenity=dancing_school` (108 raw, overlap small) ∪ fitness_centre `sport=yoga` 45 ∪ `sport=pilates` 8 ∪ name-regex residue (yoga 27, pilates 11, dance 7 — overlaps with the sport-tagged) | **≈ 150–180** | ≈ 0.11 | **thin but real** — dance density differentiates hard (渋谷 13 vs 八王子 1); viable as a secondary term, not standalone |
| **climbing** | sports_centre `sport=climbing|Bouldering|climbing_adventure` (27) + fitness name-regex (5) | **≈ 32** | 0.02 | **fact-level only** — as a per-station count it is ~0 almost everywhere; use as a bonus fact or fold into classes/other |
| (martial, if ever needed) | `amenity=dojo` 98 + boxing 12 + kickboxing 6 | ≈ 116 | 0.08 | separate axis the ticket did not scope |

Overlap caveats stated: the classes union was **not** element-deduped (sport-
tagged and name-regex hits can coincide); the boxing 12 and the yoga 45 are
cleanly disjoint from each other (verified on dumps: yoga only on
fitness_centre, boxing 7/5 split). Current `gym_sports` in the repo is
`OSM gym_count`, 89 % coverage (`research/00-overview.md:22,98` —
1244 strong / 249 estimate) — a split is feasible for gym, marginal for
classes, not for climbing.

## 6. 渋谷 vs 八王子 vs 流山 (area queries, `admin_level`-7 municipal areas)

```
[out:json][timeout:120];
area["name"="渋谷区"]["boundary"="administrative"]->.a;
nwr(area.a)["leisure"="fitness_centre"]; out count; …
```
(same statement set per city; osm_base 2026-10-13T04:40–04:43Z)

| Measure | 渋谷区 Shibuya | 八王子市 Hachioji | 流山市 Nagareyama |
|---|---|---|---|
| `fitness_centre` | **10** (10n) | **11** (10n+1w) | **21** (18n+3w) |
| `sports_centre` | 22 (6n+16w) | 49 (2n+47w) | 18 (1n+17w) |
| sports_centre sport climbing/boxing/yoga/dance | **0** | **0** | **0** |
| fitness_centre name~Anytime\|Curves\|chocoZAP | 2 | 4 | 5 |
| `amenity=dojo` | 3 | 1 | 2 |
| `leisure=dance` | **11** | 1 | 1 |
| `amenity=dancing_school` | 2 | 0 | 1 |
| **fitness_centre ∩ project bbox** | (fully inside) | (fully inside) | **1 of 21** |

Readings, honestly framed:

1. **The ticket's selector set gives 0 in all three cities** — it cannot be the
   split's query. Differentiation comes from `fitness_centre` (10/11/21) and
   `leisure=dance`+`dancing_school` (13/1/1) — the dance gradient is the
   sharpest urban-vs-suburban separator found.
2. **Shibuya is *under-mapped*, not gym-poor.** A small Shibuya-station bbox
   (35.65,139.69,35.68,139.72) alone has 6 fitness_centre and 21 sports_centre
   (mostly ways — big clubs inside complexes). Central Tokyo chains sit inside
   multi-tenant buildings that mappers tag coarsely; the 24-h franchise boom
   (chocoZAP/Anytime) instead saturates suburban Nagareyama (21). Treat raw
   counts as mapping-bias-affected in the core.
3. **流山 is essentially outside the project bbox.** Nagareyama spans
   ≈139.87–139.94 E; the project's east edge is 139.9 E ⇒ only **1 of its 21**
   fitness_centre falls inside the extraction bounds. If 流山 appears in the
   Tokyo station list at all, the bbox or the scope needs an owner decision
   (open question §10.3).

## 7. Class schedules — no open source (checked, not assumed)

Two web searches (2026-10-13), EN+JA: no gym class-timetable open data/API for
Japan exists. Commercial chains (Konami, Tipness, Anytime…) publish schedules
only in their own sites/apps; Japanese open-data portals
([e-Gov Data Portal](https://data.e-gov.go.jp/info/en),
[e-Stat](https://www.e-stat.go.jp/en)) carry municipal **facility locations**
and participation statistics, not lesson timetables. The only machine-readable
schedule-adjacent field in OSM is `opening_hours`, present on **139/930 (15 %)**
of the bbox's fitness_centre. ⇒ For the pipeline: schedule-richness **cannot**
be a signal; at most record `opening_hours` presence as a weak quality/fact
marker. If schedule data is ever wanted, it is a scraping/partnership problem,
not an open-data one.

## 8. Verdict per layer (for the owner)

| Layer | Verdict | Basis (this run) |
|---|---|---|
| Ticket's selector set (sports_centre + sport=climbing\|yoga\|boxing\|dance) | **reject as-is** | 30 POI citywide, 0 in all three contrast cities, 0 yoga/dance; misses `leisure=dance`, `dancing_school`, `dojo`, all of fitness_centre |
| `leisure=fitness_centre` (gym sub-signal) | **adopt** | 930 POI, cross-checked 930==930; 44 % brand-covered; 39 unnamed to filter |
| classes sub-signal (`leisure=dance` ∪ `amenity=dancing_school` ∪ fitness sport=yoga/pilates) | **adopt as thin secondary** | ≈150–180 POI; sharpest city gradient (dance 13/1/1); dedupe overlap before counting |
| climbing sub-signal | **reject as standalone; keep as fact** | ≈32 citywide ≈ 0.02/station |
| `amenity=dojo` / martial slice | **park for a separate axis** | 98 POI; ticket did not scope it |
| 快活CLUB as fitness brand | **reject** | 0 in fitness; all 50 are `amenity=internet_cafe` |
| Class schedules as data source | **no source exists** | web-verified §7; opening_hours 15 % |

Overall: **promising** — OSM/Overpass carries all the sub-signals the ticket
wants, but only under the discovered schema (§3), not the ticket's selector
set; climbing does not survive as its own signal.

## 9. Sources & license

- Overpass: only `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
  answered reliably today (§1); all counts/dumps from it, osm_base
  2026-10-13T03:38–04:48Z. Data license: OSM **ODbL** (stated in every
  response).
- Granularity/fields: OSM node/way POIs; tags `leisure`, `amenity`, `shop`,
  `sport`, `brand`, `operator`, `name`, `opening_hours`, `dance:*`; municipal
  polygons via `area[name=…][boundary=administrative]` (admin_level-7
  municipalities: 渋谷区, 八王子市, 流山市).
- Schedule check: searches surfaced [e-Gov Data Portal](https://data.e-gov.go.jp/info/en),
  [Dateno JP registry](https://dateno.io/registry/country/JP),
  [e-Stat](https://www.e-stat.go.jp/en) — facility locations/statistics only;
  no timetable APIs.
- Repo anchors: `app/src/lib/schema/constants.ts:12,28,42,87,166` (`gym_sports`
  definition/weight/label), `research/00-overview.md:22,98` (gym_count, 89 %
  coverage, 1244 strong/249 estimate). Format precedent:
  `research/bangkok/notes/2026-10-13-healthfood-crtky149.md` (mirror quirk
  handling §1, verdict-per-layer §6/§8 style).
- **Bangkok comparison requested by the ticket:** `research/bangkok/notes/` has
  no fitness note (checked: 10 files, none fitness/crtky143) — wave 3 runs in
  parallel; no cross-reference possible in this run.

## 10. Open questions for the owner

1. Split design: adopt `gym / classes / (fact) climbing` with the §5 selector
   sets, or keep single `gym_sports` and add classes as a separate signal? The
   dance 13/1/1 gradient argues for classes as its own term.
2. Martial arts (dojo 98 + boxing/kickboxing): in-scope for gym_sports at all,
   or a future axis?
3. 流山: only 1 of its 21 fitness POIs is inside the project bbox — is 流山 in
   the Tokyo station scope, and if yes, should the bbox east edge move?
4. Chain handling: count chocoZAP/Anytime as gym votes (44 % of the pool is
   chain), or weight brands down against independents (precision vs diversity)?
5. Mirror policy: bake `maps.mail.ru` + 504-retry + quadrant-split into the
   Tokyo fetch script (the crtky149 note already flags the same for Bangkok's
   `OVERPASS_ENDPOINTS`).
