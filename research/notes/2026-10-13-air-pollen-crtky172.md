# Air quality (そらまめくん) + cedar pollen as a seasonal factor — Tokyo (CRTKY-172)

Researched 2026-10-13 by an open-data research agent. Method: live HTTP calls
(curl / python), the SPA bundles of soramame.env.go.jp (JS inspection for
undocumented endpoints), the NIES tenbou archive API, and the Bangkok air note
`research/bangkok/notes/2026-10-13-air-crtky146.md` (read this session) for the
cross-city implementation pattern. Every number below was read or computed in
this session unless explicitly marked otherwise. Rail-station frame =
`app/src/data/stations.json` (1493 records, verified: 615 Tokyo pref-13,
222 Saitama, 319 Chiba, 337 Kanagawa).

Question from the ticket: station inventory (23 wards + Greater Tokyo); hit the
API live for several Tokyo stations and attach a response; network density vs
the 1493 stations (median/max distance); is per-station interpolation honest;
honest metric (annual mean vs % days over the Japanese standard vs seasonal
peak; pollen: seasonal sum and onset shift); new category vs facts on station
pages; joint assessment with Air4Thai.

---

## TL;DR

- **MOE そらまめ君 (soramame.env.go.jp) works live, no registration, JSON**:
  hourly PM2.5/SPM etc. per station for all 85 Tokyo stations, Sep–Oct 2026 in
  one 6.3 MB call (85,510 records, median completeness 99.1 %). Rolling window
  is **12 months** (Oct 2025 → HTTP 400 with a JSON error; Nov 2025 → OK),
  request span ≤ 3 months. Bulk monthly ZIP via `POST /soramame/download`.
- **Density is good — the opposite of Bangkok**: 291 PM2.5 monitors in the 4
  Kanto prefectures; from the 1493 rail stations the nearest monitor is
  **median 1.72 km, mean 2.34 km, max 17.1 km** (rural Bōsō peninsula). Tokyo
  only: median **1.43 km**, max 10.2 km (Okutama valley); 77 % of Tokyo
  stations within 2 km, 98 % within 5 km; **all 23 wards host monitors**.
- **Tokyo air is clean and flat**: rolling 12-month citywide mean
  (Nov 2025 → Oct 2026, 315 citywide days) = **8.24 µg/m³** vs the Japanese
  standard of 15 (annual) / 35 (24 h); only **14 of 24,162 station-days
  (0.058 %) exceeded 35 µg/m³**. A "% days over standard" metric reads ~0 —
  it is a dead metric here, unlike Bangkok's burn season. Annual mean vs the
  15 µg/m³ standard + a live "now" value is the honest pair.
- **MOE has no real-time pollen at all**: the はなこさん automatic network
  (120 sites) was abolished FY2021; what remains on env.go.jp is PDFs
  (Durham-method surveys, bud surveys). The ticket's 花粉観測実証事業 has no
  live public data portal I could find. Real options: **Tokyo Metropolitan
  Government Allergy Navi (live, 12 sites, daily counts, archive back to
  2001)** — adopt-shaped; **Weathernews** — free CSV/API but *internet
  publication requires prior contact*, and the 2022 download host did not
  resolve today; **tenki.jp (日本気象協会)** — proprietary forecasts, reject.
- **Pollen is a facts-chip, never a rating**: 2025 season sums at the 12 TMG
  sites were 0.6–9.7 個/cm²; 2026 season cumulative is 5,291 (Chiyoda) to
  **22,937 (Ōme)** — a three-orders-of-magnitude inter-annual swing plus a
  strong west-Tama gradient. A percentile across stations would be noise.
- **Recommendation: not a new rated category** — same shape as Bangkok:
  a city-level air fact + live chip, plus a Feb–Apr pollen chip with the
  season sum and per-site spread; optional per-station enrichment only where
  a *background* monitor is ≤ 1 km (roadside monitors must not be mixed in).

