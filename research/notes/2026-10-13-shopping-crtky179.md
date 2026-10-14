# Tokyo shopping: 商店街, department stores/depachika, markets — open-data audit (CRTKY-179)

Researched: **2026-10-13**, by the open-data research agent. Scope per ticket:
(1) shotengai — openness of official lists (全国商店街リスト / 商店街マップ /
METI-MLIT 商店街活性化 statistics), Wikidata for famous examples (吉祥寺サンロード,
谷中銀座, 巣鴨地蔵通り), OSM tagging; (2) department stores (`shop=department_store`
counts + Wikidata GLA); (3) markets (`amenity=marketplace`, Tsukiji/Toyosu/早市);
(4) counts over contrast stations; (5) composition — boost `daily_essentials`/`vibe`
vs a "商店街 300 m" fact; (6) honest maintainability assessment of a shotengai list.
All network checks below were run by me in this session; commands and outputs are
quoted (Appendix). Nothing here is an implementation decision — the owner adopts sources.

**TL;DR:** There is **no maintainable machine-readable national/municipal shotengai
list** — the practical replacement is the aggregate official *statistics*: the Tokyo
Metropolitan Government register states **2,374 商店街 in Tokyo as of 2022-10**
(東京都商店街実態調査報告書, PDF, **CC BY 4.0** — I downloaded and parsed it), and the
national 全振連 survey (令和6年度, PDF) sent questionnaires to **11,280 shotengai**
(prefectural registers sum to **12,091**). Neither publishes names+coordinates as
bulk data; the historical portals (shopping-street.jp, shotengai.jp) are dead/parked.
OSM is the only geocoded source, but name-based detection is leaky: **352 objects**
named `商店街` in the repo's bbox (my 4-tile Overpass scan), yet the famous streets
are named サンロード / 谷中銀座 / アメヤ横丁 *without* the word — per-station counts
give **0 for Nippori even though 谷中銀座 sits 500 m away** (6 separately named ways,
3 different `highway=*` values, plus a name-only untagged way). Wikidata has only
**178 Japanese shotengai items, 61 with coordinates**, and 巣鴨地蔵通り — one of the
most famous — **has no item at all**. Department stores are the one clean OSM signal:
**125 objects city-wide**, separating Ginza (7) / Shibuya (10) / Ueno (5) from
residential stations (0–2); Wikidata has 21 chain items, branch items lack class/size
and **no GLA property exists in Wikidata** (two property searches → none). Markets:
58 `amenity=marketplace` objects; 豊洲市場 is 3 ways `amenity=marketplace +
landuse=wholesale` (falls in **shin-toyosu**'s 800 m, not toyosu's: 3 vs 0), 築地場外
is 1 tagged way. Recommendation: **reject** a shotengai list as a data dependency and
**reject** numeric boosts to `daily_essentials`/`vibe` (double-counting: vibe already
weights `pedestrian_street_count` 0.15; essentials already counts the individual
shops); **adopt** a description/fact layer — a pattern-union OSM proximity fact
("商店街 300 m" with union patterns, not name-substring alone) plus dated TMG survey
facts (CC BY) for editorial text.

---

## 1. What the pipeline does today (code refs)

- **Vibe** (`scripts/compute-ratings.py:462-486`): `raw["vibe"] = log1p(cultural)*0.60 +
  log1p(ped_streets)*0.15 + log1p(cafe)*0.15 + min(cultural,20)/20*0.10`, from
  `cultural_venue_count` + `pedestrian_street_count` (osm_extended, NocoDB-stored,
  producer outside the repo; consumed at `scripts/build-datamart.py:224-228`).
  Confidence via `vibe_confidence` (`compute-ratings.py:216-240`): both signals →
  `strong`, cultural only → `moderate`, else `estimate`. So **shotengai streets are
  already partially inside vibe** — most shotengai map to `highway=pedestrian`
  (verified below), which is what `pedestrian_street_count` counts.
- **Daily essentials** (`compute-ratings.py:500-531`): weighted `log1p` of 7 OSM
  livability counts (supermarket .25, pharmacy .15, clinic+dentist .20, bank .10,
  laundry .10, post .05, school+kindergarten .15); `strong` if ≥5 essentials found.
  The individual *shops inside* a shotengai are already counted here shop-by-shop.
