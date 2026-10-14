# Bangkok nightlife character & adult-entertainment zones — zone-level geofence (CRTKY-153)

Researched: **2026-10-13**, by the open-data research agent. Scope per the ask:
the *character* of Bangkok's night life as a **zone-level** geofence (not
individual venues), neutral wording throughout. Nothing here is an
implementation decision — the owner adopts the source and the format.

**TL;DR:** The six zones in the ask are real and locatable, but **two of the
six district attributions in the ask do not match the pipeline's own
boundaries** (Soi Cowboy → Watthana, not Khlong Toei; Nana Plaza → a Khlong
Toei salient near the Watthana border, and Ratchathewi is nowhere near), and
the Huai Khwang / Ratchadaphisek strip **straddles Din Daeng and Huai
Khwang**. OSM **cannot derive** these zones semantically: `leisure=stripclub`
is tagged **0 times in all of Thailand**, `amenity=brothel` once in Bangkok —
so a curated static list in `static_data.py` is the only honest source. OSM
still corroborates the zones *structurally*: the six zone bboxes hold
**28 of Bangkok's 91 `amenity=nightclub` (31 %) and 52 of 445 `shop=massage`
(12 %) in 0.096 % of the city bbox area**, three zones have named OSM ways
(Soi Cowboy is a mapped `highway=pedestrian`; Nana Plaza is a 7-node
`landuse=retail` polygon cross-linked to Wikidata Q441839). Recommended
format: **center + radius_m, statically curated**, with `kind`
(`adult_entertainment` vs `club_district`) so RCA (contrast case) never lands
in a family filter; schema shared with the Tokyo mirror CRTKY-182 (Kabukichō
Q665216 verified as the mirror anchor). Verdict: **promising** — implementable
today as curated static data; OSM counts are corroboration, never derivation.

---

## 1. What was actually verified (date, method, live output)

All fetches below were run by me in this session (2026-10-13). Commands are
given in short form; raw JSONs are kept outside the repo in
`~/tmp_ov_redlight/`.

**Wikidata API** (`curl "https://www.wikidata.org/w/api.php?action=wbsearchentities…"`
and `action=wbgetentities&props=labels|claims`): five QIDs with coordinates
(P625), RU/JA/TH labels and P31 classes, quoted in §2/§3.

**Overpass** (POST/GET `…/api/interpreter`): per-zone element dumps
(`out center tags`) and `out count` aggregates. Extract base of both working
mirrors: **`timestamp_osm_base: 2026-07-24T11:04:51Z`** — ~3 months stale,
say so wherever counts are cited.

**District attribution**: point-in-polygon (pure-python ray casting) of zone
landmarks against the pipeline's own district polygons
`app/src/data/bangkok/geometry.json` (the same OSM `admin_level=6` boundaries
the product draws). Live output:

```
Soi Cowboy S (Cactus 13.73692,100.56211)  ->  khet = watthana
Soi Cowboy N (club 13.73929,100.56205)    ->  khet = watthana
Nana Plaza (way 13.74139,100.55331)       ->  khet = khlong-toei
Patpong (club 13.72865,100.53286)         ->  khet = bang-rak
HK Emmanuelle (13.77676,100.57283)        ->  khet = din-daeng
HK Mansion7 (13.78139,100.57442)          ->  khet = huai-khwang
Soi33 AtEase33/1 (13.73212,100.56826)     ->  khet = watthana
RCA Amnesia (13.75127,100.57581)          ->  khet = huai-khwang
```

Boundary probes around Nana: 13.74139/100.55150 → khlong-toei,
13.74139/100.55500 → watthana, 13.74300/100.55331 → watthana — the
Khlong Toei/Watthana line cuts through the Soi 4 area; **Nana Plaza sits in a
Khlong Toei salient**. MRT Huai Khwang station (13.77869, 100.57357) and the
southern half of the Ratchadaphisek strip are **Din Daeng**; Mansion 7
(13.78139) is the first Huai Khwang-side landmark of the strip.

