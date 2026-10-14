# Tokyo institutions — embassies, English-speaking medicine, international schools, coworking, libraries (CRTKY-180)

Researched: **2026-10-13**, by the open-data research agent. Method re-used from
the Bangkok wave-2 precedent (`research/bangkok/notes/2026-10-13-institutions-crtky145.md`):
live Overpass + Wikidata SPARQL, fact-block pattern, two-source rule for every
adopted class. All fetches below were run by me in this session; commands and
outputs are quoted (Appendix). Nothing here is an implementation decision — the
owner adopts sources.

**TL;DR:** **Embassies are the strongest find, stronger than Bangkok's**: OSM
carries **169** `office=diplomatic` POIs (→ **166** unique missions after
name+120 m dedupe), Wikidata carries **145** items with `P159 → 東京都` (only
**1** has `P625` — same quirk as Bangkok), **113** match directly by `wikidata`
tag and **144/166** match by QID-or-country-name → two-source rule satisfied
abundantly. The Roppongi/Akasaka/Hiroo cluster is now numeric: wards
**Minato 91, Shibuya 20, Chiyoda 16, Meguro 14, Shinagawa 12**; station 800 m
catchments **hiroo 40, azabu-juban 27, kamiyacho 22, akabanebashi 20,
roppongi-itchome 20** (86/1493 stations have ≥1). English-speaking medicine has
a real public directory: the **JNTO "Guide for when you are feeling ill"**
search returns **508** English-service Tokyo institutions (55 hospitals,
~305 clinics, 148 dental; geocoded lat/lng in the JSON), cross-checked by
**JMIP** accreditation (**11** Tokyo hospitals of **68** nationwide) — but both
are **© copyright, citation-only**. International schools: OSM name-match is
**14** (in-Tokyo, deduped) vs **19** Wikipedia-notable vs **64** (International
Schools Database) → OSM undercounts ≥50 %, curation required. Coworking:
**reject** (OSM 26 POIs, zero chain brands, vs WeWork's ~30 Tokyo locations
alone). Current product carries the embassy character only as hand-written
prose in **9** of 1502 station descriptions (`data/descriptions/*.json`) —
no rating signal touches institutions (`scripts/compute-ratings.py` keys:
crowd, daily_essentials, food, green, gym, nightlife, rent, safety, transport,
vibe). Recommendation: **fact blocks on station pages, not a new rating key** — §9.

---

## 1. What was checked and how (verification log)

