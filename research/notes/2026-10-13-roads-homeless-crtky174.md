# Tokyo road-safety statistics (警視庁) + proximity of homeless-services (CRTKY-174)

Date: 2026-10-13. Researcher: automated open-data sweep for CRTKY-174.
Status: research only — nothing here is adopted; any integration and any publication of
homeless-related content is an owner decision. Homeless topic below uses neutral
"proximity of support services" framing only; no scores are proposed.

Ticket framing vs what was found:
- "署別 помесячно" — **not exactly true**: 警視庁's *monthly* accident publication is by
  区市町村 (ward/municipality, PDF); *署-level* (police-station) accidents are published
  **annually** in the machine-readable Excel table 第10表 of 警視庁の統計 (verified live).
- "地点別事故発生マップ — проверь, есть ли данные, а не только визуализация" — **data
  behind the map exists (JSON endpoint verified live), but the map's terms of use
  prohibit reuse; recommend reject** (details §1c).
- "東京都 ежегодная 路上生活実態調査" — two distinct series exist: the **semi-annual**
  路上生活者概数調査 (count survey, per ward, 2004–2026, PDF) and the **quinquennial**
  national 生活実態調査 (questionnaire survey; latest 2021). Both PDF-only (§2).

## Access notes (what worked, what didn't)

- `keishicho.metro.tokyo.lg.jp`, `fukushi.metro.tokyo.lg.jp`, `catalog.data.metro.tokyo.lg.jp`
  — direct `curl` worked all session.
- Overpass: `overpass-api.de` returned **406 for every POST** (UA-independent, looks like
  WAF), `overpass.osm.jp` empty; mirrors `overpass.kumi.systems` and
  `overpass.private.coffee` alternated between `Dispatcher_Client::request_read_and_idx::timeout`
  ("too busy") and success — a retry loop (up to 10 tries, 8–12 s sleep) got every query
  through on kumi (3–7 tries each). **The area index on kumi is broken today**:
  `area(36000176636)` (東京都) and `area["name"="東京都"]["admin_level"="4"]` returned
  `total: 0`; bbox queries worked every time. All counts below are bbox-based.
- Nominatim: `Access denied` (OSF policy blocks this client). Not used.
- 警視庁 交通事故発生マップ (`www2.wagmap.jp/jikomap/`) is a JS SPA — inspected via the
  Playwright browser; its search backend was queried through the live UI.

## What was actually verified (date, method, live samples)

All checks below were executed on 2026-10-13. Commands: `curl` for pages/PDF/Excel/JSON;
`pdftotext -layout` for text PDFs; raw xlsx parsed via python `zipfile`+ElementTree
(openpyxl not installed); Overpass via `curl --data-urlencode` with retry loop;
wagmap via Playwright click-through + network capture.

---

## 1. Road safety — 警視庁 sources

### 1a. Monthly publication — 区市町村別 PDF (NOT 署別)

Page: 交通人身事故発生状況 —
`https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/tokei_jokyo/traffic_accident.html`
(current issue: 令和8年8月末 = end of Aug 2026; fetched live).

Two PDFs per issue, no text alternative, no CSV:

- `traffic_accident.files/hassei1.pdf` — citywide monthly table: 発生件数 / 死者数 /
  負傷者数 for each month, current + previous year + delta. Live values read:
  Jan–Aug 2026 = 18,868 accidents, 80 deaths, 20,878 injured; same period 2025 =
  19,745 / 85 / 21,852; delta −877 accidents.
- `traffic_accident.files/hassei2.pdf` — **区市町村別**: every 23-ward + Tama city +
  island unit + a 高速道路 row, columns 発生件数 / 死者 / 負傷者. Live samples:
  千代田区 341/3/374, 港区 680/2/775, 大田区 1,020/2/1,105, 足立区 1,065/6/1,159,
  八王子市 1,008/5/1,127, 高速道路 312/4/497; total 18,868/80/20,878.
- Same page family: `jiko5.html` (過去2年間, full-year R7/R6 PDFs), 自転車 statistics,
  初心運転者 statistics (CSV on the open-data catalog, CC BY).

**Machine-readability: PDF only.** Ward counts are extractable at year-end from the
December issue, but this is a parse-PDF pipeline, annual-refresh.

