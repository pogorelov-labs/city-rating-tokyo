# Bangkok shopping & markets: malls, wet/weekend/night markets — OSM tag counts, Wikidata GLA cross-check, per-khet coverage (CRTKY-144)

Researched: **2026-10-13**, by the open-data research agent. This run executed the
ticket's Overpass program live (`shop=mall`, `building=retail` large,
`amenity=marketplace`, name/tag exploration for Chatuchak / ตลาดนัด), the
Wikidata side (SPARQL + property search + a Wikipedia GLA-list fallback), and
per-khet counts via locally stitched district polygons. Area/GLA numbers are
computed by me from fetched geometry, not copied. Nothing here is an
implementation decision — the owner adopts sources and composition.

**TL;DR:** The OSM shopping base is live and dense where it matters but
**two-tiered**: **`shop=mall` 285 objects citywide (263 named, 229 inside the 50
khets)** with every flagship present (Siam Paragon, ICONSIAM, centralwOrld, MBK,
Terminal 21, all Central branches), and **`amenity=marketplace` 432 (323 named,
325 in khets)** — near-universal khet coverage (zero in only **2 of 50** khets).
Markets are the flat signal, malls are the steep one. **GLA does not exist in
Wikidata**: no property models it (searched "leasable"/"floor area"/"gfa");
`P2046 area` is used on **1 of 82** Thai mall items and **0** Bangkok ones;
Wikipedia's "List of largest shopping malls in Thailand" is the only open GLA
list found (**21 Bangkok rows**; **12/21** match OSM by name directly, more via
Thai/variant names). Size signal in OSM = footprint area (computable from
geometry): malls median **4,650 m²** (max 149,421 Siam Premium Outlets),
markets median **2,735 m²** (JJ Weekend Market **112,042 m²**). **Do not read
bare `building=retail` as "large retail"** — median footprint **153 m²**
(Old-Town shophouses; Phra Nakhon alone has 398); an area filter (>5,000 m²)
cuts it to **64 objects citywide**. Composition verdict: **malls are too
top-heavy for a standalone district signal (0 malls in 7 khets), marketplaces
are too weak alone; recommend fact-block "nearest mall N m" + marketplaces as a
booster of daily_essentials, not a new shopping signal** — and Overture as the
fix for the outer-khet mall gap. Mapping bias is real but asymmetric:
retail-building mapping is heavily center-biased, marketplaces are not.

---

## 0. What was actually verified (method, date, live examples)

All Overpass access ran today, **2026-10-13**, via `curl -X POST
--data-urlencode "data=…"` with an explicit User-Agent. Databases seen:

| Source file | Endpoint | `timestamp_osm_base` |
|---|---|---|
| counts, mall.json | overpass-api.de | 2026-10-13T03:33:28Z / 03:42:27Z |
| mkt_geom, chatuchak, districts | maps.mail.ru | 03:59:09Z / 04:11:05Z / 04:14:45Z |
| bldg_geom | maps.mail.ru | 2026-10-13T04:32:57Z |

Live example (verbatim, first probe of the session):

```json
{"type": "count", "id": 0, "tags": {"nodes": "25", "ways": "0", "relations": "0", "total": "25"}}
```
(`node["shop"="mall"]` in the ticket bbox, overpass-api.de.)

Local processing: Python 3.14 over saved JSON (`/tmp/crtky144/*.json`) —
shoelace areas (with cos(lat) correction), district rings stitched from
`admin_level=6` relation member-ways (pair-merge to fixpoint), even-odd
point-in-polygon.

**Not run here (stated as such):** Overture cross-check; distance-to-nearest-
mall computation (fact-block implementation); GLA normalization of Wikipedia
values (they are as-printed in the article, ref-tagged, not re-verified against
SEC/annual reports); `shop=department_store` name dedup beyond counts.

## 1. Access problems (mirrors today)

