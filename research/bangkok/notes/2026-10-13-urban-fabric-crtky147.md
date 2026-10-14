# Bangkok urban fabric — sidewalk walkability, arterial exposure, cleanliness (CRTKY-147)

Researched: **2026-10-13**, by the open-data research agent. All Overpass queries and all
web checks below were executed live in this session; commands and outputs are quoted or
summarized exactly. Nothing here is an implementation decision — the owner adopts sources.

**TL;DR.** OSM can measure Bangkok's sidewalk fabric *relatively* but not absolutely:
in the city bbox only **16.5 %** of footway ways (49 % of their length) carry
`footway=sidewalk`, and only **8.3 %** of primary/secondary/tertiary ways carry any
`sidewalk=…` mapping tag — "разреженно" is confirmed by the numbers. The relative
khet contrast is strong and deliberate-looking (Pathum Wan 5.7 km of tagged sidewalk
per km² vs Bang Kapi 0.24 — a 24× gap; arterial `sidewalk` tagging 25.4 % vs 0.8 %),
but absolute walkability scores from this are unsafe. Arterial exposure of station
zones is measurable with the repo's own coordinates: **88 % (117/133) of the 133
station zones have a primary/trunk way within 300 m** (median 10 ways; 16 zones with
none) — low discriminative power as a binary, real variance in the counts (0–54).
Cleanliness: **no honest open data today** — Traffy Fondue monthly CSVs exist but are
registration-gated and carry no stated licence; `data.bangkok.go.th` is unreachable
from this environment (again, same as CRTKY-139); the only CC-BY item is a citywide
waste-*tonnage* table on data.go.th whose file URL could not be extracted through the
portal's WAF.

---

## Access notes (what worked, what didn't)

- Overpass mirrors were very flaky this session: `overpass-api.de` 406 on POST and
  frequent 000s, `overpass.kumi.systems` / `overpass.private.coffee` alternated 504 /
  000 / 200 — every query went through with a retry loop (up to 12 tries × 4 mirrors,
  GET for short queries, POST for the geometry dump; helper at /tmp/overpass.sh).
- **Mirror base timestamps varied across responses: `2026-05-31` and `2026-07-28`**
  (different mirrors at different replication ages) — all numbers below are from
  snapshots between those dates, i.e. 2.5–4.5 months behind live OSM.
- Syntax findings for Overpass 0.7.62.11 (cost two debugging rounds, recorded here):
  `make stat n=count(ways), m=sum(length()); out;` **works** (aggregators need type
  arguments — `count()` bare is a parse error, `count(if: …)` is **not** supported on
  this version, so conditional counts were done as separate filter statements);
  inside `for(t["k"])` a bare `_` does not parse.
- Khet discovery: Bangkok khets are `admin_level=6` boundary relations, but their
  `name:en` carries a ` District` suffix (`Pathum Wan District`, rel 92063;
  `Khlong Toei District`, rel 2938033; `Bang Kapi District`, rel 2939952) — a
  `name:en~"^(Pathum Wan)$"` filter silently matches nothing (first Q2 run returned
  all-zero stats and was rerun via `area(3600<rel_id>)`).
- `data.bangkok.go.th`: unreachable again from this machine (`curl` → HTTP 000,
  connection failure; same finding as CRTKY-139). Its indexed pages were inspected
  through search-engine renders instead.
- `data.go.th` (national DGA portal): WAF-blocked for this client — `curl` gets
  "Access Denied" (Cloudflare), WebFetch gets 403. The harvest mirror
  `catalog-dga.data.go.th` **is** reachable and confirmed the metadata (below).
- `traffy.fondue.co.th` unreachable (000); `bangkok.traffy.in.th` and
  `publicapi.traffy.in.th` reachable (200); `citydata.traffy.in.th` reachable (200,
  JS SPA dashboard); `policy.bangkok.go.th/traffy/...` 403 for both curl and WebFetch.
- Station coordinates read from `app/src/data/bangkok/stations.json` (133 areas,
  `_meta.generated = 2026-09-30`, `source: scripts/bangkok/build.py`).

Bbox used throughout (city bbox from the ticket): `13.4907,100.3279,13.9556,100.9383`.

---

## 1. Sidewalk network in OSM — city bbox (Overpass, live)

Query skeleton (per metric; GET, retries):

```
[out:json][timeout:300];
way["highway"="footway"]["footway"="sidewalk"](13.4907,100.3279,13.9556,100.9383);
make m key="sidewalk_tagged_footways", n=count(ways), meters=sum(length()); out;
/* … one statement per metric … */
way["highway"~"^(primary|secondary|tertiary)$"]["sidewalk"](…); out tags;   /* value distribution */
```