**Rail anchors** came from the repo's built data
`app/src/data/bangkok/stations.json` (133 station areas; the pipeline already
resolved OSM↔Wikidata names): Asok 13.73704/100.56036, Nana 13.74054/100.55543,
Phrom Phong 13.73043/100.56971, Sala Daeng 13.72857/100.53434,
MRT Huai Khwang 13.77869/100.57357, MRT Phra Ram 9 13.75782/100.56528.

**Overpass endpoint health (recorded honestly, it cost several retries):**
`overpass-api.de` → TLS reset from this machine (`SSL_ERROR_SYSCALL`);
`overpass.osm.jp` → **expired certificate** (curl exit 60); `overpass.osm.ch`
→ Switzerland-only (returns 0 elements for Bangkok — verified); `maps.mail.ru`
→ reachable but 504 "too busy" on most queries; working set =
**`overpass.private.coffee` + `overpass.kumi.systems`** (3–5 retries needed at
peak hours; base 2026-07-24). One stale-file trap was caught mid-session: a
failed curl left the previous query's JSON in place and the naive
`grep '"elements"'` check passed on stale data — the Huai Khwang numbers below
are from the post-fix re-run (`huaikhwang2.json`).

## 2. The zone list (verified anchors, proposed geofence)

Zone centers/radii are **proposals** tuned to the verified cluster extents;
khet is measured (§1), not assumed. `dist to station area` = distance from
zone center to the nearest station-area anchor in
`app/src/data/bangkok/stations.json`.

| # | Zone (id) | Center (lat, lng) | r, m | Khet (measured) | Nearest station area | Wikidata | OSM anchor |
|---|---|---|---|---|---|---|---|
| 1 | `soi-cowboy` | 13.7376, 100.5621 | 250 | **watthana** (ask said Khlong Toei — not supported) | asok, 198 m | Q1343629 | way 156261355 `highway=pedestrian` "Soi Cowboy / ซอยคาวบอย" |
| 2 | `nana-plaza` | 13.7414, 100.5533 | 250 | **khlong-toei** salient at the Watthana border (ask said Watthana/Ratchathewi junction — Ratchathewi is not adjacent) | nana, 249 m | Q441839 | way 1491550445 `landuse=retail` polygon, `wikidata=Q441839` |
| 3 | `patpong` | 13.7286, 100.5329 | 250 | bang-rak ✓ | sala-daeng, 167 m | Q2057014 | ways 707972260 "Patpong 1 Road", 231413630/1185517313 "Thanon Phat Phong 2" |
| 4 | `huai-khwang-ratchada` | 13.7789, 100.5735 | 450 | **straddles din-daeng (S half incl. MRT station) and huai-khwang (N half)** | huai-khwang, 24 m | — (none found) | — (no named way; only venue nodes) |
| 5 | `sukhumvit-soi-33` | 13.7332, 100.5682 | 300 | watthana | phrom-phong, 348 m | — (none found) | — |
| 6 | `rca` (contrast) | 13.7498, 100.5759 | 500 | huai-khwang | phetchaburi 1350 m / phra-ram-9 1452 m — **no rail anchor** | Q6648577 | ways "ถนนอาร์ซีเอ / Royal City Avenue" (residential), e.g. 667610247 |

Per-zone justification, one paragraph each:

1. **Soi Cowboy** — Sukhumvit Soi 21 (Asok Montri), a ~300 m strip between
   Sukhumvit Rd and Phetchaburi Rd. OSM maps the strip itself as a
   pedestrian way (13.73701, 100.56214) with the go-go bars as
   `amenity=bar/nightclub` nodes along it (Cactus 13.73692,100.56211 verified).
   39 bar+pub and 3 nightclub nodes in the bbox — the densest nightlife
   corridor in the Asok area.