| # | What | Command (abridged) | Result |
|---|------|--------------------|--------|
| 1 | Overpass institutions, ask's bbox `35.5,139.2,36.0,139.9` | POST `[out:json][bbox:35.5,139.2,36.0,139.9];(nwr["office"="diplomatic"];nwr["diplomatic"];nwr["amenity"="coworking_space"];nwr["amenity"="library"];nwr["amenity"="hospital"];nwr["healthcare"="hospital"];);out center tags;` | 200 via `overpass.private.coffee` (kumi 504×2 first), **2111 elements**, base snapshot `2026-05-06T03:25Z` |
| 2 | Overpass schools + banks, same bbox | `(nwr["amenity"="school"]; nwr["amenity"="bank"];)` | 200 via kumi (retry), **7157 elements**, base `2026-05-06T03:25Z` |
| 3 | Overpass special-ward boundaries | `relation["admin_level"="7"]["boundary"="administrative"];out geom;` | 200 via kumi (504×4 retry), **107 relations**, 23 with member-way geometry; base `2026-07-15` |
| 4 | Wikidata SPARQL, embassies | `?item wdt:P31 wd:Q3917681 . { ?item wdt:P159 wd:Q1490 } UNION { ?item wdt:P159 ?hq . ?hq wdt:P131 wd:Q1490 }` | 200, **145 unique items** → `/tmp/crtky180-wd-p159.json`. First combined attempt (P131\* + `around` service in one query) → **504 gateway timeout**; split queries worked. `wikibase:around` (radius 25 km) returned **1** embassy with P625 (same P625-less model as Bangkok). `?item wdt:P131 ?loc . ?loc wdt:P131 wd:Q1490` → **0 rows**: embassy items have **no ward-level P131** |
| 5 | Ward PIP sanity | even-odd ray-casting over stitched member-way rings | **23/23** ward centroids (from `scripts/build-station-ward-map.mjs:12-36`) fall inside their own polygon |
| 6 | Station catchments | haversine ≤ 800 m per station (`data/stations.json`, 1493) | embassy counts §3.2; the repo's Tokyo catchment convention is 800 m (`scripts/compute-ratings.py:426-429`) |
| 7 | JNTO medical list | POST `https://www.jnto.go.jp/emergency/search.php?<rand>` body `cb-area=a08_tokyo…` (endpoint reverse-engineered from `../search.js`) | 200 JSON, **508 Tokyo rows** with lat/lng |
| 8 | JMIP accredited search | GET `jmip.jme.or.jp/search.php?prefectures=13&mode=search` (+`&c=2`) | **11 件該当** Tokyo (11 named); empty prefecture → **68 件** nationwide |
| 9 | Licenses/terms | fetch `jmip.jme.or.jp/site.php`, JNTO page footer, `himawari` domains | JMIP: 「当サイトに掲載されるすべての情報は、当財団が著作権を保有し…複製、改変、配布等を含む…禁止」; JNTO guide footer: `Copyright © Japan Tourism Agency. All Rights Reserved.` — both **no open licence** |
| 10 | Prose coverage | `grep -rl "embass\|大使館" data/descriptions/` | **9 files** of 1502 mention embassies (roppongi-itchome, hanzomon, hiroo, aoyama-itchome, akabanebashi…) |

**Bbox caveat.** The ask's bbox (35.5–36.0 N / 139.2–139.9 E) covers all 23
special wards plus outer Tokyo, Saitama, Kawasaki, Yokohama-north and west
Chiba. The station set is wider still (34.98–36.25 N). Class counts below are
in-bbox; ward tables are inside the 23 special wards only (PIP against
admin_level=7 rings); "outside" rows in §2 are non-23-ward parts of the bbox
(Saitama/Kanagawa/Chiba) — they exist because the bbox is square, not because
Tokyo institutions are there.

## 2. Raw counts (Overpass, in-bbox; base snapshot 2026-05-06)

| Class | Tag(s) | In bbox | In 23 wards | Named | Notes |
|---|---|---:|---:|---:|---|
| Diplomatic | `office=diplomatic` (+`diplomatic=*`) | **169** | 167 | 167 | 162 `diplomatic=embassy`, 4 consulate, 1 liaison, 2 unspecified; **136/169 carry a `wikidata` tag**; dedupe (same name, <120 m) → **166 unique** |
| Coworking | `amenity=coworking_space` | **26** | 20 | 25 | all small independents/self-study rooms; **zero WeWork/Regus/JustCo** |
| Libraries | `amenity=library` | 674 | 310 | 652 | metro (都立中央/多摩) + ward libraries + a few mis-tags |
| Hospitals | `amenity=hospital` / `healthcare=hospital` | 1242 | 401 | 1201 | 841 "outside 23 wards" — mostly mis-tagged clinics in Saitama/Kanagawa (Bangkok saw the same pattern) |
| Schools | `amenity=school` | 4972 | — | 4703 | incl. 私立/区立/県立 mix |
| — name~"international" | name contains | **17 rows** | **14 in Tokyo** (13 unique after India-Intl ×2 dup) | — | misses schools without the word (see §5) |
| Banks | `amenity=bank` | 2174 | — | — | branch density proxy only, not researched further |

## 3. Embassies — the flagship class

### 3.1 Two-source rule (satisfied)

