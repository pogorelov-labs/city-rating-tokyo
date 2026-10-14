# Tokyo nightlife character & entertainment zones — zone-level geofence (CRTKY-182)

Researched: **2026-10-13**, by the open-data research agent. Scope per the ask:
the *character* of Tokyo's night life as a **zone-level** geofence (not
individual venues), neutral wording throughout. This is the Tokyo mirror of
`research/bangkok/notes/2026-10-13-redlight-crtky153.md` — the
**center + radius + kind** schema is reused from it one-to-one. Nothing here
is an implementation decision — the owner adopts the source and the format.

**TL;DR:** All seven ask items resolve to verifiable locations with Wikidata
entities, but **three of the ask's attributions are corrected by the data**:
錦糸町's adult-tagged cluster sits on the **south** side of the station (北側:
0 objects; south: 28), **六本木 has a club-district OSM signature** (8
`amenity=nightclub`, 0 brothel/erotic) rather than an adult-zone one, and
**麻布十番 is not an adult zone at all** (1 nightclub node at the bbox edge;
0 sensitive objects) — the ask's 六本木/麻布十番 grouping covers two
distinct areas ~950 m apart. Unlike Bangkok, **OSM in Tokyo is richly
mapped**: `amenity=love_hotel` 621, `amenity=brothel` 353, `shop=erotic` 22
in the pipeline bbox (the ask's assumed `tourism=love_hotel` tag does not
exist — 0 city-wide, 4 worldwide per Taginfo; the real tag is
`amenity=love_hotel`). The eight zone bboxes hold **206 of the city's 1,202
sensitive-tag objects (17.1 %) in 0.077 % of the area (≈223× average
density)**. The city's single largest cluster is **Yoshiwara (Senzoku,
Taitō): 143 of 375 brothel/erotic objects (38 %) — not in the ask's list**.
Verdict: **promising** — implementable today as curated static data in the
CRTKY-153 format; OSM counts are strong corroboration but zone boundaries
remain common knowledge.

---

## 1. What was actually verified (date, method, live output)

All fetches below were run by me in this session (2026-10-13). Commands are
in short form; raw JSONs are kept outside the repo in `~/tmp_ov_redlight182/`.

**Wikidata API** (`action=wbsearchentities` ×10 names, then
`action=wbgetentities&props=labels|claims` for 9 QIDs + 13 class QIDs): all
zone entities resolved with en/ja/ru labels, P625 coordinates and P31
classes (§3). One 429 rate-limit retry on 烏森 — succeeded after backoff.

**Overpass** (POST `…/api/interpreter`, per-query `out count` / `out center
tags`): a citywide census of every sensitive tag in the pipeline bbox
(35.5–36.0 N / 139.2–139.9 E) plus per-zone bbox dumps (§4) and three
follow-up probes (citywide brothel/erotic dump, Ueno-wide, Kinshichō-wide)
plus a provenance query. **Extract bases are mixed per mirror**: kumi.systems
served bases 2026-07-15/2026-07-24/2026-07-28, private.coffee served
2026-05-06/2026-05-31/2026-06-01 — each count below names its base via its
zone/section; treat all as "May–July 2026 extracts".

**Overpass endpoint health (recorded honestly — it took ~2 h of retries):**
`overpass-api.de` → TLS reset both IPv4/IPv6 from this machine (curl exit
35, same as the Bangkok session); `overpass.osm.ch` → reachable but
**Switzerland-only extract** (0 elements for a Shinjuku probe — verified);
`maps.mail.ru/overpass` → **service gone** (301 to a VK Maps marketing
page); `overpass.osm.jp` → **no longer an Overpass endpoint** (404 Drupal
page); `overpass.openstreetmap.ru` → timeout. Working set =
**`overpass.kumi.systems` + `overpass.private.coffee`**, both heavily
loaded: queries needed 1–10 rounds of retries with 25–165 s backoffs, plus
two transient outage windows (~10–15 min each) mid-session.

**Ward attribution** came from the pipeline's own data — there is no
`geometry.json` for Tokyo wards, so each zone is attributed via its nearest
station anchor in `data/stations.json` and `app/src/data/ward-data.json`
(the same 1,493-station map the product shows; Tokyo special wards live in
`city_name`, `ward_name` is empty — verified by reading both files). This
matches the Bangkok note's rule: attribution must come from the same data
the product shows.