2. **Nana Plaza** — inside Sukhumvit Soi 4, ~250 m NW of BTS Nana. The plaza
   is a real OSM polygon (7 nodes, bbox 13.74102–13.74177 ×
   100.55302–100.55360, ~85 × 65 m) tagged `landuse=retail`, name
   en/ja/th/ar, `alt_name="Nana Entertainment Plaza)"` (sic — stray paren in
   OSM), `wikidata=Q441839`, `wikipedia=en:Nana Plaza`. Around it, the Soi 4
   hotel/guesthouse strip: 49 bar+pub (highest of the six zones) — Badshah,
   Hillary 2, King Indian Night Club tagged `amenity=nightclub`.
3. **Patpong** — Patpong 1 & 2 between Silom and Suriwongse Roads, 170 m from
   Sala Daeng interchange. Both soi are named OSM ways ("Patpong 1 Road"
   way 707972260). 36 bar+pub + 4 nightclub; the Patpong Museum node
   (13.72878, 100.53214) anchors the block. Khet = Bang Rak ✓ (as in the ask).
4. **Huai Khwang / Ratchadaphisek Soi 4–8** — the strip hugging the west side
   of Ratchadaphisek around MRT Huai Khwang (13.775–13.7815,
   100.5728–100.5744). **Under-mapped in OSM**: only 6 tagged elements
   (Emmanuelle + one more `amenity=nightclub`, Mansion 7, 3 `shop=massage`,
   2 bar+pub) while the strip in reality holds dozens of venues. Khet
   attribution is split (see table) — the zone must carry **both** districts
   (`districts: ["din-daeng", "huai-khwang"]`), or stay attributed to the
   station end (Din Daeng). The ask's "Huai Khwang" alone is imprecise.
5. **Sukhumvit Soi 33** — Soi 33/1–33/3 north of Sukhumvit, ~350 m NE of BTS
   Phrom Phong. The `shop=massage` cluster is real in OSM and the names make
   the character explicit (At Ease Massage 33/1, 7-Heaven, Hakumi **Nuru**
   Massage, Daisy Dream, aurora massage), plus the zone's single
   `shop=erotic` node (13.73202, 100.56776) — one of only **3** city-wide.
   Only 6 bar+pub: quiet street-level, parlour-based character — a different
   *kind* of zone from Soi Cowboy, same `kind` in the schema below.
6. **RCA (Royal City Avenue)** — Rama IX Road corridor, the contrast case:
   **14 `amenity=nightclub` (Route66, Slim, Flix, Led, Zeta, Sanook…), 0
   massage, 4 bar+pub.** A pure club district — loud late, but **not** an
   adult-entertainment zone and must never appear in a family filter. No
   rail: 1.35–1.45 km from both Phetchaburi/Makkasan and Phra Ram 9 station
   anchors, which matches its taxi-only reputation.

## 3. Wikidata

Verified via the API this session (labels en/ru/ja/th, P625, P31):

| Entity | QID | P31 | ru / ja label | P625 | Fit |
|---|---|---|---|---|---|
| Soi Cowboy | **Q1343629** | Q79007 street, Q1382472 soi | Сой Ковбой / ソイ・カウボーイ | 13.73681, 100.56250 | good |
| Nana Plaza | **Q441839** | Q17350442 venue | Нана Плаза / ナナ・プラザ | 13.74136, 100.55317 | good — matches the OSM way (§2) |
| Thanon Patpong | **Q2057014** | Q79007 street | — (no ru) / パッポン通り | 13.72833, 100.53333 | good |
| Royal City Avenue | **Q6648577** | Q123705 neighborhood | — (no ru, no ja) / อาร์ซีเอ (th) | 13.75000, 100.57694 | ok, imprecise (~±400 m vs the club cluster) |
| Kabukichō (Tokyo mirror) | **Q665216** | Q5327369 chōchō, **Q3055075 entertainment district**, **Q272888 red-light district** | Кабуки-тё / 歌舞伎町 | 35.69545, 139.70256 | mirror anchor for CRTKY-182 |
| Yoshiwara (Edo) | Q1859550 | — | — | — | historical entity only; the modern Tokyo district was not verified this session |