### 1b. Annual 署別 table — Excel, machine-readable — THE workable source

警視庁の統計 令和7年 (2025):
`https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/tokei/reiwa_7.html`

The annual book has a 統計図表 (PDF) and a 統計表 (Excel) part. Traffic tables:

| Table | File | Content |
|---|---|---|
| 図表 第4 | `reiwa_7.files/ktb004.pdf` (2.6 MB) | 交通事故の発生状況（警察署別), PDF |
| **表 第10表** | `reiwa_7.files/kt10.xlsx` (18 KB) | **交通事故発生状況(警察署別), Excel** |
| 表 第13表 | `kt13.xlsx` | 交通事故発生状況(月別) — month × vehicle class, citywide |
| 表 第11–19表 | kt11–kt19 | 違反別 / 当事者別 / 時間帯別 / 天候別 / 死傷者属性 etc. |

**kt10.xlsx parsed live (both sub-tables are on a single sheet, 136 rows):**

- Structure: 総数 → 高速隊 → 方面計 (第1–7・10方面, 第8–9方面) → per-署. Names carry
  furigana in the same cell (e.g. `麴町コウジマチ`) — strip trailing katakana.
- **102 署** (incl. 東京湾岸・東京空港 and the 5 island 署) plus a separate 高速隊 row;
  columns: 署名 | 発生件数 | 死者 | 負傷者総数 | 重傷者 | 軽傷者.
- Year 2025 totals: **30,176 accidents / 134 deaths / 33,401 injured** (高速隊 509,
  第1–7・10方面 21,029, 第8–9方面 8,598, 島部 40).
- 署 extremes: max 町田 753, 小松川 742, 立川 682, 調布 642, 八王子 642; min 東京空港 59,
  尾久 63, 大塚 82, 高輪 97, 駒込 105.
- Refresh: annual; the 令和7年 book appeared in 2026 (修正 notices exist as a separate
  page — e.g. 表33 had a numeric correction announced 令和8年10月).

**Licence:** 警視庁's 22 datasets on the Tokyo Open Data Catalog
(`catalog.data.metro.tokyo.lg.jp`, org `t000022`) are all **CC BY 4.0** — verified via
`package_search?q=&fq=organization:t000022`. The annual book itself is *not* catalogued;
its pages carry no explicit licence line (site's 法的事項 subpage not reachable at
obvious paths — licence of the book files is **unverified**, treat as TMG-copyright
pending owner confirmation).

### 1c. 交通事故発生マップ (地点別) — data exists, licence blocks reuse → reject

Entry: `https://www.keishicho.metro.tokyo.lg.jp/jiken_jiko/hassei/map_annai.html` →
external **`https://www2.wagmap.jp/jikomap/`** (Wagmap platform, ASP.NET EGIS; contract
operator, not 警視庁 itself).

Verified by clicking through the live site (Playwright, 2026-10-13):

- 4 maps: 事故状況別（一般道路 / 高速道路), 時間帯別事故状況, 死亡事故発生地点.
- Layers: 全事故地点 (kernel-density colours + black point dots), 死亡事故 by year
  (2026, 2025), 先週の死亡事故 (weekly, updated Thursdays, with a GIF schematic per
  accident), participant-type layers (二輪車 / 高齢者 / 歩行者 / 子供 / 自転車 /
  事業用車), plus a 警察署 layer.
- Agreement page states: density is **kernel density estimation over 100 m cells**
  converted to per-km²; fatal = death within 24 h; colours' absolute values differ per
  layer (layers are not comparable).
- **Data behind the UI (verified live):** the search POST
  `https://www2.wagmap.jp/jikomap/FreewordSearch/FreewordSearch` returns JSON with
  `count: 93` for 死亡事故（2026年）＋先週, per-record `fid`, free-text description
  (e.g. "タクシーと歩行者の衝突事故（全事故）"), **`x`/`y` WGS84 lon/lat** (e.g.
  139.7383031/35.6677503), attribute layer names; field schema
  (recordkind/txt/address/…); `"csvAuth": {"download": false}` — CSV download disabled.