---

## 1. Soramame API — verified live

The UI is a Vue SPA; the API manual is served as static JSON/HTML that the SPA
loads: `/data/apiManual/linkInfo.json` → pages `/data/apiManual/1..4.html`
(all fetched live, HTTP 200).

**What the manual says** (read from the four pages):

- One endpoint for hourly data:
  `https://soramame.env.go.jp/soramame/api/data_search?Start_YM=YYYYMM&End_YM=YYYYMM&TDFKN_CD=13&SKT_CD=…&REQUEST_DATA=PM2_5`
  — `TDFKN_CD` prefecture code 01–47 (13 = Tokyo), `SKT_CD` optional
  comma-separated station codes, `REQUEST_DATA` any of
  `SO2,NO,NO2,NOX,CO,OX,NMHC,CH4,THC,SPM,PM2_5,SP,WD,WS,TEMP,HUM`.
- Units: PM2.5 µg/m³; **SPM mg/m³** (0.012 mg = 12 µg/m³); gases ppm.
- Data is **速報値 (preliminary)**: "速報値は…後日修正されることがありますので、
  調査研究等でのデータ利用には確定値を入手されることをおすすめします" — for
  research use they recommend the confirmed values from data.go.jp.
- Window rule: "APIで取得可能なデータ期間は現在月から遡って1年間のうち3か月以内
  になるように設定してください" — lookback ≤ 1 year, span ≤ 3 months per request.
- Rate limits: "高頻度のアクセスを行うような利用はお控えください…リクエストを
  制限させていただく場合があります".
- Copyright (manual §2-1): held by 環境省 + the local governments + NIES
  jointly; **for non-national-station data the local government should be
  contacted**; national-station data follows env.go.jp rules
  (env.go.jp/mail.html). No registration, no personal info collected (§3-2).
- The site footer (app.js bundle, `js/app.c4669626.js`) states: 「APIも公開して
  おります。**個人利用は無償で利用可。サービス提携を目的とした利用は個別に
  ご相談ください。**」 — free for personal use; service-partnership use is
  by-consultation. MOE site content generally sits under
  公共データ利用規約 (PDL1.0, attribution required) per env.go.jp/mail.html.

**Live hits (2026-10-13, all HTTP 200):**

| Request | Result |
|---|---|
| `data_search?Start_YM=202609&End_YM=202610&TDFKN_CD=13&REQUEST_DATA=PM2_5` | 6.34 MB, 85,510 records, **83/85 stations** report PM2.5, median completeness 99.1 % over Sep 1 – Oct 12 |
| `…&SKT_CD=13104010&REQUEST_DATA=PM2_5,SPM,NO2` (国設東京（新宿）) | 1,006 records; NO2 comes back as `"-"` when absent |
| `…Start_YM=202510…` | **HTTP 400** `{"code":"PG-05-001","message":"パラメータが不正です。直近1年以内の年月を指定してください。Start_YM","status":400}` |
| `…Start_YM=202511…` | 720 records (712 non-null) → **the 12-month floor is Nov 2025 today** |
| `POST /soramame/download?DL_KBN=3&Target_YM=202609&TDFKN_CD=13&SKT_CD=13104010` | HTTP 200, ZIP 12,170 bytes → `202609_13_13104010.csv`, **Shift-JIS**, all 18 parameters hourly for the month |

**Attached live response excerpt** (station 13101010 千代田区神田司町, as
returned, 2 of 85,510 records):

```json
[{"SKT_CD":"13101010","SKT_DATE":"2026/09/01","SKT_TIME":"01","PM2_5":"3"},
 {"SKT_CD":"13101010","SKT_DATE":"2026/09/01","SKT_TIME":"02","PM2_5":"4"}]
```

**Undocumented (SPA-discovered) static feeds**, also live:

- `/data/sokutei/noudoAll/YYYY/MM/DD/HH.csv` — all-station snapshot per hour;
  metadata (`…/metadata.json`) says latest `2026/10/13 08:00`, oldest
  `2021/01/25`. The `2026/10/13/08.csv` fetch returned **1,585 stations
  nationwide** with station code, all pollutants, 測定局名称, 住所, 問い合わせ先,
  局種別, 地域コード, 都道府県コード, 市区町村名 — **no coordinates**.
- `/data/sokutei/existence/YYYY/MM/DD/HH.csv` — which stations reported.

**Confirmed values**: data.go.jp (org_2000 = MOE) is the manual's recommended
source; I could not query it — `www.data.go.jp` 301-redirects to
`data.e-gov.go.jp` and the old CKAN path `/api/3/action/...` 404s there (live).
The practical confirmed-value source found instead is NIES (below).

## 2. NIES 環境展望台 (tenbou.nies.go.jp) — confirmed archive + station registry with coordinates

Tenbou publishes the same national network as **confirmed values** plus a full
station registry. Backend discovered from `download.js`:
`POST /download/api/yearlist.php` (`types=["td","tj","tk","tm"]`),
`POST /download/api/searchfile.php` (`type`, `prefs`, `years`, `materials`),
`POST /download/api/archivedownload.php` (`type`, `file`).

- Year coverage (live `yearlist.php`): monthly/annual **td 1971–2023**,
  hourly **tj 2009–2023**, **tk 1976–2023**, station registry **tm 1971–2023**
  → confirmed data runs ~2.7 years behind (2023 latest on 2026-10-13).
- `TM20230013.zip` (Tokyo FY2023) → `TM20230013.txt` (Shift-JIS, 87 stations):
  station code matching soramame codes, **lat/lon in deg/min/sec**, address,
  測定局区分 (1 background / 2 roadside), 継続状況, per-pollutant
  測定有無 flags incl. `PM25_測定有無`, and distances to up to 6 roads.
- The server is **flaky**: intermittent `curl (52) Empty reply from server`
  (roughly 1 in 2–3 requests); scripted retries with sleeps are mandatory.

**License caveat**: tenbou's copyright page says everything is © 国立環境研究
所 (NIES) under normal copyright law — I found **no open-data license grant**
on the pages read this session. For *our* purpose it is best treated as a
metadata/registry helper; the underlying measurement data remains MOE/local
government/NIES per the soramame manual, and attribution should name the
originators, not NIES.

## 3. Station inventory — computed from live + registry data

From the live hourly snapshot (`noudoAll/2026/10/13/08.csv`):

| Frame | Monitors |
|---|---|
| Nationwide | 1,585 |
| Tokyo (code 13) | **85** — 56 in the 23 special wards (**23/23 wards covered**), 29 Tama/islands; 48 一般局 + 37 自排局 |
| Greater Tokyo (1都3県: 13+11+12+14) | **359** (Saitama 77, Chiba 106, Tokyo 85, Kanagawa 91) |

From the FY2023 registry (TM files, 継続状況=0 active): Tokyo 87 active, **86
with PM2.5** (47 background / 38 roadside / 1 other), 55 with PM2.5 in the 23
wards; Kanto 375 active, **291 with PM2.5** (198 background / 92 roadside).
The small live-vs-registry delta (85 vs 87) is the annual snapshot vs today's
reporting set — normal.

**Roadside share is large (44 % of Tokyo PM2.5 monitors)**: 日比谷交差点,
第一京浜高輪, 永代通り新川 — these measure traffic corridors. Any average or
nearest-monitor assignment must either filter 測定局区分=1 or label roadside
values explicitly; mixing them into a residential "air at your station" number
would be methodologically wrong.

## 4. Density vs the 1493-station frame — computed

Distance from each rail station (stations.json lat/lng) to the nearest active
PM2.5 monitor (haversine; monitors = 291 FY2023 registry records with
converted coordinates):