Notes for the mirror: Wikidata itself types Kabukichō with **both**
`entertainment district` and `red-light district` (Q272888) — the same
club-vs-adult ambiguity our `kind` field separates. Q2057014 and Q6648577
have **no Russian label**, so RU names must be hand-curated in
`static_data.py` (same situation as `RU_NAMES` for the 50 khets, which
exists for exactly this reason — see the header of
`scripts/bangkok/static_data.py`).

**License:** Wikidata data is CC0; OSM/Overpass data is ODbL (stated in every
response header). Both are license-clean for this repo; the curated static
list itself is our own hand data.

## 4. OSM corroboration — counts per zone (extract 2026-07-24)

Per-zone `out center tags` dumps (nodes+ways) over the bboxes of §2; bar+pub
via separate `out count`. Full per-element listings preserved in
`~/tmp_ov_redlight/<zone>.json`.

| Zone | stripclub | brothel | erotic | massage | nightclub | bar+pub |
|---|---|---|---|---|---|---|
| soi-cowboy | 0 | 0 | 0 | 12 | 3 | 39 |
| nana-plaza | 0 | 0 | 0 | 15 | 3 | 49 |
| patpong | 0 | 0 | 0 | 14 | 4 | 36 |
| huai-khwang-ratchada | 0 | 0 | 0 | 3 | 3 | 2 |
| sukhumvit-soi-33 | 0 | 0 | **1** | 8 | 0 | 6 |
| rca | 0 | 0 | 0 | **0** | **14** | 4 |
| **Σ zones** | 0 | 0 | 1 | **52** | **28** | 136 |
| Bangkok bbox (13.45–13.95, 100.30–100.85) | **0** | 1 | 3 | 445 | 91 | — |
| Thailand bbox | **0** | 8 | — | — | — | — |

Concentration math: the six bboxes total ≈ 3.15 km² = **0.096 %** of the
Bangkok bbox area, yet hold **31 % of all city `amenity=nightclub`** (≈320×
the average density) and **12 % of all `shop=massage`** (≈120×). RCA's
14-vs-0 massage split against Soi Cowboy/Nana's 27 massage vs 6 nightclubs is
the cleanest data signature of the club-district vs adult-zone contrast.

**Why OSM cannot be the derivation source:** `leisure=stripclub` is used
**zero times nationwide**, `amenity=brothel` 8 times in all Thailand
(1 in Bangkok — not in any of our six zones). The go-go bars are
`amenity=bar`/`nightclub`/untagged; `shop=massage` mixes ordinary spas with
adult parlours and must never be surfaced as an "adult" signal to users — it
is corroboration only. The zone list is therefore **curated common knowledge
pinned to verified coordinates** (this note), exactly the kind of
hand-maintained reference data `static_data.py` already carries (see its
header: RU_NAMES, LINES, CURATED_SEQUENCES, HUBS).

## 5. Format proposal — center + radius, static, shared with CRTKY-182

**Polygon vs disc:** only **1 of 6** zones has a real zone polygon in OSM
(Nana Plaza, 85 × 65 m — covers the plaza, not the Soi 4 strip); Soi Cowboy
is a *line* (pedestrian way), Patpong is two parallel street ways, RCA is a
road corridor, Soi 33 / Huai Khwang are point clusters. Polygons would be
per-zone bespoke geometry with unbounded maintenance (venue churn) and false
precision. **Recommend `center + radius_m`** as the canonical format: it
honesty-matches "zone level", drops straight into the existing per-point grid
machinery (the 200 m grid builder already computes distances per point), and
transfers to Tokyo where Kabukichō et al. likewise lack zone polygons. Keep
the OSM way id as **provenance**, never as geometry.

Proposed shape in `scripts/bangkok/static_data.py` (mirrors the existing
hand-curated dicts):