Results (Overpass base 2026-07-28, kumi mirror; run 2026-10-13):

| Metric (ways in city bbox) | Ways | Length |
|---|---:|---:|
| `highway=footway` + `footway=sidewalk` | **3,287** | **1,167.8 km** |
| all `highway=footway` | **19,958** | **2,365.5 km** |
| `highway=pedestrian` | **477** | **65.4 km** |
| nodes `highway=crossing` | 17,017 | — |
| ways `highway=footway` with any `crossing=*` | 2,651 | — |

Derived shares:

- **sidewalk-tagged share of footway ways: 3,287 / 19,958 = 16.5 %**;
  by length: 1,167.8 / 2,365.5 km = **49.4 %** (ways that do get tagged tend to be long).
- Against the Bangkok expectation «разреженно» (sparse): confirmed — only ~3.3 k
  explicitly-mapped sidewalk segments for a 1,569 km² city, i.e. roughly 0.74 km of
  mapped sidewalk per km² citywide.

**Caveat for any scoring use (important).** Bangkok OSM sidewalks are under-mapped and
inconsistently modelled (sidewalks as separate ways, as `footway=left/right` lanes on
carriageways, or not at all; `sidewalk=separate` on roads conventionally means "mapped
elsewhere"). Low absolute numbers ≠ no sidewalks. Only the *relative* contrast between
areas with comparable mapper attention is usable, and even that is confounded.

## 2. Three contrasting khets (Overpass, area queries, live)

```
area(3600092063)->.a;   /* Pathum Wan  = rel 92063  */
area(3602938033)->.b;   /* Khlong Toei = rel 2938033 */
area(3602939952)->.c;   /* Bang Kapi   = rel 2939952 */
way["highway"="footway"]["footway"="sidewalk"](area.a); make m key="pw_sidewalk", n=count(ways), meters=sum(length()); out;
/* … same battery per area … */
```

| Metric | Pathum Wan (CBD) | Khlong Toei (dense inner) | Bang Kapi (outer residential) |
|---|---:|---:|---:|
| area km² (pipeline facts) | 8.37 | 12.99 | 28.52 |
| `footway=sidewalk` ways / km | 210 / **47.9 km** | 80 / **17.9 km** | 35 / **6.9 km** |
| → tagged sidewalk km per km² | **5.72** | **1.38** | **0.24** |
| all footway ways / km | 1,356 / 105.7 km | 859 / 83.0 km | 240 / 26.2 km |
| sidewalk share of footway ways | 15.5 % | 9.3 % | 14.6 % |
| `highway=pedestrian` ways / km | **119 / 21.8 km** (skywalks) | 2 / 0.5 km | 6 / 0.8 km |
| crossing nodes | 555 | 255 | 67 |
| arterial ways (pri+sec+ter) | 394 | 337 | 393 |
| arterial ways with any `sidewalk` tag | **100 (25.4 %)** | **42 (12.5 %)** | **3 (0.8 %)** |

Read-out: a 24× contrast in tagged-sidewalk density (5.72 → 0.24 km/km²) and a 32×
contrast in arterial tagging (25.4 % → 0.8 %) across three khets of similar size-class.
Pathum Wan's 119 pedestrian ways / 21.8 km is the elevated skywalk network
(Ratchaprasong/Siam) — a real fabric feature that only OSM captures this cheaply.

## 3. `sidewalk=…` tagging on arterials — city bbox (live, from the same session's
`out tags` dump of all tagged arterial ways, 1,349 ways)

| Class | total ways | tagged | both | left | right | yes | separate | no |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | 5,239 | 474 (9.0 %) | 14 | 442 | 0 | 0 | 0 | 18 |
| secondary | 6,183 | 560 (9.1 %) | 240 | 300 | 8 | 1 | 1 | 10 |
| tertiary | 3,981 | 315 (7.9 %) | 185 | 91 | 3 | 0 | 0 | 36 |
| **total** | **15,403** | **1,349 (8.8 %)** | 439 | 833 | 11 | 1 | 1 | 64 |

- **Marked share (`both|left|right|yes|separate`): 1,285 / 15,403 = 8.3 %** of
  Bangkok's primary/secondary/tertiary ways.