- **Terms of use (利用許諾 page, accepted to enter):** content copyright 警視庁; base
  maps © Geotechnologies / NTT空間情報 / PASCO; *使用（複製・改変・転用・記載・電磁的加工・
  送信・頒布・二次的使用…）を禁止* beyond personal/statutory use — i.e. bulk retrieval,
  redistribution and derivative datasets are prohibited; exceptions only for printing
  for traffic-safety purposes. Commercial use explicitly forbidden.

**Verdict: reject.** Technically scrapeable, legally unusable for our pipeline. If
point-level accidents are ever wanted, the honest routes are (a) licence request to
警視庁, or (b) waiting for an open-data release (none in the catalog today).

### 1d. What the Tokyo Open Data Catalog has for road safety

Catalog search `交通事故` (420 datasets, 2026-10-13): **no accident-point or accident-rate
dataset citywide.** Present: 警視庁 初心運転者の交通事故状況 (CSV, CC BY), 交通量統計表
(ZIP of CSVs, CC BY — traffic volumes at ~2,160 in/out survey points; **Shift-JIS
encoded**, samples decoded live: 江戸川大橋 111,370 veh/day), 重点取締場所一覧,
音響式信号機設置場所 (CC BY); ward patches: 大田区 区内の年間交通事故 (XLSX, CC BY),
調布市・狛江市 per-year XLS/CSV (CC BY), 品川区 ヒヤリハットマップ情報.

### 1e. 署 → transit-station catchments — rough fit demonstrated (live data)

Data joined: kt10.xlsx 署 counts × OSM 署 coordinates × `data/stations.json`.

- OSM `amenity=police` objects named `…警察署` in bbox 35.50–35.85 N / 139.20–139.94 E:
  **133**; 96 match kt10's 102 署 names after normalization (塚→塚, 麹→麴, strip
  警視庁 prefix); the 6 unmatched are the island 署 (大島/新島/三宅島/八丈島/小笠原 —
  no rail); the other ~37 are Kanagawa/Saitama/Chiba 署. **All 23-ward 署 present.**
- Important discovery about `data/stations.json`: the 1,493 stations are **not all
  Tokyo** — `prefecture` field: 615 in Tokyo (13), 337 Kanagawa (14), 319 Chiba (12),
  222 Saitama (11). 706 stations fall inside the 警視庁 jurisdiction box
  (35.53–35.83 N, 139.33–139.93 E). Any 都/署-level source can only cover those.
- Nearest-署 assignment (km, equirectangular): **median 1.33 km, p90 4.37 km,
  max 10.9 km** for the 706 in-jurisdiction stations; stations per 署: median 6,
  max 26 (調布署). Pearson corr(署 accidents 2025, mapped transit-station count) =
  **0.39** — accident totals scale with road traffic/area, not with rail stations, so
  nearest-署 attribution is a coarse area proxy, not a per-catchment exposure measure.
- Kobans: 1,623 `amenity=police` objects in the extended bbox (1,108 named 交番).
  Within 800 m of a station (706 stations): **median 2 kobans, mean 2.37, max 12;
  90.2 % of stations have ≥1; 69 stations (9.8 %) have none.** All police objects
  within 800 m: median 3, max 19.

---

## 2. Homeless services — proximity framing only (no scores; publication = owner decision)

### 2a. 路上生活者概数調査 — semi-annual per-ward counts, PDF archive

Publisher: 東京都福祉局 (page: `https://www.fukushi.metro.tokyo.lg.jp/seikatsu/rojo/gaisuchosa`).
Archive verified live: **44 issues, Feb 2004 (平成16-2) → Jan 2026 (令和8-1)**, twice a
year (winter Jan/Feb, summer Aug). Method: visual survey by facility managers (roads,
parks, riverbanks, stations), plus a night and terminal-station supplement.

Fields verified from the 令和7年8月 PDF (text layer present, `pdftotext` OK):

- 資料1 路上生活者地域別概数調査一覧 — **per-ward and per-city counts** (今回調査 /
  前回調査 / 増減数): 23区 total 342 (前回 347), 市町村 18; samples: 新宿区 65 (▲11),
  渋谷区 74 (+16), 台東区 38, 墨田区 30, 足立区 19, 豊島区 24 (▲5). Excludes
  national-managed rivers (counted separately by MLIT).
- 資料2 施設別 — counts by manager (都管理 / 区管理 / 市管理) × place type (公園 / 道路 /
  河川 / その他) with a 5-issue history.