- **OSM**: 169 POIs → 166 unique missions; 167 named. Real current missions:
  "Embassy of the United States", "Embassy of New Zealand", 駐日タンザニア連合共和国大使館…,
  plus non-embassy diplomatic units (Delegation of the European Union,
  Apostolic Nunciature ローマ法王庁大使館, Peru/Brazil Consulates-General,
  Hong Kong Trade Representative Office) and one data typo ("Emnassy of
  Botswana").
- **Wikidata**: 145 items `P31=Q3917681` + `P159→Q1490` (58 carry a ward-level
  P159 value — Minato 35, Chiyoda 6, Shibuya 6, Setagaya 4, Shinagawa 3,
  Tokyo 2, Shinjuku 2); exactly **1** item carries P625 — coordinates must come
  from OSM, WD verifies existence only (identical to the Bangkok finding).
- **Match**: **113** OSM POIs ↔ WD items via the `wikidata` tag alone; adding
  country-name matching (normalised "Embassy of X" / 駐日X大使館) → **144/166**
  OSM unique missions matched to a WD item. Unmatched OSM residue = consular
  sections, ambassador residences, EU Delegation, Holy See; unmatched WD
  residue includes the defunct **Q12129510 Embassy of Manchukuo** (WD noise to
  exclude on adoption).

### 3.2 Cluster made numeric

**By special ward** (166 unique OSM missions, PIP):

| ward | OSM missions | WD P159 ward label (of 58 ward-resolvable items) |
|---|---:|---:|
| **Minato (港区)** | **91** | **35** |
| Shibuya (渋谷区) | 20 | 6 |
| Chiyoda (千代田区) | 16 | 6 |
| Meguro (目黒区) | 14 | — |
| Shinagawa (品川区) | 12 | 3 |
| Setagaya (世田谷区) | 6 | 4 |
| Shinjuku (新宿区) | 3 | 2 |
| Chuo 2 · Taito 1 · Bunkyo 1 | 4 | — |

WD's ward-resolvable subset (58/145 items have P159 = a ward) reproduces the
same Minato-first ordering — the two sources corroborate at ward level, OSM is
the geolocating source.

**By station catchment (800 m disc, all 1493 stations):**

| Station | embassies | note |
|---|---:|---|
| **hiroo** | **40** | the Hiroo/Azabu embassy belt |
| azabu-juban | 27 | |
| kamiyacho | 22 | Akasaka/Toranomon belt |
| akabanebashi | 20 | |
| roppongi-itchome | 20 | |
| hanzomon | 12 | British Embassy etc. |
| roppongi | 11 | |
| kojimachi | 10 | |
| takanawa-dai 9 · akasaka 8 · toranomon 8 · gotanda 8 | 8–9 | gotanda's 8 are real: Peru/Brazil Consulates-General, Indonesian, Belarus, Thai (Shinagawa), Tajikistan, North Macedonia, Brunei — spot-checked by name |
| ichigaya, meguro, tameike-sanno 7 · kamiizumi, kokkai-gijidomae, shibakoen 6 | 6–7 | |

**86 of 1493 stations** have ≥1 embassy in catchment — the signal is
concentrated (like Bangkok's 19-POI Phloen Chit, but here 40).

## 4. English-speaking medicine — the ask's directories, resolved

| Source | What it actually is today (checked 2026-10-13) | Licence |
|---|---|---|
| **JNTO "Guide for when you are feeling ill"** (https://www.jnto.go.jp/emergency/eng/mi_guide.html) | Live searchable registry of **English-service medical institutions**; POST endpoint `search.php` returns JSON with `medical_institution`, address, phone, reception_time, **latitude/longitude**, `emergency_response`, `jmip` flag. Tokyo = **508 rows**: 55 hospitals, ~305 clinics/other, 148 dental; 44 with emergency_response; **13 flagged JMIP** | Footer: `Copyright © Japan Tourism Agency. All Rights Reserved.` → **citation only**, no bulk reuse |
| **JMIP** — Japan Medical Services Accreditation for International Patients (https://jmip.jme.or.jp) | The accreditation system the ask meant (運営: 一般財団法人日本医療教育財団, from a 2011 MHLW project). Public search: **Tokyo 11** (Toranomon, NTT Kanto, Nissan Tamagawa, Tokyo Metropolitan Hiroo, Tokyo Metropolitan Bokutoh, Tokyo Metropolitan Tama MC, NCGM, Kyorin Suginami, Tokyo Saiseikai Central, NCNP Kodaira, Tokyo Hikifune), **nationwide 68** | `site.php`: 「複製、改変、配布等を含む…事前に当財団から許可を得た場合を除いて禁止」 → **citation only** |
| **himawari / 東京保健医療情報ネットワーク** (TMG) | The TMG directory is now a **multilingual phone service** (03-5285-8181, EN/CN/KR/TH/ES, 9–20 daily, per https://www.hokeniryo.metro.tokyo.lg.jp search hit and the TMG bureau page fetched 200 today). The old web-search domains `himawari.metro.tokyo.lg.jp` and `himawari.hospital-net.or.jp` **do not resolve from this environment** (curl DNS error) — I could not verify any web directory behind them. **Not confirmed as a usable data source.** | — |
| internationalpatients.jp (外国人患者受入れ情報サイト) | MHLW-subsidized meta-directory (運営 メディフォン株式会社) linking JMIP search, MEJ hospital list and JNTO — good entry point, no countable data of its own | not fetched beyond the page |

**Cross-check between the two countable sources**: 10 of the 11 JMIP-site
Tokyo hospitals appear in the JNTO Tokyo set with the `jmip` flag set (JNTO
flags 13 — 2–3 extra, e.g. Tokyo Nishi Tokushukai — a data-vintage difference,
harmless at fact-block granularity). The JNTO list is **geocoded**, so a
curated "English medicine" overlay maps onto station catchments without
address geocoding.

## 5. International schools — OSM alone undercounts ≥50 %

- OSM `amenity=school`, name~"international": 17 rows bbox, **14 in Tokyo**,
  13 unique (KAIS, Clarence, Ivy Prep, Willowbrook, Seven Seas, Camelot,
  Aoba-Japan Hikarigaoka, Salesian, St. Mary's, MITA, Seisen, K. International
  Tokyo, India International ×2 dup).
- Marquee presence check in OSM: present = ASIJ (Chofu), Aoba, Christian
  Academy in Japan, Sacred Heart (Hiroo), British School (Shibuya campus),
  St. Mary's, Seisen, K. International, Tokyo Chinese School, Tokyo Korean
  School; **absent = Nishimachi, Lycée Français International de Tokyo,
  Tokyo International School (Hiroo), Canadian International School, GIIS,
  Laurus, Tokyo West** — the biggest expat-facing names are missing or
  non-`school`-tagged.
- Second sources: **Wikipedia "List of international schools in Japan" →
  Tokyo section = 19** (article-linked, i.e. a conservative notable set;
  fetched 2026-10-13); **International Schools Database → "There are 64
  international schools in Tokyo"** (page fetched 2026-10-13; commercial
  directory). OSM contains roughly **9–10 of the 19** notable schools →
  undercount ≥50 %, the same failure mode as Bangkok (where OSM missed ~40 %).
- Verdict: counts must come from a **curated overlay** (Wikipedia 19 +
  ISDB-style names), geolocated against OSM/coordinates; raw OSM name-match is
  not a usable signal. Per-station numbers are tiny anyway (max 2: hiroo,
  yoga) — this class is a fact line, never a rating axis.

## 6. Coworking — reject (same verdict as Bangkok)

- OSM `amenity=coworking_space`: **26** in bbox / **20** in 23 wards. Names
  are small independents and self-study rooms (Hub Tokyo, SENQ霞ヶ関, 3×3 Lab
  Future, 自習室 at home…); **zero** WeWork/Regus/JustCo locations.
- Reality: WeWork alone lists **~30 Tokyo locations** (wework.co.jp location
  page; third-party 2025–26 guides say 30 in Tokyo, 43–44 Japan-wide). IWG
  (Regus/Spaces) adds tens more. OSM coverage <10 %.
- If coworking is ever surfaced, it is a hand-maintained chain list with an
  `updated:` stamp, not an OSM count.

## 7. Libraries and branches (библиотеки/отделения)

- `amenity=library`: **674** in bbox, **310** inside the 23 wards; ward
  leaders: Setagaya 26, Shinjuku 21, Bunkyo 18, Chiyoda 15, Shinagawa 14,
  Minato 13. Tokyo's ward-library system is dense enough to be a legitimate
  daily-essentials fact line, and it is already ODbL — but it overlaps what
  `daily_essentials` measures (or could, without a new source).
- `amenity=bank` branches: 2174 in bbox (no ward split computed). Branch
  density is a service-convenience proxy already covered by
  `daily_essentials`/`convenience` — adding it as a separate signal would
  double-count. Cultural-institute branches (Italian Institute of Culture
  appeared inside `office=diplomatic`) are rare, <10 city-wide; not a signal.

## 8. Is the embassy character in the product today?

**Prose yes, data no — 9 of 1502 station description files mention embassies**
(`data/descriptions/`: roppongi-itchome "Embassy-office Roppongi…", hanzomon
"British Embassy nearby", hiroo "Embassy belt, expat groceries",
aoyama-itchome, akabanebashi, …). `grep -rin "embass\|diplomat\|international
school\|coworking" scripts/compute-ratings.py app/src/lib/types.ts` → no
signal, no rating key touches institutions. Tokyo rating keys today:
crowd, daily_essentials, food, green, gym, nightlife, rent, safety, transport,
vibe (`scripts/compute-ratings.py:314+`). So the measured fact "hiroo
catchment = 40 embassies" is genuinely new content, exactly as in Bangkok.

## 9. Composition proposal (owner decision)

1. **Not a new category.** Embassies exist near 86/1493 stations (~6 %),
   international schools near ~20 — a 12th percentile key would be noise for
   94 % of stations. Same reasoning as CRTKY-145 §7.
2. **Fact blocks on station pages (recommended).** One Overpass pass + one WD
   check + a curated overlay; per-station facts:
   - `embassies` (count + top countries) — **strong** (two-source: OSM↔WD 144/166);
   - `english_medicine` — JNTO count within 800 m (geocoded rows make this a
     pure distance join) + `jmip_accredited` boolean/label where applicable —
     **moderate-to-strong** (JNTO↔JMIP cross-check, both © so **cite, don't
     copy**; store the count, link the source);
   - `international_schools` — curated overlay (19 Wikipedia + directory
     names), **moderate**;
   - optional `libraries` line from OSM, **strong** but low-value.
3. **Boosts: no.** An embassy term in `vibe` would re-rank ~20 central
   stations and contradict the two-source confidence rule vibe lives under
   (per-district assignment is OSM-only). The Bangkok precedent's argument
   holds verbatim.
4. **Manual/curated lists** (JMIP hospital names, int'l school overlay,
   coworking chains if ever) live in repo data files with citation URLs and
   `updated:` stamps — the copyright terms of JNTO/JMIP prohibit republication
   of the lists themselves; counts and links are fine.

## 10. Adopt / reject summary

| Source | Role | Verdict | Confidence if adopted |
|---|---|---|---|
| OSM `office=diplomatic` (Overpass) | embassy counts per ward / 800 m catchment | **adopt** | strong (WD overlap 144/166) |
| Wikidata SPARQL `P31=Q3917681`+`P159→Q1490` | embassy cross-check, CC0 | **adopt** (existence; wards via P159 labels for 58 items) | — |
| JNTO guide JSON (508 Tokyo, geocoded) | English-medicine counts + mapping | **adopt as cited snapshot** (© Japan Tourism Agency — count+link, no republication) | moderate-strong |
| JMIP accreditation search (11 Tokyo / 68 JP) | international-hospital tier | **adopt as curated cited list** (© 日本医療教育財団) | editorial |
| himawari (TMG) | the ask's TMG list | **not confirmed** — phone service only; web directory unresolvable from this environment | — |
| OSM schools + name heuristic | int'l schools | **adopt only via curated overlay**; raw name-match rejected | moderate (≥50 % undercount) |
| Wikipedia list (19) / ISDB (64) | school cross-check | Wikipedia **adopt as reference** (CC BY-SA), ISDB **reference only** (commercial) | — |
| OSM `amenity=coworking_space` | coworking | **reject** (26 POIs, 0 chains) | — |
| OSM `amenity=library` | libraries fact line | **adopt, optional** | strong but low-value |
| OSM `amenity=bank` | branch density | **reject** (covered by daily_essentials) | — |

## 11. Open questions

1. Fact blocks at station level (recommended; hiroo 40 is the headline) or
   ward level only? Which classes make the cut — embassies + English medicine,
   schools optional?
2. English-medicine counts: snapshot JNTO JSON into repo data (with © notice
   and link) at ingest time, or fetch at build time? Refresh cadence — the
   list is self-reported by institutions and undated.
3. JMIP/JNTO disagree by 2–3 hospitals on the accredited set — which vintage
   wins for the `jmip` fact?
4. WD noise: defunct items (Manchukuo) must be excluded on adoption — owner
   sign-off that a hand-exclusion list is acceptable.
5. Should `libraries` be added to `daily_essentials` instead of a new fact?
6. Coworking: confirm reject, or maintain a chain list later (WeWork ~30 +
   Regus/Spaces) as pure editorial content?

## Appendix — exact commands run this session (2026-10-13)

```
# Overpass (mirror rotation: kumi 504/429s → private.coffee OK → kumi OK)
python3 /tmp/crtky180_fetch.py
#   POST [out:json][timeout:250][bbox:35.5,139.2,36.0,139.9];
#   (nwr["office"="diplomatic"]; nwr["diplomatic"]; nwr["amenity"="coworking_space"];
#    nwr["amenity"="library"]; nwr["amenity"="hospital"]; nwr["healthcare"="hospital"];);
#   out center tags;                                   → 2111 els  (base 2026-05-06)
#   relation["admin_level"="7"]["boundary"="administrative"]; out geom;
#                                                      → 107 rels  (base 2026-07-15)
#   (nwr["amenity"="school"]; nwr["amenity"="bank"];); out center tags;
#                                                      → 7157 els  (base 2026-05-06)
# Wikidata
python3 /tmp/crtky180_wd.py
#   SELECT … ?item wdt:P31 wd:Q3917681 . { ?item wdt:P159 wd:Q1490 }
#   UNION { ?item wdt:P159 ?hq . ?hq wdt:P131 wd:Q1490 }               → 145 items
#   (combined P131*/around attempt → 504; around-only → 1 item with P625; P131→ward → 0)
# Analysis (ring stitching, even-odd PIP, 23/23 centroid sanity, haversine 800 m)
python3 /tmp/crtky180_analyze.py /tmp/crtky180_match.py /tmp/crtky180_final.py
# JNTO
curl https://www.jnto.go.jp/emergency/eng/mi_guide.html                       # 200
curl https://www.jnto.go.jp/emergency/search.js                               # 200 (endpoint)
python3  # POST search.php?…  cb-area=a08_tokyo                               # 508 Tokyo rows
# JMIP
curl "https://jmip.jme.or.jp/search.php?prefectures=13&mode=search" (+&c=2)   # 11 件 Tokyo
curl "https://jmip.jme.or.jp/search.php?mode=search"                          # 68 件 nationwide
curl http://jmip.jme.or.jp/site.php                                           # terms: ©, no reuse
# TMG / himawari
curl https://himawari.hospital-net.or.jp/            # DNS fail (also .metro.tokyo.lg.jp)
curl https://www.hokeniryo.metro.tokyo.lg.jp/        # 200 (TMG bureau, himawari = phone)
# Schools / coworking cross-checks
curl https://en.wikipedia.org/wiki/List_of_international_schools_in_Japan     # Tokyo section = 19
WebFetch https://www.international-schools-database.com/in/tokyo               # "64 international schools"
WebSearch WeWork Tokyo locations                                              # ~30 Tokyo (wework.co.jp)
# Repo coverage
grep -rl "embass\|大使館" data/descriptions/     # 9 of 1502 files
```

Data files stayed in /tmp; the only file created in the repo is this note.