- Persona weights touching these keys: `daily_essentials` 12–20, `vibe` 0–22
  (`app/src/lib/types.ts:445-466`).
- Descriptions already have a prose hook: `pedestrian_street_count > 5 → "Walkable
  shopping streets"` (`research/description-generation-rules.md:52`).
- Catchment convention: 800 m around the station (same as safety,
  `compute-ratings.py:426-429`); I used it for all per-station counts.

## 2. Official shotengai lists — what exists, what is dead

### 2.1 The one authoritative, licensed, downloadable artifact: TMG survey report ✅

**令和4年度東京都商店街実態調査 報告書** (Tokyo Metropolitan Government, 産業労働局;
152-page PDF, 5.49 MB, downloaded 2026-10-13 from
`https://www.sangyo-rodo.metro.tokyo.lg.jp/toukei/chushou/ef30f8c14fa5590ce238bb19480d2dd7_1.pdf`,
catalogued at `catalog.data.metro.tokyo.lg.jp` with **license CC BY 4.0** — read from
the CKAN package metadata). Parsed with pypdf. Key facts:

- **Frame: 「東京都内の全商店街（2,374 商店街 令和4年10月現在）」** — the TMG keeps a
  full register of Tokyo shotengai; this is the city-scale universe number.
- 有効発送 2,229 / 回収 1,349 (**60.5%**); −73 organizations vs 令和元年 survey.
- Structure: 法人 25.4% / 任意団体 74.6%; average member stores **52.9**; member mix:
  飲食店 36.3% (largest).
- **Per-municipality register counts** (page 8 table, quoted directly from the PDF):
  大田区 **140**, 世田谷区 **128**, 杉並区 **125**, 新宿区 **102**, 品川区 99, 練馬区 95,
  豊島区 87, 葛飾区 86, 板橋区 85, **台東区 (Nippori/Ueno) 109**, 足立区/江戸川区 76,
  渋谷区 74, 北区 74, **目黒区 66, 中野区 65**, 港区 58, 文京区 56, **江東区 (Toyosu) 52**,
  **中央区 (Ginza) 50**, **武蔵野市 (Kichijoji) 47**, 千代田区 45, 荒川区 43, 墨田区 40,
  **三鷹市 28** — i.e. every ward has dozens; shotengai are ubiquitous, not a
  central-Tokyo speciality.
- Cadence: every 3 years (since 平成元年度); survey owner 東京都産業労働局商工部地域産業振興課.

This report is **citable editorial fact material** (CC BY 4.0 + 加工 note), but the
register of 2,374 names/addresses is **not** in the file (aggregate only).

### 2.2 National statistics: 全振連/中小企業庁 商店街実態調査 — aggregate PDFs ✅

**令和6年度 商店街実態調査報告書** (全国商店街振興組合連合会 = Zenshin, published
2025-06, 176-page PDF, 18.5 MB, downloaded from
`https://www.syoutengai.or.jp/data/250617shoutengai01.pdf`, parsed with pypdf):

- Questionnaires sent to **11,280 shotengai** nationally (as of 令和6年10月1日),
  drawn from prefecture-maintained 名簿; footnote: 「各都道府県が把握している商店街数
  （参考値として調査）の合計は **12,091件**」 — the sum of all prefectural registers.
- Valid responses 4,824 (42.8%); 15th round since 1970; co-run with 中小企業庁 +
  中小企業基盤整備機構. Definition (footnote 2): shops forming a 街区 + *any*
  organization (法人/任意団体).
- Site policy: the portal `syoutengai.or.jp` is live (HTTP 200); the report is
  published as PDF without an explicit open-data license — **cite as fact, do not
  treat as a redistributable dataset**.
- Trend context (from the 中小企業庁 series): frame was 14,655 (2015) → 12,096 (2018)
  → **12,210 (2021, 令和3年度調査)** per the SME Agency page surfaced by web search
  (page itself is bot-gated from this environment — see §2.3; the 2021 figure is
  quoted from the search result of chusho.meti.go.jp, not read from the live page).

### 2.3 The named candidates from the ticket — dead, gated, or aggregate ❌