| Endpoint | Result (2026-10-13) |
|---|---|
| `overpass-api.de` | **works with `-A "UA"`** (returns Apache **406** without any User-Agent header — that is the whole difference vs. yesterday's run which saw TLS resets); intermittently **504 "server too busy"** under load, needs retries |
| `maps.mail.ru` | works, best for big `out geom` dumps (0.4–1.1 MB); ~50 % 504 on first try, succeeds on retry |
| `overpass.kumi.systems`, `overpass.private.coffee`, `overpass.osm.jp` | HTTP 000 (connection failed) |
| `overpass.osm.ch` | responds but **returns 0 elements** — silently wrong, must not be trusted as a fallback |

Consequence for `scripts/bangkok/fetch.py:47`: the pipeline needs (a) a
User-Agent header, (b) mail.ru in the rotation, (c) an emptiness check — a
mirror that answers HTTP 200 with zero elements must trigger a retry, not be
treated as data. `query.wikidata.org` rate-limits hard (HTTP 429 within
minutes of a first query; needs ≥60–90 s sleeps) and 500s on label-service
FILTER constructs.

## 2. OSM tag counts (bbox `13.4907,100.3279,13.9556,100.9383`)

### 2.1 Headline counts per selector

| Selector | nodes | ways | rels | total | named |
|---|---|---|---|---|---|
| `shop=mall` | 25 | 252 | 8 | **285** | 263 |
| `amenity=marketplace` | 98 | 318 | 16 | **432** | 323 |
| `shop=department_store` | 40 | 23 | 1 | **64** | 43 |
| `building=retail` | 2 | 1,208 | 9 | **1,219** | 420 |
| `building=mall` | 0 | 0 | 0 | 0 | — |
| `landuse=retail` (bare) | 0 | 0 | 0 | 0 | — |
| (reference) `shop=supermarket` | 307 | 163 | 3 | 473 | — |

All flagship malls are present with recognizable names (258 unique mall names):
**Siam Paragon, ICONSIAM, centralwOrld, MBK Center, Terminal 21, EmQuartier,
Emporium, Siam Center/Siam Discovery, Central Embassy, Central Ladprao, Central
Rama 9, Central Bangna, Central WestGate, Central Chaengwattana, MEGAbangna,
Siam Premium Outlets, Central Village, Big C, Tesco Lotus, Silom Complex** —
plus 22 unnamed `shop=mall` objects (a data-quality footnote).

Tag gaps relevant to scoring: **`indoor` is used on exactly 0 malls and 0
marketplaces**; `area:size` on 0 malls; `building:levels` on 68/285 malls
(values 2–32); `wikidata=*` on 34 mall objects (25 unique named malls — all 25
Q-ids resolve in Wikidata); `operator` on 28.

### 2.2 `building=retail` is mostly shophouses, not "large retail"

Footprint areas computed by shoelace from `out geom` (n=1,208 ways):
**median 153 m², p90 1,914 m², max 81,806 m²**. Only **64 objects exceed
5,000 m²** and **29 exceed 10,000 m²**. Phra Nakhon alone carries **398**
`building=retail` (old-town shophouse mapping effort) while Bang Bon, Chom
Thong, Rat Burana and Bang Khae carry 0. Any "large retail building" selector
must therefore filter by computed area, not by tag presence.

## 3. Markets: tags and names (the wet/weekend/night exploration)

### 3.1 What exists as tags

- `amenity=marketplace` is the only live market tag: 432 objects. The
  qualifier key `marketplace=*` (e.g. `wet_market`) is used on **0** objects;
  `indoor` on **0**.
- 29 marketplaces also carry `landuse=retail`, 5 also carry `shop=mall`
  (double-tagged), 17 are `building=roof`, 85 `building=yes`, 3 `building=tent`
  — the market is both an area and a structure in OSM practice.

### 3.2 Name exploration: ตลาด dominates, subtypes visible in names

Of 323 named marketplaces, **249 (77 %) contain "ตลาด"**. Subtype keywords in
names (my regex pass over the dump):

| Subtype | Name marker | Count | Examples |
|---|---|---|---|
| flea / temporary | ตลาดนัด | 31 | ตลาดนัดจุฬา (Chula Flea Market), ตลาดนัดกรีนเดย์ไนท์ |
| fresh / wet | ตลาดสด | 27 | ตลาดสดเอกชัย, ตลาดสดศิริชัย |
| floating | ตลาดน้ำ | 16 | ตลาดน้ำคลองลัดมะยม, ตลาดน้ำพิมาลราช |
| night | กลางคืน / Night | 4 | ตลาดกลางคืนพัฒน์พงษ์, Soi 38 Nightmarket, The Street Ratchada Night Market, Suan Lum Night Bazaar |
| weekend / Chatuchak | จตุจักร / Weekend | 1 | ตลาดนัดจตุจักร |

"เปลี่ยว" (the colloquial wet-market word) appears in 0 names — the project
dictionary should key on ตลาดสด/ตลาดนัด/ตลาดน้ำ/กลางคืน instead.

### 3.3 Chatuchak / ตลาดนัด probe (Overpass regex `name~"Chatuchak|Jatujak|จตุจักร|ตลาดนัด"`)

**97 objects** citywide carry these names; **43 are market-named**, and only
**31 of those carry `amenity=marketplace`**. The rest are markets hiding under
other tags: **4 × `landuse=retail`** (ตลาดนัดสังกะสี, ตลาดนัดซอย 1, ตลาดนัดหัวมุม,
ตลาดนัดวันอาทิตย์ "Sunday Flea Market"), **2 × `tourism=attraction`**
(Rot Fai Market Srinakharin, Sai Mai Night Market), **2 × `amenity=food_court`**,
**1 × `shop=supermarket`** (ตลาดนัดเจ๊ฝน), 1 untagged. The flagship
**Chatuchak Weekend Market = way/37911198**, tagged
`amenity=marketplace` + `landuse=retail` + `tourism=attraction`,
`name:en=Chatuchak Market`, footprint **112,042 m²**. The non-`marketplace`
stragglers (≈ 12 objects) are the recall gap of a tags-only market selector.

## 4. Wikidata: the GLA question (ask's cross-check)

### 4.1 GLA is not modeled in Wikidata — negative result, verified three ways

1. **Property search** (`wbsearchentities`, type=property): "leasable" → 0
   results; "floor area" → 0; "gfa" → 1 irrelevant (P6708 departure angle).
   The guesses P2568 (= "repealed by") etc. are ruled out.
2. **SPARQL** over all Thailand mall-class items
   (`P31/P279* wd:Q11315`, `P17 wd:Q869`): **82 items** (79 direct Q11315),
   of which **72 have coordinates**, but only **1 has `P2046 area`**
   (Bluport Hua Hin, 150,000 m² — *outside* Bangkok). **0 of 82 carry any
   gross-leasable-area value.**
3. The 50 Wikidata mall items with coordinates inside the BKK bbox carry
   **0 × P2046**, **0 × P11693 (OSM node ID)**, **1 × P402 (OSM relation ID)**
   (Jungceylon — Phuket). So Wikidata also cannot join to OSM structurally.

### 4.2 The only open GLA list found: Wikipedia

English Wikipedia article **"List of largest shopping malls in Thailand"**
(CC BY-SA) tabulates GLA for **43 malls; 21 rows are located in Bangkok**
(ICONSAM 525,000; CentralWorld 409,500; Siam Paragon 300,000; Fashion Island
350,000; Central Rama 9 214,000; Seacon Square 180,000; … Terminal 21 45,000;
Amarin Plaza 26,000). Matching those 21 Bangkok names against OSM
(`shop=mall` ∪ `shop=department_store`, normalized): **12/21 match directly**
(miss-list includes Fashion Island, CentralPlaza Rama II/III — present in OSM
under Thai-only names — and The Esplanade, present as
`Esplanade Ratchadapisek` in `shop=department_store`). Caveats: the list is
unmaintained/stale in places (e.g. CentralWestGate listed with GLA 210,000;
several 2015+ malls absent: EmQuartier, Central Embassy, Samyan Mitrtown has
GFA on its own page, not the list) and values are article-sourced, not
audited.

### 4.3 Wikidata ↔ OSM mall match (ask's "сколько совпадений с OSM")

Of the **50 Wikidata mall items with coordinates in the BKK bbox**, matching
against all four OSM dumps by normalized English name (+ Thai `name:th` +
containment variants):

- **37 exact/normalized-name matches** (incl. naming-drift pairs like
  CentralPlaza Bangna ↔ `Central Bangna`),
- **+6 variant matches** (Gaysorn → `Gaysorn Amarin`; Siam Discovery Center →
  `Siam Discovery`; Asiatique …Destination → `Asiatique The Riverfront`;
  Jewelry Trade Center → `Jewelry Trade Center Thailand`; The Esplanade →
  `Esplanade Ratchadapisek` (dept_store); Siam Square → `Center Point Siam
  Square` (weak)),
- **≈5 genuinely unmatched**: Pantip Plaza, Interchange21, Lhong 1919,
  Yodpiman Riverwalk, Palladium Square (= renamed `The Palladium World
  Shopping`), Central Rama 2 (present under Thai พระราม 2 — recoverable via
  Thai matching, so effective ≈ **45/50 ≈ 90 %**).

Reverse direction: only **25 named OSM malls carry `wikidata=*`**, so the Q-tag
alone would bridge less than half — name+coordinate matching is the workable
join.

## 5. Per-khet counts (the ask's "counts по кхетам")

Method: the 50 Bangkok `admin_level=6` boundary relations (of 72 relations in
bbox; 22 belong to Nonthaburi/Pathum Thani/Samut Prakan/… and are excluded),
member-ways stitched into rings (pair-merge to fixpoint; the naive greedy
chain left rings unclosed), point-in-polygon of object centers (bbox-centroid
for ways). **Validation: against `addr:district` tags on building=retail +
malls, PIP agrees on 816 / disagrees on 7 (99.1 %)** — the method is sound.

Objects inside the 50 khets: malls **229/285**, marketplaces **325/432**,
department stores **44/64**, building=retail **1,034/1,219** (rest are in the
ring provinces inside the bbox, e.g. Nonthaburi/Samut Prakan).

| Khet | malls | markets | dept | bldg=retail |
|---|---|---|---|---|
| Vadhana (Thong Lo/Asok) | **33** | 7 | 2 | 20 |
| Pathum Wan (Siam) | **30** | 4 | 5 | 63 |
| Bang Rak | 18 | 14 | 3 | 36 |
| Ratchathewi | 14 | 5 | 0 | 20 |
| Khlong Toei | 12 | 10 | 1 | 10 |
| Phra Nakhon | 9 | 18 | 2 | **398** |
| Chatuchak | 7 | **26** | 4 | 31 |
| Bueng Kum | 2 | **23** | 0 | 4 |
| Lat Krabang (outer-east) | 4 | 16 | 0 | 41 |
| Din Daeng | 1 | 15 | 2 | 20 |
| **Sai Mai (outer)** | **0** | 10 | 0 | 8 |
| **Nong Chok (outer-most)** | **0** | 3 | 1 | 2 |
| **Khlong Sam Wa (outer)** | **0** | 6 | 1 | 12 |
| (full 50-khet table saved in the run artifacts) | | | | |

**Zero-coverage khets: malls — 7 of 50** (Sai Mai, Bangkok Yai, Khlong Sam Wa,
Min Buri, Rat Burana, Bang Bon, Nong Chok); **marketplaces — only 2 of 50**
(Saphan Sung, Rat Burana). Markets are close to universal, malls are not.

## 6. Size distribution (footprint area; GLA absent)

Footprint areas via shoelace from `out geom` (cos(lat)-corrected):

| Set | n | median | p90 | max | >5,000 m² | >10,000 m² |
|---|---|---|---|---|---|---|
| `shop=mall` | 252 | **4,650 m²** | 26,697 m² | 149,421 m² (Siam Premium Outlets) | 119 | 76 |
| `amenity=marketplace` | 318 | **2,735 m²** | 23,414 m² | 165,905 m² (สนามหลวง 2 ส่วนขยาย) | 101 | 59 |
| `building=retail` | 1,208 | **153 m²** | 1,914 m² | 81,806 m² | 64 | 29 |

Top mall footprints read like a real ranking (Siam Premium Outlets 149k,
Central Village 108k, Asiatique 103k, MEGAbangna 82k, Central WestGate 66k,
centralwOrld 63k, Seacon Square 58k(ซีคอนสแควร์ — Thai-only name), The Mall
Bangkae 47k). Top market footprints include JJ Weekend 112k and ตลาดนัดรถไฟ
ศรีนครินทร์ 60k. `building:levels` exists on only 68/285 malls (2–32), so
levels are not a usable size proxy; footprint area is.

## 7. Composition verdict (for the owner)

Options from the ask: (a) new `shopping` signal, (b) boost `daily_essentials`,
(c) fact-block "nearest mall N m".

| Option | Verdict | Basis |
|---|---|---|
| New standalone `shopping` signal (malls) | **reject as primary** | 0 malls in 7/50 khets; top-heavy (Vadhana 33 vs outer 0); a district score would be a map of mapper attention, not commerce. With Overture added it could work — but that is a different source decision |
| Boost `daily_essentials` with marketplaces | **adopt** | marketplaces cover 48/50 khets, median footprint 2,735 m², name-keyed (ตลาด) — cheap, flat, and semantically daily-life (fresh/wet markets, ตลาดนัด). Recommend counting marketplaces (+`shop=supermarket` if that signal exists already) into the daily-essentials booster, not a separate axis |
| Fact-block "nearest mall N m" | **adopt** | always computable citywide (229 malls in khets + 48 in ring provinces; flagships all mapped), robust to density bias, one line of UI. Needs centroid-based distance code — not implemented in this run |
| Size/quality bonus (footprint area, GLA) | **optional, OSM-only** | footprint area is computable and ranks flagships correctly; GLA must come from the Wikipedia list (21 BKK rows, stale, CC BY-SA) — recommend against adopting GLA for scoring; at most as a page fact for named malls |

## 8. Mapping-bias risk in outer districts (ask's risk assessment, by counts)

- **Retail buildings** (`building=retail`): worst bias — Phra Nakhon 398 vs 0
  in four outer khets; median 153 m² (shophouses). Do not use unfiltered.
- **Malls**: moderate bias — 0 malls in 7 khets is partly real commerce
  (Nong Chok is rural) and partly mapping (Sai Mai, Min Buri, Khlong Sam Wa
  have markets and supermarkets but no mapped mall). Overture's ~300k places
  in the bbox (per `scripts/bangkok/fetch.py` docstring) is the correct
  cross-check before believing any mall-based number.
- **Marketplaces**: lowest bias — 48/50 khets non-zero, spread follows
  population (Chatuchak 26, Bueng Kum 23, Lat Krabang 16), and the name key
  ตลาด is mapper-independent. A marketplace-based signal survives the
  outer-district test; a mall-based one does not.

## 9. Sources & license

- Overpass: `overpass-api.de/api/interpreter` (counts; DB 2026-10-13T03:33Z),
  `maps.mail.ru/osm/tools/overpass/api/interpreter` (geom dumps; DB
  03:59–04:32Z). Data license **ODbL** (stated in every response).
- Wikidata: `query.wikidata.org/sparql` (TH mall items query, quoted in §4.1;
  bbox coordinate query), `wikidata.org/w/api.php` property searches. License
  **CC0**.
- Wikipedia: en.wikipedia "List of largest shopping malls in Thailand" via
  `action=parse&prop=wikitext`. License **CC BY-SA**.
- Granularity/fields: OSM node/way/relation POIs with `name`, `name:en`,
  `name:th`, `shop`, `amenity`, `building`, `landuse`, `building:levels`,
  `wikidata`; district polygons = OSM relations `admin_level=6`
  (`boundary=administrative`); Wikipedia table columns: mall, location, GLA,
  total area, stores, year.
- Pipeline helpers referenced: `scripts/bangkok/fetch.py:47`
  (OVERPASS_ENDPOINTS — needs UA + mail.ru + empty-answer retry, §1),
  bbox `BBOX` in `scripts/bangkok/static_data.py:195`
  (13.47, 100.30, 13.98, 100.96 — this run used the ticket's slightly tighter
  13.4907–13.9556 / 100.3279–100.9383; counts differ immaterially).
- Ticket: Plane CRTKY-144 (source of the Overpass selector list and the
  three composition options).
- Precedent formats reused: `research/bangkok/notes/2026-10-13-healthfood-crtky149.md`
  (mirror table, PIP method, verdict table).

## 10. Open questions for the owner

1. Fact-block "nearest mall": from **khet centroid** or from **khet boundary**
   (min distance)? Boundary-min is kinder to large outer khets but needs the
   stitched polygons at runtime.
2. Daily-essentials booster: count all `amenity=marketplace`, or require
   `name~ตลาด` precision filter (323 named vs 432 total)? And should the ≈12
   market-named objects hiding under `landuse=retail`/`tourism=attraction`
   (§3.3) be unioned in?
3. Is the stale Wikipedia GLA list acceptable as a *page fact* source for
   named malls (CC BY-SA attribution required), or skip GLA entirely?
4. Overture mall categories for the same bbox — without it, the "0 malls in 7
   khets" claim cannot be separated into real-commerce vs under-mapping.
5. `shop=department_store` (64; Big C / Tesco Lotus branches appear here, not
   as `shop=mall`): fold into the shopping booster, into daily_essentials, or
   exclude as hypermarket-≠-mall?

*Companion notes from the same day:
research/bangkok/notes/2026-10-13-{air-crtky146, flood-crtky139,
healthfood-crtky149, institutions-crtky145, michelin-crtky142, noise-crtky151,
population-crtky140, redlight-crtky153, rent-anchors-crtky141,
safety-crtky150}.md.*