**Existing product copy** checked in `data/descriptions/*.json` (1,493
files): the ten anchor stations already carry nightlife prose, including
歌舞伎町 by name — `higashi-shinjuku.json` EN: *"896 midnight spots, 6
clubs, 7 karaoke. Kabukilcho never sleeps."* (sic — **"Kabukilcho" typo**,
worth fixing independently), and `kinshicho.json` EN: *"Lively, rougher
south side."* — the product's own editorial copy already knew the
Kinshichō correction (§2, item 6).

## 2. The zone list (verified anchors, proposed geofence)

Zone centers/radii are **proposals** tuned to the measured extents of the
Overpass dumps (bbox midpoints; radius ≈ corner distance, rounded); ward is
measured via the anchor station, not assumed. Radii in the 250–500 m band
as the ask requires.

| # | Zone (id) | Center (lat, lng) | r, m | Ward (measured via anchor) | Nearest station area | Wikidata | OSM provenance anchor |
|---|---|---|---|---|---|---|---|
| 1 | `kabukicho` | 35.69536, 139.70291 | 400 | 新宿区 (seibushinjuku, 281 m) | seibushinjuku | Q665216 | node 1952395613 `place=quarter` 「歌舞伎町」 `wikidata=Q665216` |
| 2 | `shinjuku-nichome` | 35.69143, 139.70622 | 350 | 新宿区 (shinjuku-sanchome, 136 m) | shinjuku-sanchome | Q1420043 | — (no OSM object cross-linked) |
| 3 | `roppongi` | 35.66365, 139.73123 | 450 | 港区 (roppongi, 93 m) | roppongi | Q265071 | — |
| 4 | `azabu-juban` (ask grouped with #3; data says drop — see below) | 35.65460, 139.73585 | 300 | 港区 (azabu-juban, 109 m) | azabu-juban | Q4832008 | — |
| 5 | `ikebukuro-kitaguchi` | 35.73218, 139.71208 | 450 | 豊島区 (ikebukuro, 232 m) | ikebukuro | Q542366 (P625 sits ~600 m NW of the cluster — imprecise) | — (venue nodes only) |
| 6 | `kinshicho-minamiguchi` (ask said 北側; **data says south**) | 35.69485, 139.81480 | 350 | 墨田区 (kinshicho, 225 m) | kinshicho | Q11650537 (no ru label, no P625) | bus stops 錦糸町駅前(南口) node 734869358 |
| 7 | `ueno-ameyoko` | 35.70950, 139.77390 | 450 | 台東区 (keiseiueno, 195 m) | keiseiueno / ueno | Q864815 (market), Q576781 (Ueno) | node 4496960001 「アメヤ横丁」 `wikidata=Q864815`; ways 509241395 / 1353273719 「アメ横通り」 |
| 8 | `shimbashi-karasumori` (contrast) | 35.66600, 139.75710 | 400 | 港区 (shimbashi, 136 m) | shimbashi | Q1347299; 烏森 Q65272645 / 烏森神社 Q11567255 | node 57536180 `place=quarter` 「新橋」 `wikidata=Q1347299`; node 260408025 「烏森神社」 `wikidata=Q11567255` |

Per-zone justification, one paragraph each (all numbers from the §4 dumps):

1. **歌舞伎町 (Kabukichō)** — the densest zone: 73 sensitive-tag objects in
   the bbox (23 brothel, 43 love_hotel, 6 nightclub, 1 erotic) plus 113
   bar+pub and 10 `tourism=hotel`+name~ホテル. OSM even carries the zone
   itself: `place=quarter` node cross-linked to Q665216. Extent
   35.69285–35.69786 × 139.70057–139.70525; r=400 covers the whole extent
   (corner distance ≈ 350 m). Wikidata P625 (35.69545, 139.70256) lands
   inside. The adult side (soapland/health rows around 歌舞伎町一丁目
   west of 花園神社, i.e. the Ōkubo-park fringe) and the mainstream side
   (Godzilla Road, Toho building) share the same disc — the `kind` field
   (§5) is what separates the filter semantics from the nightlife fact.
2. **新宿二丁目 (Shinjuku Ni-chōme)** — Wikidata types it `chōme` +
   **`gay village` (Q748198)**; OSM corroborates with 8 `lgbtq`-tagged
   venues (6 `lgbtq=primary`, 2 `lgbtq=welcome`) — the only LGBTQ-dense
   signature among the zones, plus 7 nightclub, 4 brothel, 3 erotic, 39
   bar+pub. Neutral framing is mandatory: this is a mainstream
   nightlife/friendliness fact for many users, not a family-filter signal.
   Kept as `adult_entertainment` only in the sense that the ask's
   "entertainment zone" list targets it; §6 proposes the chip wording that
   does not stigmatize it. Extent 35.69000–35.69285 ×
   139.70354–139.70890; r=350 (the two `shop=erotic` nodes at 139.7085 are
   the eastern edge).
3. **六本木 (Roppongi)** — **OSM signature is a club district**: 8
   nightclub, 3 love_hotel, **0 brothel, 0 erotic**, 55 bar+pub. The
   district's adult-adjacent reputation (hostess clubs, ガス灯通り) is
   common knowledge but is *not* OSM-derivable. Two options for the owner
   (§8): `kind="club_district"` (follows the data; Roppongi never triggers
   the family filter — mirrors Bangkok's RCA treatment) or
   `kind="adult_entertainment"` (follows common knowledge; data does not
   corroborate). My lean is `club_district` — a false-positive family
   filter on a major international district is the costlier error. Extent
   35.66202–35.66527 × 139.72698–139.73547; r=450.
4. **麻布十番 (Azabu-Jūban)** — the ask groups it with Roppongi; the data
   does not support an adult zone: **0** sensitive objects in the bbox, 15
   bar+pub, and the single `amenity=nightclub` hit is **ELE Tokyo**
   (node 2628346254) at the bbox's north edge, ~950 m from Azabu-Jūban
   station and functionally part of the Roppongi-itchome side. The two
   areas are distinct clusters ~950 m apart. **Recommendation: drop
   azabu-juban from this list** (it can live in ordinary nightlife/dining
   facts); kept in the table so the correction is auditable.
5. **池袋北口 (Ikebukuro north/west-north side)** — the second-densest
   zone: 78 objects (22 brothel, 50 love_hotel, 6 nightclub; bar+pub only
   12 — the cluster is venue-row style, not izakaya style). The ask's
   「北口」 is supported but the cluster straddles 北口〜西口北: extent
   35.72906–35.73530 × 139.70911–139.71504, center ~230 m N/NW of
   Ikebukuro station. Wikidata Q542366 P625 (35.73479, 139.70749) sits at
   the cluster's NW edge — usable for identity, not for geometry.
6. **錦糸町北側 → corrected to south** — the ask's 北側 is **not
   supported**: the north-side bbox (35.6955–35.7005 × 139.8115–139.8170,
   base 2026-07-24) holds **0** sensitive objects (but 72 bar+pub — the
   north is a dense izakaya side). A wide probe
   (35.6910–35.7025 × 139.8080–139.8200, base 2026-06-01) found **28
   objects, all south of the station latitude** (35.69310–35.69659 ×
   139.81154–139.81805): 22 love_hotel, 2 brothel, 4 nightclub. The
   product's own copy (`data/descriptions/kinshicho.json`: "rougher south
   side") agrees. Proposed id: `kinshicho-minamiguchi`.
7. **上野／アメ横 (Ueno / Ameya-Yokochō, "смежная")** — the market strip
   itself is a drinking corridor: **198 bar+pub, the highest of all
   zones**. The sensitive objects (3 brothel, 1 erotic, 3 love_hotel, 7
   nightclub) cluster at the **southern, under-viaduct end** toward
   Okachimachi: a wide probe (35.7050–35.7180 × 139.7700–139.7800, base
   2026-07-24) found 17 objects, **none north of ~35.711** — so the
   "adjacent" framing in the ask is exactly right: the market street is
   mainstream, the adult rows are at its fringe. One brothel ("i for
   you", 35.70526) sits ~470 m from the center — outside r=450, same
   acceptable-leak situation as RCA's easternmost club in Bangkok.
8. **新橋／烏森 (Shimbashi / Karasumori) — the contrast zone** —
   after-work drinking town, the RCA analog: 47 bar+pub, 4 nightclub, 1
   erotic, 1 `lgbtq=primary` bar, **0 brothel, 0 love_hotel**. Two caveats
   to keep neutral: (a) the four nightclub nodes' names (新橋スウィーツ,
   CHERRY 新橋, ラズベリードール, 新橋平成女学園) do not read like
   dance clubs — the owner may want a second look before Shimbashi's
   nightclub count feeds any copy; (b) the unnamed `shop=erotic` node
   (6865205886) shows the tag exists here too. Neither changes the
   after-work character. 烏森 is anchored by 烏森神社 (Q11567255,
   35.66678, 139.75679 — inside the disc); Q65272645 (烏森) carries only a
   ja label and no coordinates.

## 3. Wikidata

Verified via the API this session (labels en/ja/ru, P625, P31):

| Entity | QID | P31 | ru / ja label | P625 | Fit |
|---|---|---|---|---|---|
| 歌舞伎町 Kabukichō | **Q665216** | 町丁, **Q3055075 entertainment district**, **Q272888 red-light district** | Кабуки-тё / 歌舞伎町 | 35.69545, 139.70256 | good — cross-linked OSM quarter node exists |
| 新宿二丁目 Shinjuku Ni-chōme | **Q1420043** | 丁目, **Q748198 gay village** | Ни-Тёмэ / 新宿二丁目 | 35.69, 139.70667 (coarse) | good |
| 六本木 Roppongi | **Q265071** | 町丁 | Роппонги / 六本木 | 35.66284, 139.73144 | good |
| 麻布十番 Azabu-Jūban | **Q4832008** | 町丁 | Адзабудзюбан / 麻布十番 | 35.65455, 139.73559 | good |
| 池袋 Ikebukuro | **Q542366** | neighborhood, Chinatown(!), 町丁 | Икэбукуро / 池袋 | 35.73479, 139.70749 | ok for identity; geometry ~600 m NW of cluster |
| 錦糸町 Kinshichō | **Q11650537** | neighborhood | — (no ru) / 錦糸町 | — (none) | identity only |
| 上野 Ueno | **Q576781** | city center, historical region | квартал Уэно / 上野 | 35.71333, 139.77639 | ok (market uses its own entity) |
| アメヤ横丁 Ameya-Yokochō | **Q864815** | shōtengai | — (no ru) / アメヤ横丁 | 35.71006, 139.77454 | good — cross-linked OSM node |
| 新橋 Shinbashi | **Q1347299** | 町丁, administrative entity | Симбаси / 新橋 | 35.66671, 139.75802 | good — cross-linked quarter node |
| 烏森 Karasumori | **Q65272645** (ja label only) / 烏森神社 **Q11567255** | — | — / 烏森 | shrine: 35.66678, 139.75679 | identity only |

Notes for the mirror: Q665216 carries **both** `entertainment district`
(Q3055075) and `red-light district` (Q272888) — the same club-vs-adult
ambiguity the `kind` field separates (the Bangkok note already flagged
this for the mirror). Q11650537 and Q864815 have **no Russian label**, so
RU names must be hand-curated (same situation as Bangkok's
`RU_NAMES` precedent in `scripts/bangkok/static_data.py`). Q542366's P31
includes *Chinatown* (Q202509) — a Wikidata quirk, not a data signal.

**License:** Wikidata CC0; OSM/Overpass ODbL (stated in every response
header) — same conclusion as the Bangkok note; both license-clean.

## 4. OSM corroboration — counts per zone (extracts May–July 2026)

Per-zone dumps (`out center tags`) over the §2 bboxes; bar+pub and
hotel-name proxies via separate `out count`. Full per-element listings in
`~/tmp_ov_redlight182/z_*.json`.

| Zone (bbox base) | brothel | erotic | love_hotel | nightclub | lgbtq | bar+pub | hotel ~ホテル |
|---|---|---|---|---|---|---|---|
| kabukicho (05-06) | 23 | 1 | 43 | 6 | 0 | 113 | 10 |
| shinjuku-nichome (06-01) | 4 | 3 | 1 | 7 | 8 | 39 | 1 |
| roppongi (06-01) | 0 | 0 | 3 | 8 | 0 | 55 | 0 |
| azabu-juban (06-01) | 0 | 0 | 0 | 1 | 0 | 15 | 0 |
| ikebukuro-kitaguchi (06-01) | 22 | 0 | 50 | 6 | 0 | 12 | 5 |
| kinshicho-kitaguchi (07-24) | 0 | 0 | 0 | 0 | 0 | 72 | 1 |
| ueno-ameyoko (07-15) | 3 | 1 | 3 | 7 | 0 | 198 | 6 |
| shimbashi-karasumori (05-31) | 0 | 1 | 0 | 4 | 1 | 47 | 4 |
| **Σ zones** | **52** | **6** | **100** | **39** | **9** | 551 | 27 |
| **Tokyo bbox census** | **353** | **22** | **621** | **189** | **17** | — | 522 |
| (tags also probed) | leisure=stripclub: **0** city-wide | | tourism=love_hotel: **0** city-wide (4 worldwide, Taginfo 2026-10-13) | | | | |

Concentration math: the eight bboxes total ≈ 2.71 km² = **0.077 %** of the
pipeline bbox (≈3,524 km²), yet hold **17.1 % of all sensitive-tag
objects** (206 of 1,202) ≈ **223× average density**. Kabukichō + Ikebukuro
alone: 151 objects.

**Where the rest sits (citywide brothel+erotic dump, 375 elements, base
2026-07-15):** the largest single concentration is **Yoshiwara
(Senzoku 4-chōme, Taitō): 143 elements = 38 % of the city's
brothel+erotic objects** in roughly one 0.5 × 0.6 km quarter — it is not
in the ask's list and deserves an explicit owner decision (§8). Next
cells: central-west band (35.7×139.7) 74, southern (35.5×139.7 —
Kawasaki-side, inside the bbox but outside the 23 wards) 68.

**Why the zone list still cannot be *derived* from OSM:** the tags are
real and dense, but (a) `amenity=love_hotel` mixes standalone love hotels
with ordinary-street buildings — as a *zone* signal it needs boundary
knowledge OSM does not carry; (b) `amenity=brothel` in Tokyo maps
soapland/health rows only where mappers went (Yoshiwara is dense,
Kabukichō partially, many known strips absent); (c) no OSM object defines
any zone *extent* (only single quarter/market nodes). The list remains
**curated common knowledge pinned to verified coordinates**, with OSM as
strong corroboration — a materially stronger position than Bangkok, where
almost nothing was taggable.

## 5. Format proposal — center + radius, static, shared with CRTKY-153

Same argument as Bangkok §5 (only 2 of 8 zones have any OSM zone object at
all; both are points, not extents): **`center + radius_m` discs are the
canonical format**, OSM ids are **provenance only**. Schema identical to
`research/bangkok/notes/2026-10-13-redlight-crtky153.md` §5. Proposed home:
a Tokyo-side static module (the Bangkok precedent is
`scripts/bangkok/static_data.py`; Tokyo has no equivalent yet — placement
is the owner's call):

```python
# Nightlife zones — curated geofence (CRTKY-182). Zone-level, not venues.
# kind: "adult_entertainment" (family filter applies) | "club_district"
# (nightlife fact only) | "afterwork_drinking" (Tokyo addition, see below).
# Ward attribution measured against the pipeline's station/ward data
# (data/stations.json + app/src/data/ward-data.json), 2026-10-13; see
# research/notes/2026-10-13-redlight-crtky182.md.
NIGHTLIFE_ZONES: list[dict] = [
    {"id": "kabukicho", "kind": "adult_entertainment",
     "lat": 35.69536, "lng": 139.70291, "radius_m": 400,
     "districts": ["shinjuku"], "wikidata": "Q665216",
     "osm_node": 1952395613, "verified": "2026-10-13"},
    {"id": "shinjuku-nichome", "kind": "adult_entertainment",
     "lat": 35.69143, "lng": 139.70622, "radius_m": 350,
     "districts": ["shinjuku"], "wikidata": "Q1420043",
     "osm_node": None, "verified": "2026-10-13"},
    {"id": "roppongi", "kind": "club_district",        # owner: or adult_entertainment (§8)
     "lat": 35.66365, "lng": 139.73123, "radius_m": 450,
     "districts": ["minato"], "wikidata": "Q265071",
     "osm_node": None, "verified": "2026-10-13"},
    {"id": "ikebukuro-kitaguchi", "kind": "adult_entertainment",
     "lat": 35.73218, "lng": 139.71208, "radius_m": 450,
     "districts": ["toshima"], "wikidata": "Q542366",
     "osm_node": None, "verified": "2026-10-13"},
    {"id": "kinshicho-minamiguchi", "kind": "adult_entertainment",
     "lat": 35.69485, "lng": 139.81480, "radius_m": 350,
     "districts": ["sumida"], "wikidata": "Q11650537",
     "osm_node": None, "verified": "2026-10-13"},
    {"id": "ueno-ameyoko", "kind": "adult_entertainment",
     "lat": 35.70950, "lng": 139.77390, "radius_m": 450,
     "districts": ["taito"], "wikidata": "Q864815",
     "osm_node": 4496960001, "verified": "2026-10-13"},
    {"id": "shimbashi-karasumori", "kind": "afterwork_drinking",
     "lat": 35.66600, "lng": 139.75710, "radius_m": 400,
     "districts": ["minato"], "wikidata": "Q1347299",
     "osm_node": 57536180, "verified": "2026-10-13"},
]
```

Taxonomy deltas vs Bangkok (shared format, one new value — needs owner
ratification): `azabu-juban` **dropped** (data, §2.4); `kinshicho` renamed
`kinshicho-minamiguchi` with a south center; `roppongi` defaulted to
`club_district` with the open question; and a third kind
**`afterwork_drinking`** for 新橋/烏森 — reusing `club_district` would be
factually wrong (4 nightclubs vs 47 bar+pub: izakaya-land, not clubs) and
Bangkok's RCA semantics ("club district, loud after dark") would mis-copy.
The `kind` field keeps the same invariant as Bangkok: **only
`adult_entertainment` ever triggers the family filter.**

## 6. Product recommendation — fact + optional family chip, no new subsignal

1. **Adopt as a static fact** (this list). Do **not** feed it into the
   nightlife score: `scripts/compute-ratings.py:357-381` already counts
   HP midnight + izakaya + bar + OSM nightlife + karaoke + hostel and
   rates these stations correctly high for "nightlife" — blurring an
   adult-zone flag into the score (a "subsignal") would punish exactly
   the density the nightlife key measures, for a property many users do
   not care about.
2. **Family filter chip** is the one consumer that needs geofence
   semantics: a hard dealbreaker toggle ("avoid adult entertainment
   areas") excluding station areas (Tokyo's page unit is the 1,493
   station anchors; the 800 m catchment convention from
   `compute-ratings.py:426-429` is the natural cell) whose anchor or
   covered cells fall inside any `kind="adult_entertainment"` disc.
   `club_district`/`afterwork_drinking` never trigger it. Cell semantics
   (anchor-in-disc vs overlap) mirrors Bangkok's open question #3.
3. **Prose** (`research/description-generation-rules.md` voice): mention
   zone proximity as a neutral trade-off where true and near (≤ ~800 m),
   at district level, never venue lists/counts — e.g. the existing
   higashi-shinjuku copy ("歌舞伎町は不夜城") is fine; what must *not*
   appear is anything naming venue types or counts of adult venues. The
   map should **not** draw zone outlines (stigma + precision we do not
   have); the flag lives in filter and text.

Suggested neutral wording (EN/JA/RU; aligns with the description rules —
facts over flair, no dramatising):

| Concept | EN | JA | RU |
|---|---|---|---|
| The zone type | "adult entertainment area" | 「大人向けの歓楽街」 | «зона развлечений для взрослых» |
| Filter chip | "Avoid adult entertainment areas" | 「大人向けの歓楽街を避ける」 | «Вдали от зон развлечений для взрослых» |
| Proximity in prose | "Kabukichō's late-night entertainment quarter is a few minutes' walk" | 「歌舞伎町の歓楽街が徒歩数分」 | «Ночной квартал Кабуки-тё — в нескольких минутах пешком» |
| Ni-chōme (neutral) | "LGBTQ-friendly nightlife quarter" | 「LGBTQ+にやさしい飲食街」 | «квартал ночной жизни ЛГБТ-сообщества» |
| Shimbashi (contrast) | "after-work drinking district, busy till late" | 「飲み屋街、深夜まで賑やか」 | «район идзакаи, шумно допоздна» |

Rules to pin: never "red-light district" / 風俗 / «квартал красных фонарей»
in UI copy (loaded; factually wrong for half the list; Wikidata's own ja
label for Q272888 is 風俗街 — do **not** reuse it in copy); JA standard
neutral word is **歓楽街**; name districts, not venues; no venue counts;
the ni-chōme wording must stay positive/neutral (it is also a mainstream
friendly-nightlife fact). Also worth a one-line fix unrelated to zones:
`data/descriptions/higashi-shinjuku.json` EN misspells "Kabukilcho".

## 7. Adopt / reject per source

| Source | Verdict | Why |
|---|---|---|
| Curated static list in the CRTKY-153 schema (this note's 7 zones) | **adopt** | zone extents are common knowledge; OSM corroborates 5 of 7 strongly (kabukicho, nichome, ikebukuro, ueno, shimbashi partially), 2 with corrections (roppongi kind, kinshicho side) |
| OSM Overpass counts (kumi+private.coffee, bases 2026-05-06…07-28) | **adopt, corroboration only** | 206/1202 sensitive objects in 0.077 % of area confirm every kept zone; but zone *boundaries* are not in OSM |
| `amenity=love_hotel` tag | **adopt as the proxy tag** | 621 objects in the bbox; the ask's `tourism=love_hotel` does not exist (0 city-wide, 4 worldwide — Taginfo, checked 2026-10-13) |
| OSM quarter/market nodes (Q665216, Q1347299, Q864815 cross-links) | **adopt as provenance** | real named anchors; not geometry |
| Wikidata | **adopt for ids/labels**, **reject for coordinates** | P625 imprecise (Ikebukuro ~600 m off; Q11650537 has none); ru labels missing on 2 of 10 |
| Pipeline `data/stations.json` + `app/src/data/ward-data.json` | **adopt** | ward attribution and station anchors must come from the same data the product shows |
| OSM as zone *derivation* source | **reject** | tag coverage is mapper-driven (Yoshiwara dense, other known strips absent); extents undefined |
| `amenity=brothel` as a *public-facing* signal | **reject for copy, adopt for corroboration** | real rows exist, but surfacing counts/names to users would be insensitive and maintenance-heavy |

## 8. Open questions for the owner

1. **Yoshiwara (Senzoku, Taitō)** — 143 of 375 city brothel/erotic objects
   (38 %) sit in one small quarter that the ask's list omits. Add it as an
   eighth zone (`kind="adult_entertainment"`) or keep the product silent
   about it? (Data exists for the disc: ~35.7165, 139.8010, r≈350 — not
   proposed here because it is outside the ask; one Overpass dump would
   pin it if wanted.)
2. **roppongi `kind`**: `club_district` (my lean; OSM-supported, RCA-like)
   vs `adult_entertainment` (common knowledge, OSM-silent).
3. **azabu-juban**: confirm the drop (data: 0 sensitive objects; the one
   nightclub is ELE Tokyo at the Roppongi-itchome edge) — or keep as a
   `club_district`/dining fact.
4. **Taxonomy ratification**: is the third kind `afterwork_drinking`
   acceptable in the shared Bangkok+Tokyo vocabulary, or should
   Shimbashi reuse `club_district` with a wording override?
5. **Cell semantics for the family filter**: station anchor inside the
   disc vs 800 m catchment overlap (same question as Bangkok #3) — and
   does the chip ship at all for Tokyo v1?
6. **Corroboration refresh cadence** — re-run the §4 counts yearly; today's
   numbers are May–July 2026 extracts with mixed mirror bases.
7. Not checked this session: whether Overture Places has a usable category
   for secondary corroboration (the pipeline already ingests Overture for
   nightlife — one probe before implementation, same as Bangkok #6).

Sources: Wikidata API (`wbsearchentities`, `wbgetentities` for Q665216,
Q1420043, Q265071, Q4832008, Q542366, Q11650537, Q576781, Q864815,
Q1347299, Q65272645, Q11567255 + 13 class QIDs); Overpass mirrors
`overpass.kumi.systems` / `overpass.private.coffee` (bases per §4; probes
of `overpass-api.de`, `overpass.osm.ch`, `maps.mail.ru`, `overpass.osm.jp`,
`overpass.openstreetmap.ru` recorded in §1); Taginfo API
(`tag/stats` amenity=love_hotel → 5,292 worldwide, tourism=love_hotel → 4);
repo data `data/stations.json`, `app/src/data/ward-data.json`,
`data/descriptions/*.json`; repo code `scripts/compute-ratings.py:357-381,
426-429`; repo docs `research/bangkok/notes/2026-10-13-redlight-crtky153.md`
(format precedent), `research/description-generation-rules.md`,
`research/01-nightlife.md`. All fetched/read 2026-10-13 as described above.