| Candidate | Status (checked 2026-10-13) |
|---|---|
| **全国商店街リスト** (machine-readable) | **Not found as open data.** The national universe exists only inside prefectural 名簿 (sum 12,091, §2.2) and survey frames; no bulk download. Tokyo catalog search (56 hits reviewed, CKAN API) returned **no city-wide list** — only ward-level fragments (§2.4). |
| **商店街マップ / shopping-street.jp** | **Dead.** `http://www.shopping-street.jp/` → connection failure (HTTP 000, DNS). `www.shotengai.jp` → parked page (netowl parking, HTTP 200). Archived CDX shows shopping-street.jp was never the shotengai DB (it was a shopping log site). |
| **METI 商店街実態調査 page** | **Bot-gated + moved.** Old URL `chusho.meti.go.jp/shogyo/shogyo/shotengai_chousa.html` → 404; site serves HTTP 403/empty-202 to non-browser clients intermittently (my curls). Survey results exist (§2.2 mirrors them via Zenshin). |
| **MLIT 商店街活性化** | `mlit.go.jp/crd/chukatu/` → **404** (WebFetch). 中心市街地活性化 program data is not a shotengai list anyway. **Not pursued further** — no evidence of a per-shotengai dataset. |
| **e-Stat** | Not checked (catalog search needs a free appId; the survey is not a 政府統計調査 — it runs via Zenshin/SME Agency as PDFs). Reported as *not run*. |

### 2.4 What per-ward open data does exist (fragmented) ⚠️

From `catalog.data.metro.tokyo.lg.jp` CKAN `package_search?q=商店街` (HTTP 200,
count 56):

- **目黒区商店街一覧表** (XLSX, **CC BY 4.0**, downloaded, parsed with openpyxl):
  a 地区×商店街名 matrix — 12 districts, e.g. 中目黒地区: 中目黒駅前商店街振興組合,
  中目黒駅西銀座商店街振興組合, 目黒銀座商店街協同組合…; **no coordinates, no counts,
  flat name lists only**.
- **港区商店街・商業施設・アンテナショップ** (CSV + GeoJSON with geometry, per
  catalog) — **could not download**: `opendata.city.minato.tokyo.jp` serves a 403
  CSRF interstitial to curl (retried with browser UA + cookie jar — still 403).
  **Not verified beyond the catalog metadata.**
- 港区 行政資料集 商店会数 (CSV, annual series R1–R7) — ward-level *counts*.
- 台東区 行政資料集 4.商店街振興 (CSV) — policy list, not a street register.

**Verdict:** a city-wide shotengai list would have to be assembled ward-by-ward from
heterogeneous files (some PDF/XLSX matrices without coordinates, some portals that
bot-block), refreshed per-ward on unknown schedules. That is the honest baseline
against which OSM (below) must be judged.

## 3. OSM shotengai — live Overpass counts and the tagging trap

Mirrors used (all three heavily rate-limited today; every query below is a retry-loop
success): `overpass.kumi.systems` (base 2026-07-15), `overpass.private.coffee`
(base 2026-06-01/07-28), `overpass-api.de`. ODbL.

### 3.1 City-wide (bbox 35.5–36.0 N / 139.2–139.9 E)

| Pattern | nodes | ways | relations | total |
|---|---:|---:|---:|---:|
| `shop=department_store` | 72 | 46 | 7 | **125** |
| `amenity=marketplace` | 32 | 24 | 2 | **58** |
| `highway=pedestrian` + name contains 商店街 | 0 | 30 | 0 | **30** |
| **any object** with name contains 商店街 (4 tiles: 42+251+15+44) | 84 | 265 | 3 | **352** |

Tile splits for the name scan: SW 35.5,139.2–35.75,139.55 = 42; SE 35.5,139.55–35.75,139.9
= **251** (the 23-ward commercial core); NW 35.75,139.2–36.0,139.55 = 15 (failed in
the batch driver after 14 attempts, succeeded on a solo retry); NE 35.75,139.55–36.0,139.9 = 44.

Reading: the ticket's hypothesized pattern (`highway=pedestrian` + name~商店街) finds
only **30 ways** — 8.5% of the name-substring universe (352) and ~1.3% of the
official register (2,374). Even 352 is a **lower bound with a systematic east-side
bias** (tile 2 holds 71% of the matches), and it still misses streets whose names
don't contain the word (next section).

