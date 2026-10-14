# Fitness & movement in Bangkok — gyms/chains vs dance·yoga·pilates·muay-thai·boxing·climbing studios (CRTKY-143)

Researched: **2026-10-13**, by the open-data research agent. Everything below was
fetched **live in this session** against Overpass mirrors (curl), Nominatim, the
OSM taginfo API, and the OSM wiki; commands and outputs are quoted. Nothing
here is an implementation decision — the owner adopts sources and the
gym-vs-studio split. Same district-relation method as the food note of the same
day (`research/bangkok/notes/2026-10-13-healthfood-crtky149.md`); bbox = the
ticket's grid bounds `13.4907,100.3279,13.9556,100.9383` (pipeline `BBOX` in
`scripts/bangkok/static_data.py:195` is slightly wider: `13.47,100.30,13.98,100.96`).

**TL;DR:** OSM/Overpass is live and the fitness layer exists — but it is
**an order of magnitude thinner than the food layer**. `leisure=fitness_centre`
returns **167–170 POIs citywide** (two mirrors, different DB timestamps), of
which only **87 named (52%)** and **18 branded (11%)**; the chain dimension the
ticket cares about is essentially **not tagged** — Virgin Active **0**, Fitfac
(largest muay-thai chain) **0**, Anytime Fitness **1**, Jetts 5 by `brand` but
**0 by `name`**. The "studios" side is vestigial in OSM: `leisure=dance` **2**,
`amenity=dancing_school` **2**, `shop=yoga` **0**; studio reality hides inside
`fitness_centre`/`sports_centre` + `sport` values — **~40 elements citywide**
carry any of yoga/dance/boxing/muay/climbing/pilates keywords
(`sport=muay_thai` has **50 uses on the whole planet**). The khet contrast is
harsher than the food case: **Watthana 12 fitness_centre (9 named) / Lat Phrao
1 / Nong Chok 0; studio-keyword elements 5/0/0** — the gradient measures
**mapping bias**, not demand. Schedules: no open source; OSM has no class tag
(`key=classes`: 9 uses worldwide; wiki recommends only `opening_hours`, present
on 19% of Bangkok fitness_centre) — timetables live in proprietary apps
(Fitness First SEA, Virgin Active, ClassPass, Mindbody). Verdict: **partial** —
usable as a low-weight **fact layer ("presence of fitness POIs")**; the
gym_sports *split* (gym vs classes/studios) would compute on ~50 tagged
elements citywide and is a noise detector unless rebuilt on Overture.

---

## 0. What was actually verified (method, date, live examples)