- **All 1493 stations: median 1.72 km, mean 2.34 km, max 17.09 km**
- ≤ 1 km: 23.6 %; ≤ 2 km: 59.1 %; ≤ 3 km: 78.9 %; ≤ 5 km: 91.4 %
- Worst are rural fringes, not the metro core: 江見 (emi) 17.1, 田浦 16.3,
  鴨川 (awa-kamogawa) 14.5, 大多喜 14.2, 湯河原 13.9, 浪花 13.8 km
- **Tokyo-only (615 stations): median 1.43 km, mean 1.62 km, max 10.23 km**
  (川井/kawai, Ōme river valley); worst cluster is Okutama/奥多摩 (8.5–10.2 km);
  ≤ 2 km: 473/615 (77 %); ≤ 5 km: 603/615 (98 %)
- Per-prefecture medians: Tokyo 1.43, Kanagawa 1.76, Saitama 2.23, Chiba 2.62

**Verdict on interpolation.** Unlike Bangkok (9/50 districts, median 4 km),
the Tokyo network is dense enough that a nearest-monitor or IDW value in the
23 wards is *geographically* defensible — but it remains an estimate, and
roughly half the nearest monitors are roadside. The repo's percentile
machinery would rank interpolation + siting artifacts, not districts or
stations. Density here removes the *coverage* objection to per-station facts,
not the *honesty* objection to treating estimates as measurements.

## 5. What metric is honest

Standards verified from the primary source (平成21年9月9日 環告33,
env.go.jp/kijun/taiki4.html): PM2.5 環境基準 = **annual mean ≤ 15 µg/m³ AND
24-h mean ≤ 35 µg/m³**.

From the pulled rolling 12 months (Nov 1 2025 → Oct 12 2026, 85 stations,
315 days with ≥ 40 reporting stations):

- **Citywide mean of daily means: 8.24 µg/m³** — comfortably below 15; Tokyo
  passes its own standard. (Computed from 24,162 station-days; monthly means
  range 4.9 in Sep to 10.2 in Jul; Feb 9.9, i.e. the pollen months are
  slightly elevated but nowhere near a Bangkok-style season.)
- **% of days over 35 µg/m³: 14/24,162 = 0.058 %** (worst city day in the
  window: 21.3 µg/m³ on 2026-02-05). This metric **reads ~0 and cannot
  discriminate** in Tokyo today — the exact inverse of Bangkok, where it is
  the headline number.

Recommended metric set (mirrors the Bangkok decision logic):

1. **Rolling/calendar annual mean vs the 15 µg/m³ standard** at city level —
   computable live from the 12-month window; calendar-year values later from
   the confirmed archive (2009–2023 available).
2. **Live "now" chip** — one `data_search` call per refresh (median-of-
   reporting-stations hourly PM2.5).
3. **Pollen seasonal fact (Feb–Apr, plus grass/weed season)** — seasonal sum
   個/cm² at the 12 TMG sites with the west-Tama vs central spread, and
   last-vs-this-year context (below).
4. **"Onset shift" (start-of-season date drift)** — *feasible but not done*:
   the TMG archive is daily HTML tables back to 平成13 (2001); computing onset
   (first day ≥ 1 個/cm²) over 25 seasons is a small parser job, deferred here.
   Not verified this session beyond the table format of `archive/r7/total.html`
   (141 rows, 12 sites, e.g. `1/6 月 0.0 0.0 …`).

## 6. Pollen sources — what is actually open

- **MOE real-time: none since 2021.** Press release 110339 (2021-12-24):
  はなこさん (120 automatic counters since 2002, kafun.env.go.jp) abolished
  「令和3年をもって廃止」 with the stated rationale 「民間気象事業者において
  全国に花粉観測機を設置し、環境省よりも多数の地点における花粉の飛散状況の
  情報提供が行われており」. The current MOE pollen page
  (env.go.jp/chemi/anzen/kafun, live) offers only PDFs: Durham-method
  花粉飛散量調査 (スギ/ヒノキ, volunteer-counted slides) and annual 雄花花芽
  調査 results. **The 花粉観測実証事業 named in the ticket has no live public
  data portal I could find** (web search; MOE's own page links to private
  services). Reject for the pipeline; usable as citation material.
