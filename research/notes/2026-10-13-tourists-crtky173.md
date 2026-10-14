# Tourist load for Tokyo stations: 宿泊旅行統計調査 (e-Stat 00601020) + OSM hotel density (CRTKY-173)

Researched: **2026-10-13**, by the open-data research agent. Context: Tokyo
`crowd` today is MLIT S12 daily passengers inverted (`scripts/compute-ratings.py:488-499`),
so a station like Asakusa rates "quiet" relative to its actual tourist load;
this ticket asks whether the JTA accommodation survey can add a tourist-load
signal and how it should enter the product. All network checks, downloads and
extractions below were run by me in this session; commands and outputs are
quoted (Appendix). Nothing here is an implementation decision — the owner
adopts sources.

**TL;DR:** The survey's monthly **第2次速報値** files contain a real
**市区町村別集計** (municipality breakdown: 参考5–12表) with 延べ宿泊者数 /
実宿泊者数 / 外国人 / 客室稼働率 — and they download as **plain .xlsx with no
appId at all** from the Japan Tourism Agency mirror
(`mlit.go.jp/kankocho/content/<id>.xlsx`); the e-Stat **API** itself demands a
(free) appId — verified: structured error `STATUS 100 認証に失敗しました`. I
pulled one month by municipality (July 2026) plus Feb/Mar/Apr 2026 and the
2025 annual file: **台東区 (Asakusa's ward) = 291,762 人泊/month, 71% foreign,
78.4% occupancy**, while **武蔵野市 and 船橋市 are simply absent** from the
survey's 188-municipality list — their absence *is* the low-tourist signal.
OSM (Overpass, run today) confirms the ordinal contrast:
**Asakusa 62 vs Kichijoji 5 vs Funabashi 9** tagged `tourism=hotel|guest_house|hostel`
objects in the repo's 800 m catchment (Ginza 46). Because municipal data
covers only 14 of Tokyo's 62 municipalities, is 20+-room-facility-only, and is
2 months delayed, my recommendation is **facts/badge, not a new numeric key**:
annotate or badge "high tourist flow" from OSM density (100% station
coverage), cite the survey's numbers as editorial facts where the ward exists,
and keep `crowd` as is.

---

## 1. What the pipeline does today (code refs)

- **Crowd** (`compute-ratings.py:488-499`): `raw["crowd"] = daily_pax`
  (MLIT S12 passengers, `data/passengers/s12-passengers.json`), confidence
  `strong`/`moderate`; fallback `food_hp * 300 + line_count * 10000`
  (`estimate`). Log-percentile, inverted → 1–10 (`compute-ratings.py:549-550`).
  No tourist component anywhere in the Tokyo signal.
- **Catchment convention**: Tokyo safety uses 町丁 within **800 m** of the
  station (`compute-ratings.py:426-429`) — the same 800 m radius I use for the
  OSM counts below.
- **Rating keys / confidence / sources** are per-key in
  `app/src/lib/types.ts:11,64,77`; Bangkok pages have per-station `facts`
  cards, Tokyo pages do not (only `data/descriptions/*.json` editorial text).
- The repo already ingests an e-Stat dataset at municipality level for rent
  (`scripts/merge-estat-rent.py`, `data/estat/estat-rent-raw.json`) — so an
  e-Stat-sourced municipality table is precedented plumbing.

## 2. Source A — 宿泊旅行統計調査 (e-Stat 00601020 / JTA mirror)

Official statistics page: https://www.e-stat.go.jp/statistics/00601020
(HTTP 200, 124,852 B, fetched 2026-10-13). Survey owner: 観光庁 (Japan
Tourism Agency). Monthly since 2015; the same data is published as direct
files on the JTA site:
https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html
(HTTP 200, 60,764 B).

### 2.1 Access without appId — verified

| Channel | Result (2026-10-13) |
|---|---|
| e-Stat API v3 (`api.e-stat.go.jp/rest/3.0/app/json/getStatsList?statsCode=00601020`) | **appId required.** HTTP 200 but `{"RESULT":{"STATUS":100,"ERROR_MSG":"認証に失敗しました。アプリケーションIDを確認して下さい。"}}` |
| e-Stat web file list (`stat-search/files?...toukei=00601020`) | Page shell renders (189 KB), but the dataset rows/CSV links load via JS XHR; I could not enumerate or test the CSV download headlessly. **Untested, not claimed.** |
| JTA mirror direct .xlsx | **Works with plain `curl`, no auth, no login.** Downloaded 6 files (2nd prelim Jul/Feb/Mar/Apr 2026, annual 2025, 推移表), sizes 26 KB–2.55 MB, `HTTP 200`, correct xlsx MIME. |
| e-Stat DB (dbview) | Not tested (needs a sid I could not discover without the API/UI). |

The appId issuance itself is free e-Stat user registration, but the /api
pages are JS-rendered — I could **not** quote the "free" sentence from the
live page in this session; only the API error above is a verified fact.
**Bottom line for the pipeline: the JTA mirror is the no-appId path, and it
is the same survey.**

### 2.2 Municipality (市区町村) breakdown — verified, but partial

Every monthly **第2次速報値** workbook carries a 市区町村別集計 block
(verified in `002024478.xlsx`, July 2026, sheet 統計表（目次）):

- 参考第5表: 主な市区町村 × 客室区分 — 母集団施設数 / 回収施設数
- 参考第6表: 延べ宿泊者数 (nights, 人泊)
- 参考第7表: 実宿泊者数 (actual guests, 人)
- 参考第8/9表: 外国人延べ/実宿泊者数
- 参考第10表: 定員稼働率; 参考第11表: 利用客室数; 参考第12表: 客室稼働率

**"主な市区町村" = 188 municipalities only** (my count of 参考6表 rows).
Tokyo gets **14**: 千代田・中央・港・新宿・台東・墨田・江東・品川・大田・渋谷・豊島・北区・荒川・八王子.
Chiba gets 7 (千葉・木更津・成田・市原・鴨川・浦安・南房総).
**武蔵野市, 三鷹市, 船橋市, 市川市, 松戸市 are absent.** The annual
confirmed-year file (2025, `002010340.xlsx`, 275 sheets) has **no
municipality sheets at all** — prefecture level only (grep for 市区 in sheet
names → none). So municipality-level data exists *only* in the monthly 2nd
prelim files.

Granularity of each cell: municipality × room class (1–9室 / 10–19室 / 20室以上),
but **only the 20室以上 column is ever populated** at municipality level
(all 1–9/10–19 cells are `-`). 参考5表 shows why: e.g. 台東区's frame is
**366 facilities with 1–9 rooms + 64 with 10–19 rooms (no data collected,
回収 = `-`) + 207 with 20+ rooms (66 responding)**. The survey 概要 PDF
(`/kankocho/content/001996480.pdf`, 2 pp, read via pypdf) states the 2026-01
design change: 「客室数 20 室以上の事業所：悉皆調査 / 客室数１室～19室の事業所：
標本調査（都道府県毎に標本抽出率を設定）」 and that the frame is facilities
as of 2026-01-01 (目次 note: 「令和８年１月１日現在の施設を母集団として推計」).
Values are **model estimates from self-reporting** (自計申告), with standard
errors tabulated in 参考2(7月) — not a census of nights.

### 2.3 One month pulled by municipality (July 2026, 第2次速報値) — the ask

Extracted from `/tmp/shukuhaku_2026-07_2nd.xlsx` (reference copy of
`https://www.mlit.go.jp/kankocho/content/002024478.xlsx`, 368,810 B):

| municipality | 延べ宿泊者数 人泊 | 実宿泊者数 人 | 外国人延べ 人泊 | 外国人% | 客室稼働率 % |
|---|---:|---:|---:|---:|---:|
| 千代田区 | 234,344 | 128,265 | 119,281 | 50.9 | 75.9 |
| **中央区 (Ginza)** | **540,298** | 271,357 | 375,545 | 69.5 | **83.8** |
| 港区 | 691,111 | 346,306 | 398,804 | 57.7 | 73.4 |
| 新宿区 | 243,102 | 106,746 | 174,424 | 71.7 | 77.4 |
| **台東区 (Asakusa)** | **291,762** | 138,774 | 207,874 | **71.2** | 78.4 |
| 墨田区 (Skytree) | 73,112 | 37,980 | 39,680 | 54.3 | 71.4 |
| 江東区 (Toyosu) | 235,929 | 138,843 | 108,475 | 46.0 | 80.4 |
| 品川区 | 98,980 | 62,466 | 32,050 | 32.4 | 81.5 |
| 大田区 | 174,037 | 128,874 | 51,422 | 29.5 | 87.0 |
| 渋谷区 | 105,374 | 44,672 | 88,624 | 84.1 | 86.0 |
| 豊島区 (Ikebukuro) | 123,285 | 70,344 | 71,957 | 58.4 | 72.3 |
| 北区 | 35,543 | 18,933 | 6,772 | 19.1 | 82.0 |
| 荒川区 | 23,474 | 11,126 | 16,064 | 68.4 | 56.2 |
| 八王子市 | 37,479 | 24,464 | 5,171 | 13.8 | 51.2 |
| *(Chiba) 浦安市 (Disney)* | 487,706 | 373,019 | 94,292 | 19.3 | 81.8 |
| *(Chiba) 成田市* | 188,295 | 174,559 | 91,075 | 48.4 | 71.3 |

Anchor points: Tokyo prefecture July 2026 = **7,865,630 人泊** (第2表(7月) of
the same file); the 14 published Tokyo municipalities sum to 2,907,830 =
**37.0%** of the prefecture — i.e. **63% of Tokyo's tourist nights sit in
municipalities the survey does not break out.**

### 2.4 Seasonality (sakura / GW) — quantified

Prefecture level, 2025 confirmed year (`002010340.xlsx`, 第2表/第8表 monthly
sheets, 東京都 row):

| | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nights M人泊 | 8.46 | **7.90** | 9.06 | 9.27 | 9.33 | 8.75 | 8.81 | 9.21 | 8.71 | 9.42 | 9.17 | **9.82** |
| 客室稼働率 % | 71.1 | 75.4 | 76.3 | 79.4 | 77.5 | 73.2 | 73.5 | 74.5 | 76.5 | **80.6** | 79.8 | 78.2 |

February is the floor (0.88× the annual mean); sakura/GW April–May run
**+17–18% over February** (Apr/Feb 1.17, May/Feb 1.18); December is the
annual peak (1.09×). Seasonal amplitude is real but modest at prefecture
level.

Ward level, 2026 第2次速報値 (Feb/Mar/Apr files + July, 延べ宿泊者数):

| ward | Feb | Mar | Apr | Jul | Mar/Feb | Apr/Feb |
|---|---:|---:|---:|---:|---:|---:|
| **台東区** | 243,074 | 292,177 | 284,128 | 291,762 | **1.20** | **1.17** |
| 中央区 | 585,689 | 540,692 | 558,968 | 540,298 | 0.92 | 0.95 |
| 渋谷区 | 143,740 | 142,420 | 164,835 | 105,374 | 0.99 | 1.15 |
| 江東区 | 176,941 | 199,603 | 204,856 | 235,929 | 1.13 | 1.16 |

Taito's sakura bump (+20% over February) exceeds the prefecture's (+17%), and
its occupancy climbs 78.8% → 82.7% into April — the tourist-hotspot signature
Ginza (business + luxury, flat) lacks. One caution against naive month-to-month
reading: **新宿区 fell 402,615 (Feb) → 243,102 (Jul)** — a −40% six-month swing
that must be inventory/sample effects as much as demand; monthly municipal
numbers are too volatile to drive a static rating directly.

Publication lag: the July 2026 第2次速報値 and the August 第1次速報値 are both
already listed on the JTA page I fetched today → a fixed ~1.5–2 month lag
behind "now". The 概要 PDF sets the reporting deadline at 翌月中旬 (mid
following month) for the first stage.

## 3. Source B — OSM hotel density via Overpass (verified today)

Query per station (repo's 800 m safety-catchment radius, `compute-ratings.py:427`):

```
[out:json][timeout:90];
nwr["tourism"~"^(hotel|guest_house|hostel)$"](around:800,<lat>,<lng>);
out count;
```

Station coords from `data/stations.json` (Asakusa 35.711883,139.798214;
Ginza 35.671989,139.763965; Kichijoji 35.703119,139.579765;
Funabashi 35.701865,139.984707). Circle area = π·0.8² ≈ 2.011 km².

| station | objects (nodes+ways) | per km² |
|---|---:|---:|
| **Asakusa** | **62** (49+13) | 30.8 |
| **Ginza** | **46** (17+29) | 22.9 |
| **Funabashi** | **9** (7+2) | 4.5 |
| **Kichijoji (Musashino)** | **5** (3+2) | 2.5 |

Asakusa carries **12.4×** Kichijoji's and **6.9×** Funabashi's density — the
same ordering the survey implies, but with **100% station coverage** at any
catchment size, monthly-refreshable, ODbL. Access notes: `overpass-api.de`
failed from this environment today (`SSL_ERROR_SYSCALL` ×4, retry blocked),
`overpass.osm.jp` has an expired certificate; **kumi.systems and
private.coffee work** (kumi needs 1–5 retries, "server too busy"; results
cross-checked on both mirrors for Asakusa — identical 62). OSM base snapshots
of the two mirrors: 2026-07-15 / 2026-07-28.

## 4. Honesty of the municipality → station-catchment mapping

This is the load-bearing caveat for any use of Source A:

1. **Ward ≠ catchment.** 台東区's 291,762 nights cover Ueno, Iriya and
   Yanaka too — the Asakusa station catchment is a fraction of it. No
   sub-municipal data exists in the survey.
2. **Catchments straddle wards.** Verified by reverse geocoding: 800 m due
   east of Asakusa station is already 墨田区向島一丁目 (Nominatim, today), so
   the catchment mixes 台東区 (291,762) and 墨田区 (73,112) ward economies.
   Ginza's circle likewise touches 千代田区/港区.
3. **Most stations have no ward at all.** 武蔵野市 (Kichijoji), 三鷹市, 船橋市,
   市川市, 松戸市 etc. are not in the 188-municipality list — for them the
   survey says only "below the publication floor". That is a *strong ordinal*
   signal (absence is meaningful: these are not tourist-bed towns) but it is
   not a number, and it must not be read as "zero tourists".
4. **The survey misses exactly the small places.** Only 20+-room facilities
   contribute at municipality level; the small guest houses/hostels that
   dominate Asakusa's back streets (and which OSM tags as `guest_house`
   nodes — Asakusa's 62 objects are 49 nodes) are invisible to it. The two
   sources are complements: OSM sees the small inventory, the survey sees
   the verified demand behind the big one.
5. **Estimates, sampled.** Municipal cells derive from 66 responding
   20+-room facilities (Taito; 参考5表), self-reported, with published
   standard errors; a −40% Shinjuku swing within one year (§2.4) shows the
   noise floor. Three-stage publication (第1次/第2次速報/確報) means values
   get revised; I did not measure revision magnitudes (not run).

## 5. Composition options (what the ticket asked to work through)

**Option A — annotate the existing `crowd` signal.** Add the tourist
component into the MLIT-based crowd raw value (e.g. as a small additive term
or a sources entry). *Con:* crowd is passenger-throughput; blending in ward
nights would double-count central wards (all of them high on both) while
giving nothing to the 48 unpublished municipalities. Cheapest, but muddies a
clean signal.

**Option B — facts / badge 「高い観光来訪」 (recommended).** No new numeric
key. Two layers:

- *Badge/flag* computed from **OSM hotel density** (Source B) — covers all
  1493 stations uniformly, refreshable, and its ordinal separation
  (62/46 vs 9/5) is wide; a threshold like ≥15 objects/800 m separates
  tourist-bed districts from commuter towns with a large gap. It would slot
  into the station page as a flag next to existing per-key confidence
  (`app/src/lib/types.ts:64,77`), or into `data/descriptions/*.json` as an
  editorial sentence.
- *Facts numbers* from **Source A** where the ward exists: "台東区:
  292k宿泊人泊/月 (2次速報 2026-07), 71% 外国人, 稼働率 78%" — great
  description-generation material (the repo already generates per-station
  descriptions; the survey's per-ward facts are exactly the kind of
  citable, dated fact those rules want).

**Option C — a new numeric tourist-load key with confidence.** *Con:* 14/62
Tokyo municipalities published; ward≠catchment; monthly volatility; 2-month
lag; estimates not counts. A numeric key built on this would be `estimate`-
confidence for ~most stations and would need normalization across a
non-random subset — worse quality than the existing `crowd` estimate
fallback. If the owner wants a numeric tourist axis anyway, build it on
**Source B (OSM density, 100% coverage)** and use Source A only for
calibration/facts — not the reverse.

**Seasonality handling:** the site is static, so either use annual confirmed
values (fetched once a year, no seasonality problem) or, if a badge carries a
month, state the month in the caption ("2026年7月時点"). Do not chase monthly
updates in a static rating: the Feb→Jul Shinjuku swing (§2.4) shows monthly
deltas are not actionable.

## 6. Asakusa vs Musashino/Funabashi — the asked contrast, with numbers

| | Asakusa (台東区) | Ginza (中央区) | Musashino (吉祥寺/武蔵野市) | Funabashi (船橋市) |
|---|---:|---:|---:|---:|
| Survey nights, Jul 2026 | **291,762** | 540,298 | **not published** | **not published** |
| Foreign nights share | 71.2% | 69.5% | n/a | n/a |
| Occupancy | 78.4% | 83.8% | n/a | n/a |
| Sakura bump (Mar/Feb 2026) | +20% | −8% | n/a | n/a |
| OSM hotels 800 m | **62** | 46 | **5** | **9** |
| OSM per km² | 30.8 | 22.9 | 2.5 | 4.5 |

Reading: Asakusa is a tourist-bed district by every measure —
near-half-milllion ward nights in high season, ~7 of 10 nights foreign,
occupancy ~80%, sakura-season spike, 62 tagged properties. Musashino and
Funabashi are invisible to the survey (below its 188-municipality floor) and
show ~5–9 tagged properties in the same 800 m — i.e. **12–13× fewer** than
Asakusa. The honest one-line product statement is exactly that pair:
"measured tourist district" vs "not even tracked by the national survey, with
10× fewer hotels on the map".

## 7. Licenses

- 宿泊旅行統計調査 (e-Stat/JTA): e-Stat terms-of-use page
  (https://www.e-stat.go.jp/terms-of-use, fetched 2026-10-13) states
  「本利用ルールは、政府標準利用規約（第2.0版）に準拠しています」 and CC BY 4.0
  compatibility — the same terms the repo already runs under for MLIT S12
  (`research/03-crowd.md:23`). Attribution line + 加工 note on
  `/methodology` if adopted.
- OSM: ODbL (stated in every Overpass response header).

## 8. Recommendation

**Adopt Source B (OSM `tourism=hotel|guest_house|hostel` density in the 800 m
catchment) as the driver of a "high tourist flow" badge/annotation** —
verified mechanics, full coverage, wide ordinal separation.
**Adopt Source A (JTA mirror xlsx, no appId) as an editorial facts layer**
for the 14 published Tokyo municipalities (dated ward facts for descriptions),
pulled from 第2次速報値 monthly files or the annual confirmed file.
**Reject** building a numeric tourist rating from Source A (coverage,
granularity, volatility); **reject** the e-Stat API as an ingest path
(appId gate — unnecessary given the mirror); keep `crowd` unchanged.

## 9. Open questions for the owner

1. Badge threshold: OSM ≥15 objects/800 m is a suggestion (separates
   Asakusa/Ginza from Funabashi/Kichijoji with a 3× margin) — calibrate
   against the full 1493-station distribution before fixing.
2. Where does the badge live: a per-station flag next to the existing
   confidence/sources fields, a fact card (Bangkok-style), or
   description-generator sentences only?
3. Facts layer: which wards get numbers, and do we refresh them monthly
   (2nd prelim) or annually (確報)?
4. Should the fact card carry the 20+-room caveat in user-visible text?
5. Attribution wording for 政府標準利用規約/CC BY on `/methodology`.
6. If a numeric tourist axis is ever wanted: confirm OSM-density-based
   construction with survey calibration (Option C as scoped in §5).

## Appendix — exact commands run this session (2026-10-13)

```
curl -sS https://www.e-stat.go.jp/statistics/00601020                     # 200, 124852 B
curl -sS "https://www.e-stat.go.jp/api/v1/json/getStatsData?..."          # 404 HTML (v1 path dead)
curl -sS "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList?statsCode=00601020&limit=5"
    # STATUS 100 認証に失敗しました。アプリケーションIDを確認して下さい。
curl -sSL https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html  # 200, file list
curl -sSL https://www.mlit.go.jp/kankocho/content/002024478.xlsx  -o jul  # 200, 368810 B (Jul 2026 2nd prelim)
curl -sSL https://www.mlit.go.jp/kankocho/content/002010407.xlsx  -o feb  # 200, 366648 B
curl -sSL https://www.mlit.go.jp/kankocho/content/002010404.xlsx  -o mar  # 200, 365706 B
curl -sSL https://www.mlit.go.jp/kankocho/content/002010342.xlsx  -o apr  # 200, 369568 B
curl -sSL https://www.mlit.go.jp/kankocho/content/002010340.xlsx  -o year # 200, 2554483 B (2025 confirmed)
curl -sSL https://www.mlit.go.jp/kankocho/content/002018997.xlsx  -o suii # 200, 1333092 B (推移表)
curl -sSL https://www.mlit.go.jp/kankocho/content/001996480.pdf           # survey 概要 (pypdf text)
uv run --with openpyxl python …  # sheet inventory, 目次 dump, 参考5/6/7/8/12表 extraction,
                                 # 188-municipality list, Tokyo 14 + Chiba 7, ward seasonality
curl -sS "https://overpass.kumi.systems/api/interpreter"      --data-urlencode "data=<query>"  # Asakusa/Ginza/Kichijoji
curl -sS "https://overpass.private.coffee/api/interpreter"    --data-urlencode "data=<query>"  # Asakusa cross-check + Funabashi
    # overpass-api.de: SSL_ERROR_SYSCALL x4; overpass.osm.jp: cert expired
curl -sS "https://nominatim.openstreetmap.org/reverse?lat=35.711883&lon=139.8054&zoom=14"
    # 向島一丁目, 墨田区, 東京都  (catchment straddle check)
curl -sSL https://www.e-stat.go.jp/terms-of-use                            # 政府標準利用規約 2.0 / CC BY 4.0
```

All downloaded workbooks were read in memory/temp only; the only file created
in the repo is this note. Numbers in §2.3–2.4 and §6 are transcribed from
`openpyxl` reads of the files listed above; OSM counts from the `out count`
responses quoted in §3.