All Overpass access ran **2026-10-13** via
`curl -s -m <t> -G <mirror> --data-urlencode "data=<query>"` (and one POST
probe). Mirrors that answered: `overpass.private.coffee` (base
`timestamp_osm_base: 2026-07-24T11:04:51Z` — ~3 months stale) and
`overpass.kumi.systems` (freshness not shown in count responses; its full dump
returned 167 elements vs private.coffee's 170 — different DB snapshots). Local
aggregation: `python3 -c` with `json.loads(..., strict=False)` (the mirrors emit
raw control characters in some tag values; `jq` chokes on them).

Live example (verbatim output fragment, first query of the session):

```json
{"type": "count", "id": 0, "tags": {"nodes": "121", "ways": "49",
 "relations": "0", "total": "170"}}
```

Not verified in this run, stated as such: the dedicated Overpass count of
schedule-like keys (`nwr["leisure"="fitness_centre"][~"^(classes?|schedule|timetable|course)$",i](bbox); out count;`)
— **not run** after 12 failed attempts across 3 mirrors (§1); Overture
cross-check; any real-world branch counts beyond OSM (chain sizes are cited
only from the booking-platform pages listed in §6).

## 1. Access problems (mirror availability today)

| Endpoint | Result (2026-10-13) |
|---|---|
| `overpass-api.de` | GET → **406 Not Acceptable** (Apache "An appropriate representation … could not be found"); POST → empty body. Unusable today. |
| `overpass.kumi.systems` | intermittent: two heavy `out tags` dumps succeeded, then **HTTP 000** (connection failure) on most subsequent calls; small queries sometimes returned an HTML `OSM3S Response` wrapper instead of JSON |
| `overpass.private.coffee` | intermittent dispatcher timeouts (`Dispatcher_Client::request_read_and_idx::timeout — server is probably too busy`); succeeded on retry for most queries; carried the per-khet and per-selector counts |
| `overpass.openstreetmap.ru` | empty responses (connection reset) |
| `maps.mail.ru/osm/tools/overpass` | **504 Gateway Time-out** on every attempt — this is the mirror that carried the entire food-note run earlier the same day |

Consequence for the pipeline: `scripts/bangkok/fetch.py:47` lists exactly the
three endpoints that were flaky-or-dead today (main/kumi/private.coffee);
`fetch.py:65-89` already rotates with linear backoff — mail.ru and the
406/HTML-wrapper quirks deserve a retry-aware handler (the wrapper is valid
HTTP 200 HTML, so a 200 alone must not be trusted; the food note's
`fetch.py` remark check covers `remark`, not the HTML page).

## 2. Recon — the real tag set (wide `out count` probes, private.coffee)

Ticket-mentioned selectors first, then variants discovered by probing:

| Selector (bbox-wide) | count | Reading |
|---|---|---|
| `nwr["leisure"="fitness_centre"]` | **170** (121 n + 49 w) | main gym tag; alive |
| `nwr["leisure"="sports_centre"]` | 258 (58 n + 198 w + 2 r) | mostly courts/condo rooms, not studios |
| `… sports_centre` carrying any `sport` | 107 | only 41% have a sport value |
| `nwr["sport"~"^(fitness\|gym)$",i]` | 51 | gyms tagged by sport alone — a second gym pool, partial overlap with fitness_centre |
| `nwr["leisure"~"dance",i]` | **2** | `leisure=dance` is vestigial here |
| `nwr["amenity"~"danc",i]` | **2** | `amenity=dancing_school` |
| `nwr["shop"~"danc\|yoga",i]` | **0** | no shop-based studios |
| `nwr["leisure"~"yoga",i]` | **0** | `leisure=yoga` unused |
| `nwr["shop"="yoga"]` | **0** | taginfo confirms: 12 uses **worldwide** |

Conclusion of the recon: the ticket's `leisure=dance` / `shop=yoga` branches
are empty; the only living studio carrier is the `sport` subtag on
`fitness_centre`/`sports_centre` (+ two `amenity=dancing_school`), and
`fitness_centre` itself already contains studios via `sport=yoga` etc.
Worldwide context (taginfo, data until 2026-10-12): `leisure=fitness_centre`
108 964; `leisure=dance` 11 827; `amenity=dancing_school` 4 301; `sport=yoga`
7 668; **`sport=muay_thai` 50**; `shop=yoga` 12.

## 3. `leisure=fitness_centre` in detail (dump `out tags`, kumi mirror → 167)

| Metric | value |
|---|---|
| total | 167 (118 nodes + 49 ways; private.coffee count gave 170) |
| with `name` | **87 (52%)** |
| with `brand`/`brand:en` | **18 (11%)** |
| with `brand:wikidata` | 13 |
| with `opening_hours` | **32 (19%)** |
| with `sport` | 32 |

Top brands (tag `brand`/`brand:en`): **Fitness First 9, Jetts Fitness 4 +
"Jetts" 1**, then singles (I FIT GYM, F45 Training, Celebrity Fitness,
Fitness 24 Seven).

Chains found by **name regex** among the 87 named
(`^(Fitness First|Virgin Active|Jetts|Anytime Fitness|Apple Fitness|…)\b`):
fitness first 9, jetts 6, crossfit 2, true fitness 1, anytime fitness 1,
absolute 1, f45 1, celebrity 1 → **22 chain instances by name** vs 18 by brand
tag: brand alone undercounts.

**The chain dimension is broken, not thin.** A name+brand+operator scan across
*all* tags in the bbox found: **Virgin Active 0** (has multiple Bangkok clubs —
virginactive.co.th lists Emporium, Central EastVille etc.), **Fitfac 0**
(Bangkok's largest muay-thai gym chain per ClassPass/Bangkok fitness listings),
**Anytime Fitness 1**, **Jetts 0 by name** (its 5 POIs are brand-tagged with
non-matching names), Fitness First 9. With the two biggest named chains absent,
a "chains vs studios" contrast computed from OSM would measure tagging, not the
market.

## 4. The studio layer (dump of sport keywords, kumi mirror)

Query: `nwr["sport"~"muay|thai.?box|boxing|yoga|dance|climbing|pilates|martial",i]` ∪
`nwr["amenity"~"danc",i]` → **40 elements citywide** (39 named; 12 with
`opening_hours`).

| primary tag | sport value | n |
|---|---|---|
| fitness_centre | yoga | 7 |
| sports_centre | climbing | 5 |
| sports_centre / stadium | boxing (incl. +kickboxing variants) | 6 |
| fitness_centre | muay_thai / kickboxing combos | 4 |
| sports_centre | yoga (incl. +pilates, +cycling combos) | 4 |
| amenity=dancing_school | — | 2 |
| leisure=dance | — | 2 |
| fitness_centre | pilates / climbing / boxing (singles) | 3 |
| meditation_centre | yoga | 1 |
| stadium | muay_thai | 1 |
| `sports` | "muay thai;taekwondo;martial arts" | 1 |
| (no primary) | boxing | 1 |
| fitness_centre | multi-sport combos incl. yoga | 3 |

Totals by keyword (overlapping): **yoga ~14, boxing 7, climbing 7,
muay/kickboxing ~6, pilates 4, dance 4** (2 `leisure=dance` + 2
`dancing_school`). Named studio examples: **RSM Rajadamnern Singha Muay Thai
Academy** ×2 (dup), **Urban Playground** ×2 climbing (dup-ish), **Absolute
Studio, RSU Tower Sukhumvit** (cycling;yoga;pilates), **วี ฟิตเนส เอกมัย /
We Fitness Ekkamai** (sport=`weightlifting,_yoga` — malformed, comma instead of
`;`), **CrossFit Naga** ×2, **Thonglor Crossfit** (`wheightlifting` — typo),
**Dance Synergy**, **The Hop Bangkok** (`leisure=dance`) + **The Hop**
(`dancing_school`) — almost certainly the same venue double-tagged.

Reading: **~40 studio-tagged elements in a city of 50 khets** — the studio
"split" would rest on 0–7 elements per district. Also note `fitness_centre`
absorbs studios (yoga 7 + pilates + muay), so "gym vs classes/studios" cannot
be separated by primary tag alone — only by the `sport` value, which only 19%
of fitness_centre carry (32/167).

## 5. Per-khet contrast (Watthana / Lat Phrao / Nong Chok)

Khet polygons: OSM `admin_level=6` relations from Nominatim — Watthana
(`เขตวัฒนা`) rel **2938036**, Lat Phrao (`เขตลาดพร้าว`) rel **2938034**,
Nong Chok (`เขตหนองจอก`) rel **3147501**; counted via `area(3600000000+rel)`
in Overpass (same relations as the food note, which fetched them by geometry).

| District | fitness_centre | of which named | of which branded | studio-keyword elements | leisure=dance | dancing_school | sports_centre | sc + sport=fitness\|gym |
|---|---|---|---|---|---|---|---|---|
| **Watthana** (Sukhumvit/Thong Lo, fitness heart) | **12** | 9 | 2 | **5** | 0 | 0 | 14 | 0 |
| **Lat Phrao** (mid, dense residential) | **1** | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| **Nong Chok** (outer, rural-east) | **0** | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Watthana's 9 named: Fitness First ×2 (branded, sport=fitness), Pilates Station
Bangkok, Dirty B Fitness, The Little Gym, RSM Muay Thai Academy ×2, CrossFit
Naga ×2, Thonglor Crossfit. The gradient **12 → 1 → 0** is steeper than the
food note's 646 → 76 → 12 because the fitness layer itself is ~10× thinner than
food. Lat Phrao having exactly one gym is not a demand statement — it is a
mapping hole (the district hosts multiple malls with gyms in reality; they are
simply not in OSM under any fitness tag). Any district-level gym_sports signal
built on OSM alone would be dominated by this bias.

## 6. Classes & schedules — no open source; ceiling = point presence

- OSM side: the wiki page for `leisure=fitness_centre` recommends only
  `name`, `opening_hours`, `sauna/swimming_pool`, `personal_trainer`,
  `operator` — **no class/timetable tag exists**; it also advises
  `sport=fitness` (not `sport=gym`) and flags `amenity=gym` as a mistake.
  taginfo: `key=classes` **9** and `key=schedule` **38** uses worldwide
  (`key=timetable` 8 753 — transport context). The dedicated bbox-level
  Overpass count of such keys could not be run today (12 failed attempts, §1);
  in the fetched dumps only `opening_hours` appears (19% of fitness_centre,
  30% of studio elements).
- Proprietary side (web check, 2026-10-13): class timetables and booking live
  in chain apps and aggregators — [Fitness First SEA app](https://apps.apple.com/app/fitness-first-sea)
  ("search and book classes, view real-time timetables"),
  [virginactive.co.th](https://www.virginactive.co.th) (schedules + own app),
  [ClassPass Bangkok](https://classpass.com/place/bangkok) (multi-studio
  booking incl. Virgin Active, muay thai, pilates; in Bangkok since 2018),
  Mindbody (boutique-studio booking platform). None publish open data.

So the open-data ceiling for "movement" is exactly the ticket's fallback:
**presence of points** (+ opening hours), never class schedules.

## 7. Verdict per dimension (for the owner)

| Dimension | Verdict | Basis (this run) |
|---|---|---|
| `leisure=fitness_centre` presence count | **adopt as fact layer (low weight)** | live, 167–170 citywide; but 48% unnamed, 11% branded, khet gradient 12/1/0 = mapping bias |
| gym_sports **split** gym vs classes/studios | **reject on OSM alone** | studios = ~40 elements citywide, spread over 4 tag families; `sport` present on only 19% of fitness_centre; chains (Virgin Active, Fitfac) missing entirely — the split would compute 0-vs-0 in most khets |
| chain detection (brands) | **reject as-is** | brand tag 18/167; biggest chains absent; would need Overture brand/category join |
| schedules/classes dimension | **no open source** | §6; proprietary apps only — drop from signal design |
| studio tag families `leisure=dance`, `shop=yoga`, `amenity=dancing_school` | keep only `dancing_school` as a bonus term (2 POIs) | counts 2/0/2 |

Overall: **partial** — the source is live and honest counts exist, but the
ticket's intended gym-vs-studio contrast and the classes dimension do not hold
up on OSM Bangkok data; presence-as-fact is the only defensible output, and a
real fitness/movement signal would need Overture Places (already wired into the
pipeline: `OVERTURE_RELEASE = "2026-09-23.1"` in `scripts/bangkok/fetch.py:53`)
as its carrier — not examined in this run.

## 8. Sources & license

- Overpass mirrors (queried 2026-10-13): `https://overpass.private.coffee/api/interpreter`,
  `https://overpass.kumi.systems/api/interpreter`, plus failed probes against
  `overpass-api.de`, `overpass.openstreetmap.ru`, `maps.mail.ru/osm/tools/overpass`
  (§1). OSM data license: **ODbL** (stated in every response).
- Nominatim (khet relation IDs): `https://nominatim.openstreetmap.org/search`
  — เขตวัฒนา rel 2938036, เขตลาดพร้าว rel 2938034, เขตหนองจอก rel 3147501.
- taginfo API (worldwide tag/key counts, data until 2026-10-12):
  `https://taginfo.openstreetmap.org/api/4/tag/stats`, `/api/4/key/stats`.
- OSM wiki: `https://wiki.openstreetmap.org/wiki/Tag:leisure%3Dfitness_centre`.
- Booking/schedule platforms (proprietary, cited for the ceiling claim):
  [Fitness First SEA](https://apps.apple.com/app/fitness-first-sea),
  [Virgin Active Thailand](https://www.virginactive.co.th),
  [ClassPass Bangkok](https://classpass.com/place/bangkok).
- Pipeline touchpoints: `scripts/bangkok/fetch.py:47` (mirror list),
  `fetch.py:65-89` (rotation/backoff), `static_data.py:195` (`BBOX`).
- Ticket: Plane CRTKY-143. Format & khet method reused from
  `research/bangkok/notes/2026-10-13-healthfood-crtky149.md`.

## 9. Open questions for the owner

1. **Overture cross-check** (release 2026-09-23.1 already in the pipeline):
   how many fitness-category places in the bbox, and does it carry Virgin
   Active / Fitfac / Anytime? This single check decides whether the
   gym-vs-studio split lives or dies — it cannot live on OSM tags.
2. If the fact layer is adopted: dedupe policy for double-tagged/duplicate
   POIs (The Hop ×2 tag families, CrossFit Naga ×2, Urban Playground ×2) and
   for malformed `sport` values (`weightlifting,_yoga`, `wheightlifting`)?
3. Is a district-level fitness count meaningful at all when Lat Phrao = 1 and
   Nong Chok = 0 in OSM — or should the fact layer be Overture-only?
4. Overpass mirror policy: today none of the three configured endpoints
   (`fetch.py:47`) was reliably alive; add mail.ru + HTML-200-wrapper guard to
   the rotation, or move research fetches to the Overture pipeline?
