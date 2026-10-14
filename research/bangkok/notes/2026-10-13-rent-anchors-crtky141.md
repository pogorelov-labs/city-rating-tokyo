# Published rent anchors for editorial-rent — KF / JLL / C&W / CBRE / DDproperty (CRTKY-141)

Researched: **2026-10-13**, by the open-data research agent. The ask: find out what
rent anchors the big consultancies and the DDproperty portal actually publish for
Bangkok, map their segments to khets, count how many of the 50 districts get a
quotable anchor, and decide between Outcome A (formalize these sources in
`editorial.json → _meta`) and Outcome B (portals remain the only path).

**TL;DR: none of the five named sources publishes residential RENT levels in 2026.**
What they publish is sale-side: Knight Frank = asking *sale* prices for 3 city
segments; C&W MarketBeat = a per-submarket table that is **average *selling* price
of new launches, not rent** (the word "rent" appears zero times in Q1–Q3 2026
MarketBeats); JLL = qualitative rent commentary with yield/vacancy rates, no
absolute rents; CBRE = residential rents only behind a paid subscription;
DDproperty = demand/search statistics, no rent levels since its 2022 rent index.
The only published table of actual rents by geography found anywhere is a
self-published portal aggregator (Vurel, Sep 2026) covering **31 of 50 khets** —
and its numbers independently match the existing editorial values in the core
(Pathum Wan 38,000; Watthana 32,000 THB/mo, exactly). Verdict: **Outcome B for
rent levels** (portal-derived, keep researcher calibration), **with a cheap
partial Outcome A** — formalize C&W submarket prices + KF segments + JLL
yield/vacancy in `_meta` as *market context / validation* (clearly labeled
sale-price and yield, never as rent anchors).

All fetches below were run by me in this session on 2026-10-13 (curl + pypdf +
site JSON APIs); commands and key outputs are quoted. Nothing here is an
implementation decision — the owner adopts sources.

---

## 1. Knight Frank — Bangkok Condominium Market, Mid-Year 2026 (the 13028 PDF)

- **Located exactly:** the research landing page
  `https://www.knightfrank.co.th/en/research/reports/bangkok-condominium-market-2265`
  (research id **2265**, found via the `/en/research` listing page) links the PDF
  `https://www.knightfrank.co.th/site-assets/research-pdfs/bangkok-condominium-market-mid-year-2026-q2-2026-13028.pdf`
  — document **13028**, "Mid-Year 2026", created **2026-09-02** (PDF metadata:
  `D:20260902145448+07'00'`, InDesign). Downloaded (HTTP 200, 2,153,116 bytes,
  6 pages). Note the ask expected it on `content.knightfrank.com`; the live host
  is `knightfrank.co.th/site-assets` — same document id, so same document.
- **What it contains:** supply (797,995 cumulative units H1 2026, +1.1 % ytd),
  launch sales rates, developer presales, and **asking sale prices** for the three
  location segments CBD / City Fringe / Bangkok Suburbs (Fig. 4). The note under
  Fig. 4 says the segment split is "based on location" and **not** by project
  grade — and no district list is published, so the segment→khet mapping (§7) is
  interpretive.

| KF segment (sale, THB/m²) | 2016 | 2025 | Q2 2026 |
|---|---|---|---|
| CBD | ~225,600 (2016–19 avg) | 188,258 | **191,971** |
| City Fringe | 127,523 | **118,971** | — (annual series) |
| Bangkok Suburbs | 67,698 | **88,076** | — (annual series) |

  CBD–suburban price differential narrowed from 2.83× to 2.14×.
- **Rent content: none.** Text search for rent/rental across all 6 pages gives
  one incidental mention ("associated with rental investment"). I also
  downloaded the two most recent back issues the page still links —
  Q2 2025 (12378.pdf, 5 pp) and Q4 2024 (12019.pdf, 7 pp): likewise **no rent
  section** (only passing words). KF's older "Bangkok Residential Market Report"
  series with rents is retired from the site.