- Anomaly worth knowing before anyone "uses" this: `left` dominates (833 of 1,285,
  incl. 442 of 474 on primaries) — a tagging-convention artefact (likely a mapper who
  tags the sidewalk side relative to the way direction), not street reality. Treat
  per-value composition as noise; only the tagged/un-tagged split is meaningful.

## 4. Arterial exposure of station zones — 300 m, all 133 zones (live)

Method (the ask's "грубо по станциям из stations.json"): one Overpass dump of the
whole arterial class with geometry (7.8 MB JSON, `out geom`; base 2026-07-28):

```
way["highway"~"^(trunk|primary|trunk_link|primary_link)$"](13.4907,100.3279,13.9556,100.9383);
out geom;
```

then a local computation (python3, equirectangular projection, point-to-segment
haversine distance) against the 133 `areas[].lat/lng` of
`app/src/data/bangkok/stations.json`. Script output:

- arterial ways fetched: **8,670** (primary 5,239, primary_link 1,946, trunk 1,043,
  trunk_link 442);
- **117 / 133 zones (88.0 %) have at least one primary/trunk(+link) way within 300 m**;
- per-zone arterial ways within 300 m: **median 10, p10 0, p90 32, max 54**;
- nearest-arterial distance: **median 6 m**, max 605 m (BTS/MRT corridors in Bangkok
  run along the arterials — the 6 m median is real, not a bug);
- the 16 zones with **no** arterial within 300 m: Ban Thap Chang, Bang Pho, Bang Son,
  Charoen Nakhon, Chatuchak, Hua Mak, Itsaraphap, Kamphaeng Phet, Khlong San,
  Krung Thep Aphiwat / Bang Sue, Min Buri Market, Ratchadamri, Ratchaprarop,
  Sanam Chai, Taling Chan (list truncated at 15 in script output).

**Methodology caveat, verified on a sample:** `stations.json` coordinates are *zone*
points; for at least one zero-hit zone the centroid is demonstrably off the platform —
`ratchadamri` zone point (13.73947, 100.53945) sits 564 m from Rama I Rd / 580 m from
Phloen Chit Rd (both `primary` in OSM), while the actual BTS platform is on
Ratchadamri Rd. So 88 % is a **conservative, centroid-based** figure; platform-based
counts would be higher and sharper. Direction of use: this measures *exposure to
traffic corridors* (noise/dust side of urban fabric), not a walkability amenity.

## 5. Cleanliness — candidate sources, checked live

1. **Traffy Fondue monthly CSVs** (`publicapi.traffy.in.th`) — the city's 311-style
   complaint platform (BMA + NECTEC), type taxonomy includes waste/garbage classes.
   - Endpoint alive: `curl https://publicapi.traffy.in.th/` → `OK v0.0.71` (200).
   - **Access is registration-gated**: the download listing/CSV endpoints require
     `name/org/purpose/email` (verified against the `Kinosaur/transparent-city`
     backend docs on raw.githubusercontent.com, which implements exactly this flow:
     `…/teamchadchart-stat-api/download/bangkok_monthly?…&name=…&org=…&purpose=…&email=…`);
     unauthenticated probes from here: legacy CSV → 404, listing without fields → 400,
     unknown paths → 404. **Matches the ticket's «за регистрацией».**
   - ~60 monthly CSVs since 2021-09, 24 columns incl. `type` (hierarchical),
     `district` (khet), `coords` (lon,lat), state, durations — i.e. per-khet ขยะ
     complaint counts with geography *are constructible* — but only after registering,
     and **no licence statement was found anywhere in the reachable pages**; BMA's own
     catalog entry for Traffy summaries says **«License not specified»**.
   - `citydata.traffy.in.th` (200) is a JS dashboard, not a file source;
     `policy.bangkok.go.th/traffy/` (BMA's complaint analysis center, 1.28 M records
     searchable, filterable by type incl. water-flooding etc.) → **403** from this
     environment; web UI only in any case.
2. **data.bangkok.go.th (BMA open-data portal)** — unreachable from this machine
   (HTTP 000, twice today). Indexed metadata (via search-engine renders) shows the
   relevant uploads exist: Traffy complaint summaries (`/dataset/traffy-fondue`,
   monthly, **«License not specified»**), GPS points of public garbage bins
   (organization สำนักสิ่งแวดล้อม = Environment Dept), per-district garbage-hauling
   spreadsheets (mostly 2021, **«License not specified»**). None verifiable or
   downloadable from here.
3. **data.go.th (national portal)** — WAF-blocked for this client (curl "Access
   Denied", WebFetch 403). One directly relevant dataset is documented in its
   rendered page and confirmed in the reachable DGA harvest catalog
   (`catalog-dga.data.go.th`, package index CSV): **«ข้อมูลปริมาณขยะมูลฝอย จำแนกตามเขตการปกครองกรุงเทพมหานคร»**
   (municipal-waste tonnage by Bangkok khet), org BMA, yearly updates,
   **license "Creative Commons Attributions"**, marked High Value Dataset
   (package id `731a8cb0-d563-45ca-93ae-52e3de47e474`). The resource file URL could
   not be extracted without the CKAN API (WAF); a browser session would get it.
   Note this is **waste volume**, a collection/density proxy — not street cleanliness.
4. BMA Environment Dept performance stats (street-sweeping km, river-waste tonnes)
   exist as annual/budget-year **PDFs on `webportal.bangkok.go.th`** (403 from here;
   confirmed via search-engine render of `environmentbma/page/sub/28230` and a
   rendered PDF sample with citywide monthly tonnage 2013–2022) — citywide totals,
   not per-khet, PDF-only.

**Verdict: «нет честных данных» holds.** No open, licensed, spatially-resolvable
*cleanliness* source exists today. Closest honest proxies: annual waste tonnage per
khet (CC BY, file access pending) and Traffy waste-complaint counts per khet
(registration + licence-unspecified).

---

## Per-sub-question recommendations (ticket scheme: signal / refinement / fact / reject)

1. **Sidewalk network (footway/footway=sidewalk) — reject as a city signal; keep as fact-texture.**
   Absolute OSM sidewalk coverage in Bangkok (16.5 % of footway ways; 0.74 km/km²
   citywide) reflects mapper behaviour more than streets; percentile-ranking khets on
   it would publish mapper noise. The 24× khet contrast (PW 5.72 vs BK 0.24 km/km²)
   is usable as neutral editorial fact lines per district page ("mapped sidewalk
   density, OSM 2026"), never as a score input.
2. **Crossings — fact (minor).** Counts verified (17,017 nodes / 2,651 crossing-ways
   citywide; 555/255/67 in the three khets). Only meaningful as a component of a
   future *pedestrian-infrastructure* fact block alongside §1–3, not standalone.
3. **`sidewalk=…` on arterials — reject as signal; fact only.** 8.3 % marked citywide
   with a heavy `left`-bias artefact; per-khet shares (25.4/12.5/0.8 %) are fine as
   texture. Re-check composition after any bulk sidewalk import lands in Thai OSM.
4. **Arterial exposure (300 m around station zones) — refinement (method proven,
   adopt when a consumer signal exists).** Runs end-to-end on repo data
   (`app/src/data/bangkok/stations.json` × one Overpass geom dump × local
   point-to-segment distances; 117/133 = 88 %, median 10 ways, 16 zeros). As a binary
   it barely discriminates (88 % true); as a count (0–54) or nearest-distance (6 m
   median) it carries real variance. It belongs on the **noise/exposure** side of
   urban fabric (framing decision = owner). Recompute from platform coordinates, not
   zone centroids, if adopted.
5. **Cleanliness — reject for the pipeline today.** Monitor three reopeners:
   (a) Traffy Fondue licence clarification or an owner-registered bulk download
   (per-khet ขยะ counts would then be a legitimate monthly-updating fact);
   (b) `data.bangkok.go.th` becoming reachable / publishing its Environment-Dept
   datasets with a licence; (c) manual one-time browser grab of the CC-BY waste-tonnage
   CSV on data.go.th as an annual fact.

## Open questions for the owner

1. Is arterial exposure intended as a **negative** (noise/air at the doorstep) or a
   neutral fabric descriptor — and if negative, does it belong in the noise topic
   (CRTKY-151) rather than urban fabric?
2. Traffy Fondue registration needs a real name/e-mail/org/purpose, and no licence is
   stated — acceptable to register on behalf of the project, and under what legal
   basis for redistribution of derived counts?
3. data.go.th waste-tonnage CSV (CC BY) needs one manual browser download (API is
   WAF-blocked from our environment) — proceed? What refresh cadence (dataset updates
   yearly)?
4. Which station point should exposure use — the zone centroid in
   `app/src/data/bangkok/stations.json` (conservative 88 %) or the true platform
   coordinate (higher share, sharper counts)?
5. Overpass mirror snapshots used here lag live OSM by 2.5–4.5 months (base
   2026-05-31 / 2026-07-28) — acceptable freshness for the implementation run, or wait
   for the primary mirror's base to catch up?