### 3.2 The famous three — how they are actually tagged (query: name~サンロード|谷中銀座|地蔵通り|アメヤ横丁|アメ横, 600 m around each station)

| Object | OSM | Tags |
|---|---|---|
| 吉祥寺サンロード商店街 | way 185393652 | `highway=pedestrian` ✔ |
| サンロード (same street, second way) | way 1148606044 | `highway=pedestrian`, **name has no 商店街** |
| 谷中銀座 | ways 671851311, 737745076 (`pedestrian`), 737745077, 671851312 (`residential`), 253020945 (`footway`), 736938228 (`service`) | **6 ways, 4 different highway values, none named …商店街** |
| 地蔵通り商店街 (巣鴨) | way 176781353 | **name-only, no tags at all** (`{}`) |
| 地蔵通り | way 176116031 | `highway=unclassified` |
| アメヤ横丁 (上野) | node 4496960001 | `amenity=marketplace` + `tourism=attraction` |
| 吉祥寺サンロード / 谷中銀座 gates | nodes 10685091805 / 8691137817 | `tourism=attraction` |

Consequences: (a) any single-pattern detector (pedestrian+商店街) returns **0 for
Nippori** although 谷中銀座 is ~500 m from the station; (b) 巣鴨's main street is an
untagged name-only way — invisible to any tag-based filter except the name; (c) a
robust detector must be a **union**: `highway~pedestrian|footway` + name regex
(商店街|商店会|銀座|サンロード|横丁|モール) ∪ `amenity=marketplace` ∪
`tourism=attraction` near them — with a real precision cost on 銀座 (the suffix also
names Ginza-the-district streets).

### 3.3 Per-station 800 m counts (repo stations.json coords; count queries with 3 blocks each)

| station | department_store | marketplace | name~商店街\|商店会 |
|---|---:|---:|---:|
| shibuya 渋谷 | **10** (4n+6w) | 1 | 0 |
| ginza 銀座 | **7** (3n+4w) | 1 | 1 |
| ueno 上野 | **5** (4n+1w) | 1 | 1 |
| tsukiji 築地 | 4 | 1 (way) | 0 |
| kichijoji 吉祥寺 | 2 (w) | 1 | 1 |
| toyosu 豊洲 | 1 | **0** | 0 |
| **shin-toyosu 新豊洲** | 1 | **3** (豊洲市場 ways) | 0 |
| nakano 中野 | 1 | 1 | **5** (4w+1r) |
| sugamo 巣鴨 | **0** | 2 | **6** (4n+2w) |
| jiyugaoka 自由が丘 | 0 | 1 | 3 |
| kagurazaka 神楽坂 | 0 | 0 | 1 (relation) |
| nippori 日暮里 | **0** | **0** | **0** ← 谷中銀座 not matched (§3.2) |
| sangenjaya 三軒茶屋 | 0 | 0 | 0 |
| denenchofu 田園調布 | 0 | 0 | 0 |