```python
# Nightlife zones — curated geofence (CRTKY-153). Zone-level, not venues.
# kind: "adult_entertainment" (family filter applies) | "club_district"
# (nightlife fact only). khet attribution measured against the pipeline's
# OSM admin_level=6 polygons, 2026-10-13; see research/bangkok/notes/
# 2026-10-13-redlight-crtky153.md.
NIGHTLIFE_ZONES: list[dict] = [
    {
        "id": "soi-cowboy",
        "kind": "adult_entertainment",
        "lat": 13.7376, "lng": 100.5621, "radius_m": 250,
        "districts": ["watthana"],
        "wikidata": "Q1343629",
        "osm_way": 156261355,           # provenance, not geometry
        "verified": "2026-10-13",
    },
    {"id": "nana-plaza", "kind": "adult_entertainment", "lat": 13.7414,
     "lng": 100.5533, "radius_m": 250, "districts": ["khlong-toei"],
     "wikidata": "Q441839", "osm_way": 1491550445, "verified": "2026-10-13"},
    {"id": "patpong", "kind": "adult_entertainment", "lat": 13.7286,
     "lng": 100.5329, "radius_m": 250, "districts": ["bang-rak"],
     "wikidata": "Q2057014", "osm_way": 707972260, "verified": "2026-10-13"},
    {"id": "huai-khwang-ratchada", "kind": "adult_entertainment",
     "lat": 13.7789, "lng": 100.5735, "radius_m": 450,
     "districts": ["din-daeng", "huai-khwang"],
     "wikidata": None, "osm_way": None, "verified": "2026-10-13"},
    {"id": "sukhumvit-soi-33", "kind": "adult_entertainment",
     "lat": 13.7332, "lng": 100.5682, "radius_m": 300,
     "districts": ["watthana"], "wikidata": None, "osm_way": None,
     "verified": "2026-10-13"},
    {"id": "rca", "kind": "club_district", "lat": 13.7498,
     "lng": 100.5759, "radius_m": 500, "districts": ["huai-khwang"],
     "wikidata": "Q6648577", "osm_way": 667610247, "verified": "2026-10-13"},
]
```

Shared schema with the Tokyo mirror (CRTKY-182, 歌舞伎町 etc.): identical
fields; Tokyo entries would be e.g. `{"id": "kabukicho",
"kind": "club_district", "wikidata": "Q665216", …}` and the Yoshiwara
(Taito) adult zone the mirror's owner curates — the `kind` field is what
keeps "nightlife is great here" and "family filter applies" from colliding in
both cities. Display names should come from Wikidata labels where present
(soi-cowboy: ja ソイ・カウボーイ, ru Сой Ковбой) with hand-curated RU/JA for
the rest (Q2057014/Q6648577 have no ru/ja labels); RCA's ja "アールシーエー
（RCA）" is a proposal, not a verified label. Radii on RCA cover 12–13 of the
14 tagged clubs (the easternmost, 13.74677/100.58149, sits ~660 m out — fine
for a zone flag; widen to 550 m if the owner prefers full coverage).

## 6. Product recommendation — fact + optional family chip, no new subsignal

1. **Adopt as a static fact** (this list). Do **not** feed it into the
   nightlife score: the existing nightlife category already rewards density
   and rates Soi Cowboy, Nana and RCA equally high — that is correct for
   "nightlife", and blurring an adult-zone flag into it (a "subsignal")
   would quietly punish districts for a property users may not care about.
2. **Family filter chip** is the one consumer that needs geofence semantics:
   a hard dealbreaker toggle ("avoid adult-entertainment zones") excluding
   grid cells / station areas / districts whose center or covered cells fall
   inside any `kind="adult_entertainment"` disc. RCA (`club_district`) never
   triggers it. This matches the existing dealbreaker-filter model (hard
   per-category minimums) rather than the soft persona weights.
3. **Prose** (descriptions): mention zone proximity as a neutral trade-off
   where it is true and near (≤ ~800 m), at street level, never venue
   lists/counts. The grid map should **not** draw zone outlines (stigma +
   precision we do not have); the flag lives in filter and text.