- Latest issue 令和8年1月 (read from rendered page images): 23区 307 (前回 342),
  多摩 18; 新宿区 75, 渋谷区 68, 台東区 37, 墨田区 30. **This PDF has no text layer**
  (`pdffonts` empty, `pdftotext` returns nothing — values above read visually from the
  200-dpi render): recent issues are raster; OCR is required for them.
- Context (都 press release 2025-11-04): total incl. national rivers 557 (Aug 2025);
  peak 6,731 (Aug 2004); long-term decline to ~1/12 of peak.

**Machine-readability: PDF only, no CSV/XLSX, and at least the newest issue is
image-only.** Not in the Tokyo Open Data Catalog (catalog `ホームレス` query: 0 datasets;
`路上生活者` matches only unrelated road-works data).

### 2b. 生活実態調査 (national questionnaire survey) — quinquennial, context only

法に基づきおおむね5年ごと (special measures law); latest fieldwork Nov 2021; Tokyo-23
sample 320 respondents; report hosted by 福祉局
(`https://www.fukushi.metro.tokyo.lg.jp/documents/d/fukushi/r4-seikatsuchosa`, PDF
1.9 MB, published 2022). Content is person-level sensitive material (health, income,
life history: e.g. 95.0 % male, mean age 65.1, 43.4 % street-living ≥10 years, mean
work income ≈ ¥53,000/month). **Not a proximity signal; useful only as background
for editorial text. Keep out of any automated scoring.**

### 2c. OSM `amenity=social_facility` — reject as data source

Overpass (extended Tokyo bbox, kumi mirror, ODbL, 2026-10-13):

- `amenity=social_facility`: **3,263 objects** (2,885 nodes, 365 ways, 13 relations).
- Homeless-related subset — `social_facility:for~homeless|street|displaced` or
  ホームレス in name/description: **0 objects**. Tokyo OSM does not tag homeless
  services in this scheme at all.

Conclusion identical to the Bangkok finding (CRTKY-150 §6): OSM cannot model
"proximity of homeless services"; a **hand-curated facility list is the only workable
input**, used as proximity facts only.

### 2d. Known support facilities — verified list (11 entries, wards given)

Neutral framing: these are support/welfare service locations; nothing here implies
anything about neighbourhoods beyond "service exists nearby".