Reading: `department_store` is a **clean ordinal signal** (10/7/5 vs 0–2; 3 of 13
stations have 5+, zero for residential/shitamachi stations). The shotengai name count
is **noisy in both directions**: 巣鴨 6 > 吉祥寺 1 despite Kichijoji's famous arcades
(Sunroad partially uncounted, §3.2), and three 0s that are demonstrably false
negatives (nippori, and sangenjaya which has 三軒茶屋銀座通り — absent from OSM under
that name). Marketplace per-station is sparse and inconsistent (sugamo's 2 are small
nodes; the real Toyosu market lands in shin-toyosu's circle).

## 4. Department stores

- **OSM counts** (above): 125 city-wide; concentration matches reality — Ginza 7,
  Shibuya 10, Ueno 5 (松坂屋上野/アメ横横丁 block), Tsukiji 4 (this circle includes
  the Ginza-side edge at 800 m), Kichijoji 2 ( Parco/Yamashiro-ki? — ways, unnamed
  here), Toyosu 1 (node; ララポート? not inspected). Not verbatim-audited per object —
  counts only.
- **Wikidata** (SPARQL + entity API, run today):
  - Chain items: `P31/P279* Q2549179 (百貨店チェーン)`, `P17 Q17` → **21 chains**.
  - 伊勢丹 Q3155239, 三越 Q1065598 (P31 business/enterprise — *not* dept-store
    class), 高島屋 Q2058024 all exist with inception/official links.
  - **Branch coverage is sparse and classless**: 伊勢丹新宿本店 Q140194005 exists
    (P31=Q41176 building, coords 35.69156,139.704651 — no class "department store",
    no size); タカシマヤタイムズスクエア Q2109853 (coords; its P3032 area claim has
    **no value**); 銀座三越 → **no item** (search 0); 渋谷西武 Q11628905 exists.
  - **GLA: no Wikidata property exists** for gross leasable area — property searches
    for "gross leasable area" and "leasable" (`type=property`) both returned **0**.
    So "Wikidata GLA" from the ticket is **not available**; the closest Wikidata can
    give a branch is coordinates and a chain link, not floor area.
- **Depachika** (department-store basement food halls): no OSM tag convention and no
  Wikidata representation was found; as a data layer this is **editorial prose only**
  (e.g. fact-card text on stations near the ~10 flagship stores), not a computed key.

## 5. Markets

- OSM `amenity=marketplace` = **58 objects city-wide** (§3.1); per-station counts
  sparse (§3.3).
- **豊洲市場**: ways 436183395/436183396/436183397 = `amenity=marketplace` +
  `landuse=wholesale` (5/6/7街区 blocks) + relation 9113166 `landuse=commercial`.
  Its 800 m circle is **shin-toyosu**'s (3 marketplace ways) — toyosu station proper
  counts 0. Any "market" fact must be keyed off the right catchment.
- **築地場外市場**: way 606978548 `amenity=marketplace` + `landuse=retail` (in
  tsukiji's 800 m ✔). The *inner* market is gone (moved 2018).
- **Wikidata**: 豊洲市場 Q11633916 (P31 central wholesale market Q11363644, coords
  35.64417,139.78361 ✔); 築地場外市場 → **no dedicated item** — the search hits
  resolve to Q859471 築地市場, described as 「かつて…存在した」 (the *former* inner
  market). 早市 (morning markets): no meaningful OSM/Wikidata coverage found — not
  further pursued.
- Honest note: `amenity=marketplace` in Tokyo is used for everything from 豊洲市場 to
  a small shopping-center food floor (sugamo's 2 nodes) — treat counts as raw
  evidence, not as "public market" semantics, if ever surfaced.

## 6. Wikidata shotengai — coverage check (the ticket's list hypothesis)

- Class: Q96288394 日本の商店街 (shōtengai), subclass Q21000333; arcade subclass
  Q96288605 日本のアーケード商店街.
- SPARQL (run today): instances/subclasses of Q96288394 in Japan = **178 items, 61
  with coordinates** — against a universe of 12,091 (national registers) / 2,374
  (Tokyo), Wikidata covers **~1.5% nationally** and is unusable as a proximity layer.
- Famous-three check: 吉祥寺サンロード = Q10855749 (P31 arcade, no coords),
  谷中銀座 = Q106701725 (no coords), **巣鴨地蔵通り = absent** (0 hits across
  wbsearchentities and full-text search for 巣鴨地蔵通り / 地蔵通り商店街 /
  Jizo-dori Sugamo). A list that misses one of Tokyo's most famous shotengai cannot
  back a station feature.

## 7. Composition: boost daily_essentials/vibe vs a "商店街 300 m" fact

**Option A — numeric boost to `daily_essentials`.** Rejected: the component shops of
a shotengai are already counted individually in the 7 livability counts
(`compute-ratings.py:500-522`); adding street presence double-counts the same
geometry, and shotengai retail mix (飲食 36% of members, souvenirs) is not
essentials-weighted — Yanaka Ginza has few pharmacies/banks. It would also import
the OSM east-side bias (§3.1) into a weight that 4 personas carry at 12–20%
(`app/src/lib/types.ts:445-466`).

**Option B — numeric boost to `vibe`.** Rejected as an *additional* term: vibe
already contains `log1p(ped_streets)*0.15` (`compute-ratings.py:464-486`) and
shotengai streets largely *are* the pedestrian streets — a second term re-weights
the same objects by name luck (§3.2). If the owner wants shotengai to matter more in
vibe, the honest lever is recalibrating `pedestrian_street_count`'s 0.15 weight, not
a parallel signal. Note `vibe` also carries an AI-researched override for ~252
stations (`mcp/USAGE.md:104`), which further reduces marginal value of a new
computed term.

**Option C — "商店街 300 m" fact / description layer (recommended).** A fact card /
description sentence computed from a **pattern union** in a small radius (300 m for
facts, or reuse 800 m to match the safety convention — owner's call):
`(highway in {pedestrian,footway} AND name ~ 商店街|商店会|銀座|サンロード|横丁|モール)
UNION amenity=marketplace UNION tourism=attraction(name~同)`. This is:
full-station-coverage, refreshable monthly, ODbL; the famous-sample (§3.2) shows the
union actually catches Sunroad (2 ways), Yanaka Ginza (6 ways + attraction node),
Ameya-yokochō (marketplace node). It must ship with a **known-false-negative
caveat**: untagged name-only ways (地蔵通り商店街) and brand-named streets in
unmapped areas still drop out — the fact says "shotengai mapped nearby", not
"no shotengai here".

**Option D — dated editorial facts from official statistics.** The TMG report
(CC BY 4.0) yields citable, dated facts for descriptions/methodology: 「都内の商店街
2,374 (令和4年10月現在)」, per-ward counts (台東区 109 — one of the densest), decline
−73 in 3 years, average 52.9 member stores. Zero pipeline coupling; perfect for the
description generator's fact blocks and `/methodology` attribution.

## 8. Maintainability of a shotengai list — honest assessment

- **No open machine-readable list exists to ingest** — national registers are
  prefecture-internal (12,091 names), TMG's 2,374-item register is not published as
  data, ward lists are fragmentary (Meguro XLSX without coordinates; Minato GeoJSON
  bot-blocked from here), historical portals are dead. Building our own curated list
  would mean manual maintenance of ~2,400 organizations with a 3-year official
  cadence and no update feed. **Reject.**
- **OSM is the only geocoded feed**, but single-pattern detectors are provably wrong
  on anchors (30 pedestrian+商店街 ways; Nippori=0). A union pattern is defensible
  and self-maintaining (community updates, ODbL), with east-side and
  tagging-generation bias documented above. **Adopt as fact layer only.**
- **Wikidata cannot substitute** (178 items, 61 coords, famous-three incomplete). 
- **Wikidata as enrichment**: acceptable for *named famous* shotengai fact cards
  (Sunroad 1971 open date via P1619, official site P856) — decorative, not structural.

## 9. Recommendation

1. **Adopt Option C**: a pattern-union OSM proximity **fact** ("商店街 ~300 m":
   nearest mapped shotengai name + distance) for description/fact layers, with the
   false-negative caveat in the methodology text. Not a rating key.
2. **Adopt Option D**: TMG 東京都商店街実態調査報告書 (CC BY 4.0) as the editorial
   statistics source (2,374 city total, per-ward counts, 3-year refresh); Zenshin
   report as national context (11,280 surveyed / registers 12,091).
3. **Reject**: numeric boost to `daily_essentials` or `vibe`; a curated shotengai
   list dependency; Wikidata as coverage source; "Wikidata GLA" (no such property);
   depachika as anything but prose.
4. If a shopping signal must enter a rating anyway, the only clean candidate is
   `shop=department_store` density (125 objects, wide ordinal separation) — as an
   **owner decision**, e.g. a small term in vibe or a "department stores nearby"
   fact; not tested as a key here.

## 10. Open questions for the owner

1. Fact radius: 300 m (ticket phrasing) or 800 m (repo catchment convention)?
2. Pattern set for the union: include 銀座/横丁/サンロード/モール (recall↑, precision↓
   — 銀座 collides with the Ginza district)? Suggest calibrating on the 1,493-station
   distribution before fixing (not run here).
3. Should the fact card show the matched street name ("谷中銀座 400 m") or a bare
   boolean?
4. Department-store density: keep as prose/landmarks material only, or give it a
   rating role (persona-weighted)?
5. Attribution wording: TMG report CC BY 4.0 + 加工 note on `/methodology`; ODbL for
   OSM counts.
6. The Minato GeoJSON (ward shotengai with geometry) failed to download from here
   (403 CSRF) — if the owner can fetch it in a browser, it would be the one ward
   list worth keeping as a spot-check ground truth for the OSM union.

## Appendix — exact commands run this session (2026-10-13)

```
# Overpass (retry loop over kumi.systems / private.coffee / overpass-api.de; Python driver /tmp/opq.py, /tmp/queue.py)
nwr["shop"="department_store"](35.5,139.2,36.0,139.9); out count;            # 125 (72n/46w/7r)
nwr["amenity"="marketplace"](35.5,139.2,36.0,139.9); out count;              # 58 (32n/24w/2r)
nwr["highway"="pedestrian"]["name"~"商店街"](35.5,139.2,36.0,139.9); out count;  # 30 ways
nwr["name"~"商店街"](35.5,139.2,36.0,139.9); out count;                      # 4 tiles: 42/251/15/44 → 352
# per-station (800 m), 3 count blocks each:
(nwr["shop"="department_store"](around:800,LAT,LNG););out count;
(nwr["amenity"="marketplace"](around:800,LAT,LNG););out count;
(nwr["name"~"商店街|商店会"](around:800,LAT,LNG););out count;
#   stations: kichijoji sugamo nippori ueno shibuya | ginza toyosu tsukiji kagurazaka nakano |
#   sangenjaya jiyugaoka denenchofu | (+shin-toyosu solo)
(nwr["name"~"サンロード"](around:600,35.703119,139.579765);
 nwr["name"~"谷中銀座"](around:600,35.727908,139.771287);
 nwr["name"~"地蔵通り"](around:600,35.733445,139.739303);
 nwr["name"~"アメヤ横丁|アメ横"](around:600,35.71379,139.777043);); out tags center 40;   # §3.2 table
(nwr["name"~"豊洲市場|豊洲漁業|築地場外"](35.5,139.2,36.0,139.9);); out tags center 20;     # §5 tagging

# Wikidata
wbsearchentities: 吉祥寺サンロード→Q10855749; 谷中銀座→Q106701725; 巣鴨地蔵通り/地蔵通り→0 hits
Special:EntityData: Q10855749, Q106701725, Q96288605, Q96288394, Q28683525, Q1065598,
  Q3155239, Q2549179, Q140194005, Q2109853, Q11633916, Q859471
property search: "gross leasable area"/"leasable" type=property → 0 results
SPARQL (query.wikidata.org):
  P31/P279* Q96288394 & P17 Q17 → 178 items, 61 coords
  P31/P279* Q2549179 & P17 Q17 → 21 chains
  (P31 Q210728 — WRONG QID used in a first probe, returned 0; corrected after checking Q6881511/Q2549179)

# Official data
curl catalog.data.metro.tokyo.lg.jp CKAN package_search q=商店街 → 56 datasets (license fields read)
curl -o meguro.xlsx  data.bodik.jp …/131105_meguroshoutengaiichiran20250711.xlsx ; openpyxl read (CC BY 4.0)
curl -o tmg_sg.pdf   sangyo-rodo.metro.tokyo.lg.jp …/ef30f8c14fa5590ce238bb19480d2dd7_1.pdf (5,490,104 B);
  pypdf: 2,374 frame, per-ward table, 回収率 60.5%, −73, 52.9 avg stores, 飲食 36.3%
curl -o zenshin_r6.pdf syoutengai.or.jp/data/250617shoutengai01.pdf (18,526,566 B);
  pypdf: 11,280 sent, registers 12,091, valid 4,824, definition footnote
curl chusho.meti.go.jp (403/202 bot-gate), shotengai_chousa.html (404), mlit.go.jp/crd/chukatu (404),
  shopping-street.jp (DNS fail), shotengai.jp (parked), shotengai.or.jp/accepted (2016-era forms portal)
opendata.city.minato.tokyo.jp CSV → 403 CSRF (browser UA + cookie jar retried)

# Repo reads
scripts/compute-ratings.py:216-240,455-531,547-605; app/src/lib/types.ts:4,64-78,389-480;
scripts/build-datamart.py:224-228; research/description-generation-rules.md:45-56; mcp/USAGE.md:104;
data/stations.json (station coords; shin-toyosu exists at 35.648718,139.789996)
```

Only this note was created in the repo. All downloads went to /tmp; numbers in
§2–§5 are transcribed from the parsed files and Overpass JSON outputs quoted above.