- **Tokyo TMG Allergy Navi (hokeniryo1.metro.tokyo.lg.jp/allergy/pollen) —
  live and adopt-shaped.** 12 observation sites (千代田, 葛飾, 杉並, 北, 大田,
  青梅, 八王子, 多摩, 町田, 立川, 府中, 小平); daily counts in 個/cm² as HTML
  tables; cedar/cypress Jan–mid-May, grass/weeds late-May–Nov; documented
  caveats on the page (5 Tama sites skip weekends with equal-division
  correction; the 5 central sites are batch-measured with a delay). Current
  2026 season cumulative: **5,291.0 (千代田) … 22,936.7 (青梅)** 個/cm². The
  2025 season (summed by me from `archive/r7/total.html`, 129 days): 0.6–9.7
  個/cm² — i.e. **a ~3-orders-of-magnitude inter-annual swing** and a strong
  west-Tama > 23-wards gradient. Archive back to 平成13 = 2001.
  License: the pages carry no explicit open-data license; treat as TMG
  website content with attribution — owner should confirm before republication.
- **Weathernews ポールンロボ** (release jp.weathernews.com/news/38969,
  2022-02-07): ~1,000 citizen sensors, hourly counts per municipality,
  「CSVファイルやAPI連携でどなたでも取得が可能」, free — **but** terms require
  attribution 「ウェザーニュースの「ポールンロボ」で観測されたデータである
  ことを明示してください」 and **prior contact for commercial use or
  internet publication** 「営利・商用目的でのご利用や、インターネットを通じた
  成果物の公開をご検討の場合はお問い合わせください」. The 2022-era download
  host `pollen.weathernews.com` did not resolve from this network today, so
  current availability is unverified. → **hold; owner decision** (a permission
  conversation, not an API integration).
- **日本気象協会 tenki.jp/pollen — reject.** Live page confirms it is a
  proprietary seasonal forecast product (2026 season closed; 2027 forecast
  first report published 2026-09-30); no data license, no machine access.

## 7. Composition options

| Option | Verdict |
|---|---|
| **A. New rated category** (7th Tokyo category, percentile across 1493 stations) | **Reject.** Values would be monitor-derived estimates for most stations (median 1.4–1.7 km), ~44 % of Tokyo monitors are roadside, and the discriminating metric (% days over standard) reads 0.06 % — the percentile would rank siting and interpolation artifacts. Breaks the 6-category weight balance for no signal. Same conclusion as Bangkok. |
| **B. City-level air fact + live chip** on `/tokyo` and station pages ("annual mean 8.2 µg/m³ vs JP standard 15 · now N µg/m³ · 10 monitors in your ward") | **Recommend.** One honest number, one API call per refresh, attribution "環境省 大気汚染物質広域監視システム そらまめ君 (+各地方公共団体)" per PDL1.0. |
| **C. Per-station enrichment** where a *background* monitor is ≤ 1 km | Optional add-on; only with 測定局区分 filtering and explicit "monitor in ~X m" framing. ~24 % of all Kanto stations qualify today (≤ 1 km to any monitor; background-only share lower). |
| **D. Pollen chip (Feb–Apr)**: season sum vs last season at nearest TMG site ("cedar season: X 個/cm² here vs 22.9k at Ōme; last year 9.7") | **Recommend** as the seasonal-factor implementation — it is where Tokyo's air story actually varies in time. Scrape TMG HTML (small, stable tables), cite TMG Allergy Navi. |

## 8. Joint pattern with Bangkok Air4Thai (CRTKY-146)