- **License:** final page — *"Reproduction of this report in whole or in part is
  not allowed without prior written approval of Knight Frank Thailand."* Not
  open data; quoting isolated figures with attribution for calibration is a
  normal-usage judgement call for the owner.

## 2. Cushman & Wakefield — MarketBeat: Bangkok Condominium Q1/Q2/Q3 2026

- **Located exactly:** from `cushmanwakefield.com/en/thailand/insights/thailand-marketbeat`
  I pulled the MarketBeat PDF links; the ask's URL resolves to
  `https://assets.cushmanwakefield.com/-/media/cw/marketbeat-pdfs/2026/q1/apac-and-gc/bangkok-condo-mb-1q2026-final_.pdf?rev=9459323b62f9440c97c33c8c79baf295`
  (HTTP 200, 2 pages). Also downloaded **Q2 2026** (`…q2/…bangkok-condo-mb-2q2026-final.pdf`,
  created 2026-07-24) and **Q3 2026** (`…q3/…bangkok-condo-mb-3q2026-final.pdf`,
  created **2026-10-06** — very fresh).
- **The per-area table (page 2, "Market Statistics") is a SALE-price table**, and
  the ask's key question is answered: *"AVG. PRICE CONDOMINIUM WERE LAUNCHED
  2024 – Q1 2026 (THB/SQM)"* — the average asking **selling** price of new
  launches, not rent. `grep -i rent` over the extracted text of all three
  editions hits only "current/currently" — **zero rent mentions**.

Q1 2026 edition (created 2026-04-08), verbatim from `cw_1q26.pdf` page 2:

| Submarket | Supply 2008–Q1 26 | before 2020 | new 2020–Q1 26 | % chg | **Avg price launched 2024–Q1 26 (THB/m²)** | US$/sf |
|---|---|---|---|---|---|---|
| Central Lumpini | 8,814 | 8,025 | 789 | 10 % | **305,000** | 876.82 |
| Narathiswas - Rama 3 | 15,867 | 13,853 | 2,014 | 15 % | **136,315** | 391.88 |
| Phatumwan - Phayathai | 17,753 | 15,253 | 2,500 | 16 % | **373,486** | 1,073.70 |
| Sathorn - Silom | 27,648 | 22,695 | 4,953 | 22 % | **266,333** | 765.66 |
| Sukhumvit | 48,467 | 39,595 | 8,872 | 22 % | **242,130** | 696.08 |
| Riverside | 9,688 | 5,077 | 4,611 | 91 % | **138,580** | 398.39 |
| Outer Area | 389,056 | 260,074 | 128,982 | 47 % | **96,712** | 278.03 |
| Grand Total | 517,293 | 364,572 | 152,721 | 40 % | 137,691 | 395.84 |

Q3 2026 edition updates the same column to "launched 2024–Q2 2026": Riverside
**147,342**, Sathorn-Silom **262,420**, Sukhumvit **242,130**, Central Lumpini
305,000, Outer Area **94,302**, Grand Total **136,195** (supply 524,433 units).
Q2 2026 prose adds a Sukhumvit detail: ~90 % of Q2 launches sat between Sukhumvit
Soi 34 and 63 (Watthana) at a district average ≈ **THB 183,875/m²**.

- **License:** *"©2026 Cushman & Wakefield. All rights reserved … informational
  purposes only."* Not open data.

## 3. JLL — Asia Pacific Property Digest (APPD), Bangkok residential

- **Q2 2026 page exists** at
  `https://research.jllapsites.com/appd-market-report/q2-2026-residential-bangkok/`
  (fetched 200; article dated **August 14, 2026**). Found via the site's own
  WordPress search; the **Q1 2026 page does not exist** — direct slugs
  (`q1-2026-residential-bangkok`, `1q2026-…`, `q1-2026-bangkok-residential`) all
  return 404, the site search finds only the Q2 page, and the REST API
  (`/wp-json/wp/v2/posts?categories=341`) shows no other Bangkok APPD report.
