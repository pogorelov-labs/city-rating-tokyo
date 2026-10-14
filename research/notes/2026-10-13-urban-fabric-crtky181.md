# Tokyo urban fabric — walkability, arterial/首都高 exposure, barrier-free stations (CRTKY-181)

Researched: **2026-10-13**, by the open-data research agent. Companion to the
Bangkok wave (the ask asked to compare with
`research/bangkok/notes/2026-10-13-urban-fabric-crtky147.md` — **that file does
not exist yet** as of this run; §9). All fetches and computations below were run
by me in this session; commands and outputs are quoted. Nothing here is an
implementation decision — the owner adopts sources.

**TL;DR:** Tokyo's urban fabric is measurable from open data, and the signal is
*much* stronger than anything Bangkok had. Three verified findings: (1) OSM has
dense, distinct walkability signals per area — crossing nodes run **197/km² in
千代田区 vs 62/km² in 世田谷区 vs 21/km² in the covered part of 八王子市**, and the
separately-mapped sidewalk network (`highway=footway`+`footway=sidewalk`) runs
**127/km² vs 23/km² vs 16/km²** — but the ask's proposed metric, *sidewalk tags
on arterials*, is dead on arrival in Japan: only **0.0–1.5 %** of primary/secondary
length carries `sidewalk=*`, because Japanese sidewalks are mapped as separate
ways, not tags. (2) 首都高 is cleanly extractable (`highway=motorway`+
`name~首都高`, 845 ways in the project bbox) and gives a real per-station
exposure spread: **0.16 km (渋谷) … 1.6 km (二子玉川) … 18–22 km (立川/八王子)**.
(3) Barrier-free has an open-data main find: **MLIT publishes bulk CSVs of
barrier-free equipment per station (elevator/escalator counts, tactile paving,
accessible toilets/gates, lat/lon)** — 654 station×line rows for Tokyo, 585
with elevators — while **JR East's own ODPT dataset is Challenge-2026-restricted
(not reusable)** and JR East's website has no bulk list. Cleanliness: no honest
open data — skip. Verdict: **promising** — build walkability as a *per-station
proxy* from OSM (crossing + sidewalk-network density + arterial/首都高 exposure),
source barrier-free from MLIT, reject the arterial-sidewalk-tag metric.

---

## 1. What the ask asked, mapped to checks

| Ask item | Check run | Result |
|---|---|---|
| Share of primary/secondary with `sidewalk=*` or parallel `footway=sidewalk`, lengths sampled via 千代田 vs 世田谷 vs 八王子 | live Overpass `poly` queries over ward boundary rings; haversine length per way (§3) | measured; sidewalk-tag share ≈ 0; separate ways counted (§3) |
| Crossings density | live Overpass `node(poly)["highway"="crossing"]` counts (§4) | 2,224 / 3,615 / 3,979 nodes (§4) |
| 歩行者天国 zones (name) | live Overpass `name~歩行者天国` in project bbox + `highway=pedestrian` in Ginza box (§5) | **0 named features**; periodic zones not in OSM (§5) |
| 首都高 proximity to 10 sampled stations | live Overpass motorway geometry + haversine to 10 stations from `data/stations.json` (§6) | 845 ways; table in §6 |
| Barrier-free: OSM `railway=station`+`wheelchair` counts by prefecture; operator lists (JR East?) | live Overpass poly over 東京都 boundary ring; ODPT CKAN fetch; MLIT CSV downloads (§7) | OSM 338 yes / 25 limited / 16 no of 796 stations; MLIT CSVs = main find (§7) |
| Cleanliness | web search for Tokyo ward/street cleanliness open data (§8) | no honest dataset → skip |
| Compare with `urban-fabric-crtky147.md` | `ls research/bangkok/notes/` | file not present (§9) |

## 2. What was actually run — and the Overpass environment reality

All OSM numbers came from live Overpass calls in this session. The named
mirrors behaved very differently, and two defects forced a methodology change —
worth recording because production pipeline decisions depend on it:

- `overpass-api.de` — **dead from this environment**: `curl` → `000`,
  `LibreSSL SSL_connect: SSL_ERROR_SYSCALL` (TLS reset in <1 s); plain HTTP →
  `(52) Empty reply`.
- `overpass.kumi.systems` — reachable but the interpreter endpoint timed out on
  every real query (120–150 s, `000`); only `/api/status` ever answered.
- `overpass.private.coffee` — **worked**, but: (a) **the area index is broken**
  — `area(3601759474)` exists (`.a out count;` → `areas: 1`) yet
  `node(area.a)["highway"="crossing"]` returns **0**, while the same feature
  class in a bbox returns 4,982 — so **administrative-area filters are unusable
  here**; (b) responses came from different backend shards with different base
  snapshots — `timestamp_osm_base` observed `2026-05-06`, `2026-05-31`,
  `2026-06-01`, `2026-07-15`, `2026-07-28` across this session; (c) GET URLs
  over ~2 KB die with **HTTP 414**, so long queries must go via
  `POST --data-urlencode data@file` (works; 17 s for a small query).

Because area filters were broken, every area-scoped query in this note uses
**`poly:"lat lon …"` filters built from the ward boundary relations themselves**
(`rel(id); out geom;` → chain member ways end-to-end → Douglas-Peucker simplify
to ~0.5 m·10² tolerance). Method note: ways enter the poly result when their
geometry falls inside the polygon; the polygon is the simplified boundary, so
border strips (<~50 m) are fuzzy.

Commands used (representative):

```
curl -4 -sS -o w3_chiyoda.json --max-time 560 -X POST \
  https://overpass.private.coffee/api/interpreter --data-urlencode data@q3_chiyoda.overpass
# q3_chiyoda.overpass (per ward):
# [out:json][timeout:400];
# way(poly:"<ring>")["highway"="crossing"]; out count;
# way(poly:"<ring>")["highway"="footway"]["footway"="sidewalk"]; out count;
# way(poly:"<ring>")["highway"~"^(primary|secondary)$"]; out geom;
```