Institutional network (東京都+23区 joint 自立支援センター, one per 5-block rotation,
~5-year terms; sources: 千代田区・中央区 official pages, 都 施設評価書 令和6年3月
`fukushi.metro.tokyo.lg.jp/documents/d/fukushi/04_shisakuhyoukasho`, operators' sites):

1. **自立支援センター (第1ブロック: 千代田・中央・港・新宿) — 中央区**, operating
   令和7年8月–令和12年7月 (中央区 HP).
2. **自立支援センター千代田寮 — 千代田区** (2020-08, previous 1st-block site; 評価書).
3. **自立支援センター荒川寮 — 荒川区** (2020-07, operator 社会福祉法人有隣協会,
   yurin.org).
4. **自立支援センター大田寮 — 大田区仲六郷4-2-12** (2024-03, 有隣協会, yurin.org).
5. **自立支援センター板橋寮 — 板橋区** (2021-03; 評価書; superseded by #6 in block 4).
6. **自立支援センター杉並寮 — 杉並区** (opened 2026-03-23, operator 社会福祉法人東京援護協会,
   緊急一時保護 定員15 + 自立支援 定員35; tokyoengokyokai.or.jp).
7. **自立支援センター江戸川寮 — 江戸川区** (2024-03; 評価書).

NGO / community-based (each verified on the organisation's own site):

8. **認定NPO法人きぼうのいえ — 台東区清川2-29-12** (San'ya area; hospice-style shared
   housing and 24-h care for people left without homes; kibounoie.info).
9. **NPO法人自立支援センターふるさとの会 — 台東区千束4-39-6-4F** (San'ya; shelters
   ふるさと千束館・あさひ館 in 台東区, ふるさとせせらぎ館 and 地域生活支援センターすみだ
   in 墨田区; hurusatonokai.jp).
10. **つくろい東京ファンド — 個室シェルター 中野区沼袋**; ~53 rooms across 中野・豊島・
    練馬・板橋 (housing-first), partner NPO TENOHASI in 池袋/豊島区 (tsukuroi.tokyo).
11. **NPO法人もやい — 新宿区大京町** (poverty/homelessness consultation; address seen
    only on an older community site (tokyohomeless.com) — re-verify current address
    before publication).

Geocoding route when needed: these 11 + ward centroids give a coarse "services within
X km" fact; per-station distances were **not computed** in this pass (owner decision
on publication first).

---

## Per-source verdicts

| Source | Verdict | Why |
|---|---|---|
| 警視庁の統計 第10表 (署別, `kt10.xlsx`) | **fact — adopt if/when road-safety is added** | machine-readable Excel, 102 署 × 6 columns, verified by parsing; annual refresh; explicit licence unverified (book not in CC-BY catalog) |
| Monthly hassei1/hassei2 PDFs (区市町村別) | **fact — secondary** | per-ward counts verified live; PDF-only; annual January refresh from the Dec issue |
| 交通事故発生マップ (wagmap) | **reject** | JSON endpoint exists but TOU prohibits 複製・再配布・二次利用; base-map copyright third-party; CSV download disabled |
| Tokyo catalog 警視庁 datasets (交通量統計表 etc., CC BY) | optional texture | no accident geography; traffic volumes are Shift-JIS CSV, usable as facts |
| Ward accident XLSX patches (大田区/調布市/狛江市, CC BY) | reject for pipeline | patchwork coverage, no citywide standard |
| 路上生活者概数調査 (福祉局, 44 PDFs) | **fact — adopt as background/texture** | per-ward numbers verified in two issues; PDF-only, newest issue raster (OCR needed); not in catalog |
| 生活実態調査 (quinquennial, 2021) | context only | person-level sensitive survey; never a score input |
| OSM `amenity=police` / kobans | **adopt as minor proximity fact** (same doctrine as 02-safety §4a) | 1,623 objects, 1,108 交番 in extended bbox; median 2 kobans within 800 m of a station; ODbL |
| 署→catchment nearest-署 mapping | refinement (method proven) | 96/102 署 geocoded from OSM; median 1.33 km; corr 0.39 — coarse area proxy only |
| OSM `amenity=social_facility` | **reject as data** | 0 homeless-tagged objects despite 3,263 total; use the curated list |
| Curated 11-facility list | **fact — proximity framing only** | every entry verified on primary source; no scores; publication is the owner's separate decision |

## Recommendation per sub-question (ticket scheme: fact / refinement / reject)

- **Road safety: refinement.** Today's Tokyo safety is crime-based and excludes roads
  (`research/02-safety.md` — the accident topic appears nowhere in its formula). The
  workable path if the owner ever wants it: annual 第10表 署別 Excel → nearest-署 (or
  ward-level year-end PDF counts) → a labelled `moderate`-confidence fact ("traffic
  accidents per 署 area, 2025: N"), not a score. The 地点別 map stays rejected on
  licence grounds.
- **Homeless services: fact, framed as service proximity only.** Curated list of 11
  verified facilities (+概数調査 ward counts as neutral context). No scores, no
  "homeless presence" signal of any kind; publication wording is the owner's call.

## Open questions for the owner

1. `data/stations.json` contains 615 Tokyo + 878 Kanagawa/Chiba/Saitama stations
   (prefecture field). Project docs say "Токио 1493 станций" — confirm intended
   coverage before wiring any 都-only source.
2. Licence of 警視庁の統計 book files (not in the CC-BY catalog): acceptable to ingest
   with attribution, or request confirmation from 警視庁?
3. Should 署別/区別 accident facts appear in station/ward page briefs at all
   (editorial decision), and in which wording (accident counts can read as fear
   messaging; neutral "traffic volume/accident statistics" framing suggested)?
4. Homeless-services proximity: which of the 11 facilities to publish, and exact
   wording — separate owner decision per ticket (incl. the もやい address re-check).
5. If the point-level accident map is ever wanted despite the TOU: request a licence
   from 警視庁交通総務課 (contact on map_annai.html), or monitor the catalog for an
   open release.
6. 概数調査 newest PDFs are image-only — is an OCR step acceptable for a
   background-texture source?