- **Content is commentary, no absolute rents.** All numeric facts I could
  extract: vacancy ≈ **4.1 %**, gross yield **5.4 %**, luxury condo stock
  **74,922 units**, pipeline ~1,900 units. Rent statements are directional only:
  "Prime apartments remained strong in Q2 2026", "**Gross rents in the CBA
  stayed stable**", "rents projected to stay flat y-o-y". The disclaimer on the
  page scopes it to *"Bangkok's high-end and luxury residential market"*, with
  geographies **CBA** (Central Bangkok Area) and **Central East** — not districts.
- The full APPD digest PDF (which historically carried a THB/m² rent table) is
  not linked from the page and not on the open web for 2026 (DuckDuckGo finds
  only 2015–2018 copies on Scribd/naredco).
- **License:** site Terms of Use — *"download content for non-commercial,
  personal use only"*; reproduction without JLL's written permission prohibited.

## 4. CBRE Thailand

- `cbre.co.th` **blocks both curl and WebFetch with HTTP 403** (verified twice).
  Content retrieved via the Exa fetcher instead.
- **Free tier has no residential rents.** "Bangkok Overall Figures Q1 2026"
  (May 21, 2026) and "Q2 2026" (Aug 18, 2026) give one qualitative residential
  paragraph each (12 launches in Q1; launches +265 % y-o-y in Q2 off the
  post-earthquake low base); rents are discussed for **offices** only.