Lengths were computed locally by haversine over the returned `out geom` points
(pure python, no deps). Ward areas were computed from the same boundary rings by
shoelace on an equirectangular projection — **self-verified against official
values**: 世田谷区 ring 57.84 km² vs official 58.06 km² (−0.4 %), 千代田区 ring
11.31 km² vs official 11.66 km² (−3 %; DP corners + the Imperial-Palace hole
counted as land). **八王子市's OSM boundary in this mirror is defective**: the
relation has only 50 member ways, chains into a perfect closed ring, but its
bbox is 35.598–35.719 N × 139.162–139.430 E and its area computes to
**185.6 km² vs the official 669.26 km²** (largest municipality in Tokyo;
[Wikipedia](https://zh.wikipedia.org/wiki/八王子市)). The Hachioji numbers below
are exact counts *within the polygon the mirror served* — i.e. roughly the
urban eastern/central belt, not the whole city. Production should re-verify
boundaries against `overpass-api.de` or a local extract.

## 3. Arterial sidewalk share — the proposed metric is wrong for Japan

`way(poly)["highway"~"^(primary|secondary)$"]`, length-weighted by haversine:

| Ward (ring area) | arterial ways | total km | primary km | secondary km | `sidewalk=mapped`¹ | `sidewalk=separate` | untagged | separately-mapped `footway=sidewalk` ways |
|---|---|---|---|---|---|---|---|---|
| 千代田区 (11.31 km²) | 401 | 52.8 | 19.4 | 33.4 | **0.9 %** | **1.5 %** | 97.5 % | **1,434** (126.8/km²) |
| 世田谷区 (57.84 km²) | 488 | 98.2 | 58.0 | 40.2 | **0.0 %** | **0.0 %** | ~100 % | **1,355** (23.4/km²) |
| 八王子市 (185.6 km², partial ring) | 507 | 171.1 | 60.0 | 111.0 | **1.1 %** | **0.0 %** | 98.9 % | **2,915** (15.7/km²) |

¹ `sidewalk` in {yes, both, left, right, lane, …}; `no` counted as untagged.

**Finding:** in Japanese OSM, carriageway `sidewalk=*` tagging is essentially
absent (0.0–1.5 % of length). Sidewalks are mapped as **separate
`highway=footway` + `footway=sidewalk` ways** — 1,434 in Chiyoda alone. The
per-ward density gradient of that separate network (127 → 23 → 16 ways/km²) is
the real sidewalk signal. Any pipeline metric that reads `sidewalk=*` off
arterials will report "Tokyo has no sidewalks" — **reject that metric**; use
separate-way density (or a within-buffer sidewalk-length measure) instead.

Sanity check on extraction quality: the largest returned way in Chiyoda is an
18-node 436 m stretch of 晴海通り (`highway=primary`); a random way was
re-fetched by id from the OSM API itself and matches (`api.openstreetmap.org/api/0.6/way/19779850/full.json` → 2-node micro-segment, same tags), i.e.
Japan's OSM really does carry micro-split carriageway segments, and the length
sums are honest.

## 4. Crossings density

`node(poly)["highway"="crossing"]` (one combined query, three counts):

| Ward | crossing nodes | per km² |
|---|---|---|
| 千代田区 | 2,224 | **196.6** |
| 世田谷区 | 3,615 | **62.5** |
| 八王子市 (covered ring) | 3,979 | **21.4** |

A 9× core-to-suburb gradient — this is the single strongest walkability
discriminator found, and it is one cheap Overpass query per station buffer.
Note Japan-specific tagging: pedestrian crossings are also mapped as *ways*
(`highway=crossing` on ways) for zebra areas — in these three wards that
variant contributed **0 ways**, so node-based counting is sufficient here, but
the pipeline should count both variants to be safe.

## 5. 歩行者天国 (periodic pedestrian zones) — not in OSM

- `name~歩行者天国` over the full project bbox (nodes+ways): **0 elements**
  (valid JSON, empty `elements` — verified negative, snapshot 2026-06-01).
- Control query, `highway=pedestrian` in the Ginza/Shimbashi box
  (35.655–35.680 N, 139.750–139.785 E): 145 pedestrian ways — all permanent
  plazas, arcades and footbridges (named examples: 日比谷アーケード,
  汐留駅前歩道橋, カレッタプラザ, 銀座東八丁目歩道橋). **銀座中央通り — the famous
  Sunday 歩行者天国 — is NOT tagged pedestrian**, correctly, since the closure
  is periodic.
- I found no machine-readable public registry of 歩行者天国 schedules in this
  session (TMG/ward pages are prose calendars; not verified beyond a web
  search).

Verdict: periodic pedestrian zones are **out of OSM and out of easy open
data**. If the owner wants the flavor, the ~10 famous ones (銀座中央通, 秋葉原
中央通, 新宿 etc.) can be a tiny hand-curated list — optional, not adoptable as
a data source.

## 6. 首都高 exposure — clean per-station signal

Query: `way["highway"~"^(motorway|motorway_link)$"]["name"~"首都高"](35.5,139.2,36.0,139.9); out geom;`
→ **845 ways**, snapshot 2026-07-15 (routes seen: 都心環状線 121, 中央環状線 115,
湾岸線 113, 4号新宿線 54, 3号渋谷線 28, 5号池袋線 26, 6号線s, 羽田線, 深川線, …).
Distance = min haversine from the project's station pin (`data/stations.json`,
1,493 entries) to every 3rd geometry vertex (4,862 sampled points; ≤~30 m
overestimate):

| Station (slug) | min distance to 首都高 |
|---|---|
| shibuya 渋谷 | **0.16 km** |
| ueno 上野 | **0.17 km** |
| akihabara 秋葉原 | **0.20 km** |
| ikebukuro 池袋 | 0.52 km |
| tokyo 東京 | 0.59 km |
| shinjuku 新宿 | 0.98 km |
| shinagawa 品川 | 1.03 km |
| futako-tamagawa 二子玉川 | 1.61 km |
| tachikawa 立川 | 18.29 km |
| hachioji 八王子 | 21.69 km |

A clean 0.16→21.7 km spread — per-station expressway exposure is directly
computable from OSM with no external source. ( Tokyo's noise note
`research/notes/2026-10-13-noise-crtky175.md` §6 already flagged 首都高 ramps
as a modeled-noise component; the same geometry serves the walkability/
annoyance side. )

## 7. Barrier-free stations — MLIT bulk CSVs are the open main find

### 7.1 OSM wheelchair tagging (live, 東京都 boundary ring, snapshot 2026-07-15)

`node(poly:"<Tokyo ring>")["railway"="station"]` → **796 stations**; with
`wheelchair` tag: **379 (47.6 %)** → `yes` **338**, `limited` **25**, `no` **16**.

Half the network is untagged — OSM alone is not a barrier-free source, but it
is a usable cross-check.

### 7.2 MAIN FIND — MLIT 公共交通施設に関するバリアフリー情報 (open bulk CSVs)

Dataset [公共交通施設に関するバリアフリー情報](https://data.e-gov.go.jp/data/dataset/mlit_20160325_0033)
(国土交通省, data.go.jp portal). CSVs are hosted at `www.hokoukukan.go.jp` and
**download successfully** (verify: `curl -L -A "<browser UA>" -e
"https://data.e-gov.go.jp/data/dataset/mlit_20160325_0033"
https://www.hokoukukan.go.jp/download/mlit_jr_sta.csv` → HTTP 200; note a bare
curl gets **403** — a browser User-Agent + Referer header is required, not a
license wall):

| File | Rows JP | Rows 東京都 | elevator count > 0 (Tokyo) |
|---|---|---|---|
| `mlit_jr_sta.csv` | 1,282 | 131 (JR東日本 129, JR東海 2) | 121 |
| `mlit_metro_sta.csv` (subways) | 613 | 228 (東京地下鉄 132, 都営 96) | 218 |
| `mlit_pr_tram_sta.csv` (民鉄・軌道) | 1,201 | 295 (京王 66, 西武 60, 東急 56, 東武 28, 小田急 23, 京成 21, 京急 19, ゆりかもめ 12, 東京モノレール 10, …) | 246 |
| **total** | **3,096** | **654** | **585 (89 %)** |

Schema (CP932 CSV, verified by parsing): 鉄道事業者名 / 駅名 / 路線名 /
都道府県・市・町村 / 段差への対応 / プラットホーム数 + 段差解消ホーム数 /
**エレベーターの設置基数** + 基準適合基数 / エスカレーター数 (+適合) / その他昇降機 /
傾斜路 / 視覚障害者誘導用ブロック / 案内設備 / **障害者対応型便所** / 対応型改札口 /
対応型券売機 / 車いす対応ホーム数 / 転落防止設備 / **緯度・経度** (100 % filled,
verified) / 場所情報コード.

Granularity: **station × line rows** (not unique stations) with coordinates —
directly joinable to the project's per-station model. Caveats: rows are
self-reported by operators; dataset released 2016-03-29, metadata updated
2023-04-18, update frequency 不定期 (irregular); no explicit CC license on the
page — it falls under the data.go.jp government terms of use (政府標準利用規約
pattern, attribution-based reuse). Bus/ship/airport terminals are also
included in the same dataset family (not needed here).

### 7.3 JR East specifically — checked, not openly reusable

- ODPT CKAN ([ckan.odpt.org](https://ckan.odpt.org), 44 StationFacility-family
  datasets): JR東日本's 駅情報 is licensed **【チャレンジ2026限定】(Challenge-2026
  limited license)** — contest-restricted, **not adoptable** for a public
  product. (Tokyo Metro's datasets showed no explicit license on the page —
  also not clean.)
- JR East publishes per-station facility/layout pages
  ([jreast.co.jp](https://www.jreast.co.jp/en/multi/stations/)) — web prose per
  station, no bulk list, site copyright; not a data source.
- ⇒ the open path for JR East barrier-free data **is the MLIT CSV**, which
  includes JR東日本 rows (129 in Tokyo).

## 8. Cleanliness — skip

Web search (JP + EN) found **no unified Tokyo-wide street-cleanliness dataset**:
only per-ward litter surveys (渋谷区 ポイ捨てごみ実態把握調査; 府中市 beautification
stats), a national 環境省 questionnaire report, and a private company ranking
(Pirika/タカノメ 23-ward litter amounts). Nothing comparable, licensed, and
street-level ⇒ **no honest data, skip** — one line, as instructed: no open,
licensed, comparable street/ward cleanliness measurements exist for Tokyo, so
any "cleanliness" dimension would be invented, not measured.

## 9. Comparison with Bangkok urban-fabric-crtky147.md

**Not possible: the file does not exist.** `ls research/bangkok/notes/` (this
session) shows 11 notes (air, flood, healthfood, institutions, michelin, noise,
population, redlight, rent-anchors, safety, tourists) — no urban-fabric note.
Where the comparison was expected, the Tokyo side stands alone; the shared
pattern file should be reconciled when the Bangkok ticket lands.

## 10. Recommendation — per-station walkability proxy: **adopt**; arterial sidewalk-tag share: **reject**

Per-station proxy is not just feasible in Tokyo, it is the strongest form of
this dimension available anywhere in the two cities:

- **Signal strength** — orders-of-magnitude density gradients (§3/§4: crossings
  197 vs 62 vs 21 /km²; sidewalk ways 127 vs 23 vs 16 /km²) mean a per-station
  buffer (e.g. 400–800 m) will differentiate stations sharply, not noise-fully.
- **Two independent OSM components** (crossing density, separately-mapped
  sidewalk-network density) plus **arterial length in buffer** and **首都高
  distance** (§6) compose into a defensible walkability/exposure score.
- **Barrier-free rides on MLIT** (§7.2): per-station elevator counts with
  lat/lon — a direct station-level attribute, no modeling needed.
- **What NOT to do:** do not score `sidewalk=*` on arterials (0–1.5 % tagged →
  constant near-zero); do not use OSM `wheelchair` as the barrier-free layer
  (47.6 % coverage); do not rely on Overpass `area` filters or this mirror's
  administrative boundaries (§2 — Hachioji ring is 185.6 of 669.26 km²).

| Source | Verdict |
|---|---|
| OSM `poly`-filtered crossings / `footway=sidewalk` / arterial geometry (Overpass) | **adopt** (via station buffers, not wards) |
| OSM 首都高 motorway geometry, `name~首都高` | **adopt** |
| MLIT バリアフリー情報 CSVs (hokoukukan.go.jp via data.go.jp) | **adopt** as the barrier-free layer |
| OSM `wheelchair=*` on stations | cross-check only (48 % coverage) |
| Arterial `sidewalk=*` share (as asked) | **reject** for Japan |
| JR East ODPT dataset (Challenge license) / jreast.co.jp pages | **reject** (license / no bulk) |
| 歩行者天国 from OSM | reject (absent); optional hand-curated list |
| Cleanliness | **skip** — no honest open data |

## 11. Open questions for the owner

1. Production Overpass strategy: `overpass-api.de` was unreachable from this
   environment and the working mirror has a broken area index, stale/uneven
   snapshots (May–Jul 2026) and a partial 八王子市 boundary — self-hosted extract
   (or NLD 行政区域 boundaries as the polygon source) vs. mirror-with-QA?
2. Buffer radius for the per-station proxy (400 m walkable vs 800 m), and how
   the components weight (crossings vs sidewalk-network vs exposure)?
3. Is the MLIT CSV's freshness acceptable (released 2016, irregular updates,
   last metadata touch 2023-04) as the barrier-free baseline, with OSM as a
   fresher-but-sparser overlay?
4. Does the 403-unless-browser-UA quirk on `hokoukukan.go.jp` need a
   polite-fetch policy (UA string, rate) in the pipeline?
5. Walkability label semantics: with gradients this strong, is the dimension
   "walkability" or "urban fabric / street environment"? (affects 福岡/バンコク
   comparability, §9 pending)