Suggested neutral wording (aligns with `research/bangkok/description-rules.md`
hard rules: facts over flair, no dramatising, plain text):

| Concept | EN | JA | RU |
|---|---|---|---|
| The zone type | "adult entertainment area" | 「大人向けの歓楽街」 | «зона развлечений для взрослых» |
| Filter chip | "Avoid adult entertainment areas" | 「大人向けの歓楽街を避ける」 | «Вдали от зон развлечений для взрослых» |
| Proximity in prose | "Soi Cowboy's late-night strip is a few minutes' walk" | 「ソイ・カウボーイの夜の歓楽街が徒歩数分」 | «Ночной Сой Ковбой — в нескольких минутах пешком» |
| RCA (contrast) | "club district, loud after dark" | 「クラブ街、夜遅くまでにぎやか」 | «клубный район, шумно допоздна» |

Rules to pin in the description guide: never "red-light district" in UI copy
(loaded; factually wrong for RCA; JA/RU equivalents likewise avoided);
name streets, not venues; no venue counts; RCA is described as a club
district only; the same wording rules apply to the Tokyo mirror (歌舞伎町 is
「歓楽街」 in JA copy — the standard neutral word).

## 7. Adopt / reject per source

| Source | Verdict | Why |
|---|---|---|
| Curated static list in `static_data.py` (this note's six zones) | **adopt** | only honest derivation-free source; matches repo precedent for hand data |
| OSM Overpass counts (mirrors, base 2026-07-24) | **adopt, corroboration only** | nightclub/massage density + named ways confirm the zones; sensitive tags absent in Thailand |
| OSM polygons (Nana Plaza way) | **adopt as provenance** | real polygon exists but covers only the plaza; discs stay canonical |
| Wikidata | **adopt for ids/labels**, **reject for coordinates** | P625 imprecise (RCA ~±400 m); ru/ja labels missing on 2 of 5 entities |
| Pipeline `geometry.json` + `stations.json` | **adopt** | khet attribution and station anchors must come from the same data the product shows |
| OSM as zone *derivation* source | **reject** | 0 stripclub nationwide, 1 brothel in Bangkok — nothing to derive from |

## 8. Open questions for the owner

1. Approve the six-zone set, the radii (§2) and the `kind` taxonomy; is RCA
   in scope as a `club_district` fact (recommended) or out of scope for
   CRTKY-153?
2. Family chip: hard dealbreaker (recommended) or soft toggle? Exact
   EN/JA/RU copy (§6 proposals need sign-off) and whether districts/station
   areas also get the flag or only grid cells.
3. Cell semantics for the filter: cell center inside the disc (cheap,
   recommended) vs any overlap (flag leaks one cell further).
4. CRTKY-182: confirm the shared schema + `kind` field with the Tokyo side
   before either side ships; who curates Yoshiwara/Roppongi equivalents?
5. Corroboration refresh cadence — re-run the §4 counts yearly against a
   current mirror base (today's numbers are from the 2026-07-24 extract).
6. Not checked this session: whether Overture Places has a usable category
   for secondary corroboration (the pipeline already ingests Overture for
   nightlife — worth one probe before implementation).

Sources: Wikidata API (`wbsearchentities`, `wbgetentities` for
Q1343629, Q441839, Q2057014, Q6648577, Q665216, Q1859550 + class labels);
Overpass mirrors `overpass.private.coffee` / `overpass.kumi.systems` (base
2026-07-24; probes of `overpass-api.de`, `maps.mail.ru`, `overpass.osm.jp`,
`overpass.osm.ch` recorded in §1); repo data `app/src/data/bangkok/geometry.json`,
`app/src/data/bangkok/stations.json`, `scripts/bangkok/static_data.py`;
`research/bangkok/00-overview.md`, `research/bangkok/description-rules.md`,
`CLAUDE.md`. All fetched/read 2026-10-13 as described above.