Reading the Bangkok note side by side, the two cities converge on one
implementation shape:

| Aspect | Air4Thai (Bangkok) | そらまめ君 (Tokyo) | Shared pattern |
|---|---|---|---|
| Hourly JSON API, no key | yes (`webV2/history/api/data.php`) | yes (`soramame/api/data_search`) | one no-registration endpoint |
| Rolling window | ~2.5–3 months | **12 months** (span ≤ 3 mo/call) | window forces own cron accumulation for season metrics |
| Bulk archive | gdcatalog annual CSVs (unreachable from our network) | NIES tenbou confirmed 2009–2023 + monthly ZIP | a second, slower "confirmed" source |
| Station list with coords | not in API (geocoded by hand) | **official registry with coords** (TM files) | JP is strictly better here |
| Density verdict | fatal (9/50 districts) | fine (median 1.7 km) | same *composition* verdict anyway |
| Metric that discriminates | % days ≥ 37.5 (burn season) | annual mean vs 15; % days is dead | pick per-city metric, same chip UI |
| Composition | city fact + live chip, not a category | same + pollen chip | one component serves both cities |
| License | "Open Data Common" (gdcatalog) | PDL1.0 + mixed provenance (MOE/local gov/NIES), attribution required | attribution line per city |

So the recommendation "not a rated category; city-level seasonal fact + live
chip (+ optional near-monitor enrichment)" is now **cross-city evidence**, not
a one-off judgment — a single `AirQualityFact` component parameterized per
city covers both tickets.

## 9. Adopt/reject summary

| Source | Verdict | Why |
|---|---|---|
| soramame `soramame/api/data_search` (hourly JSON) | **adopt** | live, free, no key, 12-month window, 83/85 Tokyo stations at 99 % completeness |
| soramame `POST /soramame/download` (monthly ZIP) | **adopt** | bulk per-month CSV, Shift-JIS (decode needed) |
| soramame `noudoAll/…/HH.csv` snapshots | **adopt** | station inventory + "now" values, no coords |
| NIES tenbou TM registry (coords) | **adopt** | official lat/lon, PM2.5 flags, annual cadence; flaky server → retries |
| NIES tenbou confirmed tj/td archive | **hold/fallback** | 2009–2023 confirmed values; © NIES pages, no explicit reuse license; server flaky |
| data.go.jp confirmed values | **not verified** | e-gov CKAN path 404s; needs a fresh look from the owner |
| MOE pollen (実証事業/はなこさん残存物) | **reject** | no real-time feed since 2021; PDFs only |
| Weathernews ポールンロボ | **hold** | free but internet publication needs prior consent; host unverified today |
| tenki.jp (日本気象協会) pollen | **reject** | proprietary forecasts, no open license |
| TMG Allergy Navi pollen | **adopt (license check first)** | live, 12 sites, daily counts, 25-season archive, HTML tables |

## 10. Open questions for the owner

1. **Attribution/provenance for non-national stations** — the soramame manual
   says local-government data use should be cleared with each local
   government; is the blanket attribution line sufficient for us, or does the
   owner want explicit clearance?
2. **Preliminary (速報値) vs confirmed values** — is the live preliminary feed
   acceptable for published facts (with a "preliminary" note), or should
   published annual figures wait for / fall back to the confirmed archive?
3. **TMG pollen license** — confirm reuse terms of Allergy Navi content
   before the pollen chip ships.
4. **Weathernews permission** — worth one email (free data, hourly, ~1,000
   sensors, municipality granularity) if we want denser pollen coverage than
   TMG's 12 sites; otherwise skip.
5. **Onset-shift fact** — do we want the 25-season onset computation from the
   TMG archive (small parser, ~25 pages), or is the seasonal sum + YoY
   contrast enough for v1?
6. **Roadside policy** — if option C is taken, confirm the ≤ 1 km +
   background-only rule and its user-facing wording.