- **Rents live in the paid product:** "Bangkok Property Report" sits under
  `…/thailand-paid-subscription-research/bangkok-property-report` ("For the
  report subscription or more information, please contact CBRE") — 9 sections,
  >1,000,000 condominiums covered, incl. secondary-market transactions. Not
  publicly quotable without a subscription.

## 5. DDproperty quarterly

- `ddproperty.com` **returns HTTP 403** to curl (consistent with the repo's
  standing finding that portals block automated access —
  `research/bangkok/00-overview.md`).
- Their 2026 quarterly releases (reached via Money & Banking, 2026-04-27 and
  2026-07-20, plus a DDproperty-branded summary on oceanwwp.com) are
  **demand statistics**: rental lead-to-view ratio 15.6 % H1 2026 (vs 8.7 % H1
  2025), Bangkok rental demand +9 % QoQ Q1 2026, most-searched subdistricts per
  price band (e.g. Thung Maha Mek/Sathon #1 for 40–60k THB/mo rentals). **No
  rent levels by district.**
- The last artifact with an actual rent *number* is the **"Thailand Property
  Rental Market Index"** inside the DDproperty Q2/2565 (2022) Market Report
  (Bangkok rent index 90 points, 2018=100) — an index, and **4 years stale**.

## 6. Bonus find — Vurel "Bangkok Condo Rents and Yields by Zone, 2026"

Not among the ask's sources, but it is the only published rent table I found,
so I verified it directly: `https://vurel.io/blog/bangkok-condo-rents-by-zone-2026`
(fetched 200, updated **28 Sep 2026**; data window 29 Aug – 28 Sep 2026; medians
of live listings across 8 portals — LivingInsider "Lease" rows included, Hipflat
excluded; per-zone ≥ 1,900 live rentals). No license statement on the page;
self-published, so treat as a cross-check, not a source of record.

Bangkok zones (provincial zones omitted) with mapping to khets — **31 of 50
khets directly covered**, 19 not covered by any zone:

| Vurel zone | Median asking rent (THB/mo) | Rent ฿/m² | Khets mapped |
|---|---|---|---|
| Chidlom - Ploenchit | 38,000 | 754 | Pathum Wan |
| Sathorn - Silom | 35,000 | 653 | Bang Rak, Sathon |
| Khlong Toei - Rama 4 | 35,000 | 721 | Khlong Toei |
| Sukhumvit | 32,000 | 671 | Watthana, Khlong Toei |
| Rama 3 - Yan Nawa | 31,000 | 450 | Yan Nawa, Bang Kho Laem |
| Ratchathewi - Phaya Thai | 29,000 | 657 | Ratchathewi, Phaya Thai |
| Ari - Saphan Khwai | 23,000 | 607 | Phaya Thai |
| Rama 9 - Ratchada | 21,000 | 569 | Huai Khwang, Din Daeng |
| Kaset - Ratchayothin | 20,000 | 575 | Chatuchak, Lat Phrao (edge) |
| On Nut - Bearing | 19,000 | 552 | Phra Khanong, Bang Na |
| Ladprao | 18,000 | 571 | Lat Phrao, Chatuchak (edge) |
| Thonburi - Taksin | 17,500 | 468 | Thon Buri, Bangkok Yai, Khlong San (edge) |
| Bang Sue - Prachachuen | 14,000 | 400 | Bang Sue |
| Pinklao - Bang Phlat | 14,000 | 423 | Bangkok Noi, Bang Phlat |
| Srinakarin - Pattanakan | 13,000 | 414 | Prawet, Suan Luang |
| Ramkhamhaeng | 13,000 | 429 | Bang Kapi, Bueng Kum, Wang Thonglang |
| Bang Na - Lasalle | 12,000 | 407 | Bang Na |
| Bang Khae - Phetkasem | 12,000 | 400 | Bang Khae, Phasi Charoen, Nong Khaem (edge) |
| Don Mueang - Laksi | 12,000 | 414 | Don Mueang, Lak Si |

Not covered (19): Phra Nakhon, Pom Prap Sattru Phai, Samphanthawong, Dusit, Bang
Khen, Sai Mai, Taling Chan, Thawi Watthana, Bang Bon, Bang Khun Thian, Chom
Thong, Rat Burana, Thung Khru, Saphan Sung, Khan Na Yao, Khlong Sam Wa, Min
Buri, Nong Chok, Lat Krabang — exactly the low-rent periphery where the current
editorial values are already anchored to townhouse/apartment levels.

**Independent validation of editorial.json:** Vurel Chidlom-Ploenchit 38,000 =
`editorial.json` Pathum Wan `rent_1br` 38,000; Vurel Sukhumvit 32,000 = Watthana
32,000. Sathorn-Silom 35,000 vs editorial Bang Rak 26,000 / Sathon 25,000 —
editorial is deliberately lower (1-bed "typical" vs all-unit listing median).
Core calibration looks sound.

## 7. Segment → khet mapping (consultant geographies)

C&W inner submarkets → khets (12 districts get a specific number; the other 38
share one "Outer Area" blend — 94,302 ฿/m² in the Q3 2026 edition):

| C&W submarket | → khets |
|---|---|
| Central Lumpini | Pathum Wan (Lumpini side; Ratchathewi edge) |
| Phatumwan - Phayathai | Pathum Wan, Ratchathewi, Phaya Thai |
| Sathorn - Silom | Bang Rak, Sathon |
| Sukhumvit | Watthana, Khlong Toei |
| Narathiswas - Rama 3 | Sathon (east), Yan Nawa, Bang Kho Laem |
| Riverside | Bang Rak (river side), Khlong San, Thon Buri (edge), Bang Kho Laem, Bangkok Yai (outer edge) |
| Outer Area | remaining 38 khets (single blended number) |

KF segments → khets: KF publishes **no district list** ("classifications are
based on location", PDF p.4); the conventional reading is CBD ≈ Pathum Wan +
Watthana/Khlong Toei core + Sathon/Bang Rak, City Fringe ≈ Phaya Thai, Ratchathewi,
Din Daeng, Huai Khwang, Phra Khanong, Yan Nawa belt, Suburbs = the rest. That is
my interpretation, not KF's. JLL: CBA ≈ the same core; "Central East" ≈ Rama 9 /
Huai Khwang belt. All three geographies are too coarse to assign a per-district
rent from.

## 8. Coverage scorecard — who of the 50 khets gets a quotable anchor

| Source | Freshness (fetched 2026-10-13) | What it quotes | Khets covered |
|---|---|---|---|
| Knight Frank Mid-Year 2026 (doc 13028, created 02.09.2026) | ~6 weeks | Sale asking price, 3 city segments | 50 in 3 buckets — **not rent** |
| C&W MarketBeat Q3 2026 (created 06.10.2026) | ~1 week | Sale price of launches, 7 submarkets | 12 specific + 38 blended — **not rent** |
| JLL APPD Q2 2026 (14.08.2026) | ~2 months | Qualitative rents + yield 5.4 %, vacancy 4.1 % | luxury CBA/Central East only, no levels |
| CBRE free figures (21.05 / 18.08.2026) | fresh | Qualitative residential, office rents | 0 (residential rents paid-only) |
| DDproperty quarterly (Apr/Jul 2026) | fresh | Demand shares, top subdistricts | 0 rent levels |
| **Any published RENT level** | — | — | **Vurel only: 31/50** (data window ends 28.09.2026) |

## 9. Verdict — Outcome A or B?

**Outcome B for rent levels: yes — the portals (or portal-derived data) remain
the only path to actual rents.** No consultancy publishes rentable numbers for
free in 2026; the two per-area tables the ticket asks about (C&W) and the
segment series (KF) are **sale prices**, which cannot substitute for a
rent_1br/rent_2br anchor.

**Partial Outcome A is still worth doing, cheaply and honestly labeled:** the
C&W submarket table (Q3 2026), KF's CBD/City Fringe/Suburbs series and JLL's
yield (5.4 %) / vacancy (4.1 %) are stable, citable, dated figures that
document the *market context* the researcher calibrated against — a
`_meta.rent.context_sources` entry (clearly typed "sale prices / yields, not
rents") would make the editorial method more auditable at zero data risk. Vurel
is usable only as an external cross-check (its core numbers already match
`editorial.json` exactly), not as a source of record: self-published, no
license, monthly-moving medians.

## 10. Open questions for the owner

1. Add the "context_sources" block (C&W Q3 2026 submarket prices, KF mid-year
   segments, JLL Q2 2026 yield/vacancy) to `editorial.json → _meta.rent`, typed
   as sale-price/yield context — yes/no? All three are ©-restricted, quoted
   figures only.
2. Is quoting ©-restricted report figures (with attribution, figures only) in
   `_meta` acceptable for the site, or should `_meta` reference the reports
   without reproducing numbers?
3. Subscribe to CBRE's paid Bangkok Property Report? It is the only candidate
   with district-grade rent data; cost unknown (contact form).
4. Vurel as a public cross-check in the methodology page (its Pathum Wan /
   Watthana values match editorial exactly), or keep it private?
5. C&W/KF publish quarterly — should `_meta` pin the exact PDF URLs + creation
   dates (as done in §1–2) so future audits can re-fetch the same documents?

Sources (all fetched 2026-10-13):
`knightfrank.co.th/en/research/reports/bangkok-condominium-market-2265` +
`…/site-assets/research-pdfs/bangkok-condominium-market-mid-year-2026-q2-2026-13028.pdf` (+ Q2 2025 / Q4 2024 back issues),
`assets.cushmanwakefield.com/-/media/cw/marketbeat-pdfs/2026/{q1,q2,q3}/apac-and-gc/bangkok-condo-mb-…pdf`,
`cushmanwakefield.com/en/thailand/insights/thailand-marketbeat`,
`research.jllapsites.com/appd-market-report/q2-2026-residential-bangkok/` (+ WP REST API, + terms-of-use),
`cbre.co.th/insights/figures/bangkok-overall-figures-q1-2026`, `…/bangkok-overall-figures-q2-2026`, `…/thailand-paid-subscription-research/bangkok-property-report` (via Exa; direct 403),
`en.moneyandbanking.co.th/2026/257691/`, `en.moneyandbanking.co.th/2026/240222/` (DDproperty Q2/Q1 2026),
`ddproperty.com/คู่มือซื้อขาย/ddproperty-thailand-property-market-report-q2-2565-64761` (2022 rent index; site 403),
`vurel.io/blog/bangkok-condo-rents-by-zone-2026`.
