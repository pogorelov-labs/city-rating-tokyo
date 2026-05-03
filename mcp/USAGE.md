# MCP Usage Guide — city-rating Tokyo

This is a usage guide for the 9 tools exposed by the city-rating MCP
server. Read it before relying on tool output for product decisions —
the dataset has known asymmetries that "100% coverage" headline numbers
hide.

Endpoint: `https://city-rating.pogorelov.dev/mcp`
Bearer auth (request a key at `https://city-rating.pogorelov.dev/api-access`).

---

## Pick the right tool

```
Question                                          → Tool

"Top N stations under filters X with weights Y"   → search_stations
"Tell me everything about station Z"              → get_station
"Compare stations A vs B vs C"                    → compare_stations
"How many izakayas / parks / clinics near Z?"     → list_pois
"How is the food rating computed?"                → get_methodology
"What rating dimensions / locales exist?"         → list_categories

"Find stations matching this vibe in words"       → semantic_search
"I like station Z, what else feels like it?"      → find_similar
"User describes goals AND has hard requirements"  → recommend
```

### When to pick `search_stations` vs `recommend`

- `search_stations` — when the user can express preferences as
  numerical weights and dealbreakers ("at least 7 safety, ≤¥130k rent,
  bump food weight"). Same logic as the homepage UI.
- `recommend` — when intent is fuzzy ("a quiet neighborhood with
  character, not too far from Shinjuku"). Embeddings handle the fuzzy
  part, structured weights re-rank.
- Use `recommend` with `hybrid_alpha=1.0` for pure semantic, `0.0` for
  pure structured. `0.5` (default) blends both.

### When to pick `semantic_search` vs `find_similar`

- `semantic_search(query)` — searches description vectors against an
  arbitrary natural-language query.
- `find_similar(slug)` — searches against the seed station's own
  vector. The seed is excluded from results.
- Both can constrain to one description field via `field='nightlife'`
  (or atmosphere / landmarks / food). Useful for queries like
  "shopping street with old kissaten" → `field='atmosphere'`.

---

## Reading results

Every tool that returns station rows includes:

| Field | What it means |
|---|---|
| `slug` | Stable string ID; never changes. Use for cross-tool calls. |
| `name`, `name_jp`, `name_secondary` | Locale-aware display names. |
| `score` | Composite weighted score 1–10 under the requested weights. |
| `ratings` | All 10 raw category scores (1–10). |
| `confidence` (in get_station / per-row metadata) | Per-category confidence: strong / moderate / estimate / editorial. **Read this before quoting a rating.** |
| `sources` | Per-category source list (e.g. `["hotpepper", "osm"]` for food). Quote when explaining a rating. |
| `rent_1k_1ldk` | Monthly rent, ¥. `null` if unknown. |
| `min_transit_min` | Minutes to nearest of Shibuya / Shinjuku / Tokyo / Ikebukuro / Shinagawa. |
| `rent_unknown` | True if a rent filter was active and the station has no rent data — interpret cautiously, the station was NOT excluded by the filter. |
| `url` | Locale-aware site URL (canonical). |

### `confidence` levels — what to actually do

| Level | Meaning | When you see it |
|---|---|---|
| `strong` | Direct measurement from 2+ verified sources. **Quote freely.** | Tokyo wards food/transport/safety, etc. |
| `moderate` | Single source or aggregated fallback. **Quote with "based on X".** | e-Stat ward-level rent (most stations), prefecture-average safety outside Tokyo. |
| `estimate` | Modeled from formula or proxy, not observed. **Hedge: "estimated from"**. | Distance-regression rent for edge stations, composite_fallback for vibe. |
| `editorial` | Set by AI researcher, may differ from data. **Don't double-quote sources.** | ~252 hand-curated stations like Shibuya, Kichijoji, etc. |

### Reading `score`

The composite score = weighted average of 10 ratings, normalized 1–10.
Defaults match the site (transport 18, rent 18, daily_essentials 14,
food 12, safety 10, nightlife 8, green 8, gym 4, vibe 4, crowd 4).

A score of `7.0` is **above the Greater Tokyo p50 of 6.0**. The full
distribution: p5=3.6, p50=6.0, p95=7.15. Interpret accordingly:
- `7.5+` is genuinely strong (top 5%)
- `6.0–7.0` is the broad "typical" band
- `<5` is below average — usually weak transport, food, or essentials

---

## Source data per category

| Category | Primary source | Coverage | Caveats |
|---|---|---|---|
| **transport** | Station line_count (ekidata) + MLIT S12 daily passenger counts | 1493/1493 lines, 94% passengers | Number-of-lines-with-bonus-for-passengers. Doesn't account for transfer hassle or platform crowding. |
| **rent** | Suumo listings → e-Stat ward avg → log-linear distance regression | 273 stations Suumo (strong), 826 e-Stat (moderate), rest regression (estimate). `confidence.rent` tells which. | **Only ~18% have real station-level rent.** Most are ward averages — fine for affordability comparisons within Tokyo wards, **noisy outside Tokyo**. |
| **daily_essentials** | OSM osm_livability table (supermarket, pharmacy, clinic, school, kindergarten, post office, bank, laundry, dentist) | 1493/1493 strong | OSM completeness varies by area; very dense urban OSM is excellent, edge prefectures may underreport. |
| **safety** | Tokyo: Keishicho ArcGIS neighborhood polygons (615 stations strong). Other prefectures: ward-level fallback (moderate) → prefecture average (estimate). | 1493/1493 normalized but quality drops outside Tokyo. | **The tier matters a lot.** A "safety: 8 prefecture_average" is much weaker than "safety: 8 keishicho_arcgis". Always look at `confidence.safety` and `sources.safety`. |
| **food** | HotPepper Gourmet API total_count + OSM food POI count | 100% both. r=0.855 correlation between sources. | **Single-vendor (HotPepper) for the rich signal** — no automated fallback. If HotPepper has thin data for an area (rare in Tokyo), the rating leans on OSM. |
| **green** | OSM `leisure=park\|garden\|nature_reserve` + landuse + natural=wood; polygon area | 100% normalized | Very dense urban areas can score low because OSM tags small pocket parks inconsistently. |
| **gym_sports** | OSM `leisure=fitness_centre\|sports_centre\|swimming_pool` count | 100% | Same OSM completeness caveat. |
| **vibe** | OSM cultural venues (theatre/cinema/arts_centre) + pedestrian streets + cafes + cultural shop ratio. AI-researched override for ~252 stations. | 100% normalized | The fuzziest category. ~252 stations have hand-curated values that diverge from the OSM-derived score. |
| **nightlife** | HotPepper `midnight_count` + izakaya + bar + OSM nightlife + karaoke + hostels | 100% | Single-vendor for the rich signal (same as food). |
| **crowd** | MLIT S12 daily passengers (inverted: fewer = quieter) | 94% MLIT, rest HotPepper density proxy | "Crowd" is *passenger throughput*, not residential density. A residential station with low ridership scores high (= quiet) even if streets are busy on weekends. |

---

## Common pitfalls

### 1. "100% coverage" doesn't mean uniform quality

Every category has 1493/1493 stations participating in the normalization,
but the underlying source quality is **wildly uneven**. A station outside
Tokyo with `safety: 8 prefecture_average` got that 8 by being compared to
peers in the same prefecture — not by direct measurement. Always check
`confidence.<category>` before treating a number as ground truth.

### 2. AI-researched (`editorial`) stations override the pipeline

About 252 stations (Shibuya, Kichijoji, Shimokitazawa, etc.) have ratings
set by human researchers. For these:
- `confidence: editorial` for some/all categories where the researcher
  diverged from the data
- The `description` field is hand-authored prose, not LLM-generated
- These are **the most reliable subjective takes** but should not be
  cited as "data shows X" — they're informed opinion.

### 3. Rent for non-Tokyo stations is mostly ward-level

Outside the 23 special wards, `rent.source` is usually `estat` (ward
average from government statistics) or `distance_regression` (formula).
Saying "this station has cheap rent" is fine; saying "this station's
rent is exactly ¥118k" is misleading without the source caveat.

### 4. "Transit minutes" is geographic, not GTFS

`transit_minutes` to the 5 hubs is computed from a calibrated geographic
model (Haversine + line connectivity), not real timetable routing.
MAE 5.5 min, 85% within 10 min of ground truth. **Don't quote as if it
were Google Maps directions.** Useful for ballpark filtering, not for
"my morning train at 8:14".

### 5. Last train times — Sat/Sun/Holiday combined

`last_train.holiday` is a single value covering Saturday, Sunday, AND
Japanese national holidays. The source (mini-tokyo-3d) doesn't separate
them. If a user asks "what about Sunday specifically", the honest answer
is "we don't distinguish — last train is the same conservative cutoff
for any non-weekday".

### 6. Live cameras go stale

`livecams[*].video_id` references a specific YouTube live stream. When
that stream ends (days to weeks), the embed shows "Video unavailable".
Re-scraping every ~week keeps them current. If a user reports a dead
camera, that's the cause.

### 7. `rent_unknown=true` in search results

When a rent filter is active and the station has no rent data, it
**passes the filter** but is marked `rent_unknown: true`. The site UI
dims these markers; LLM clients should call this out:
> "Note: 3 of the 10 results have no rent data and may not actually
> meet your ¥130k cap."

### 8. Station naming — kanji is canonical

Even in EN locale, the user is physically in Tokyo and sees kanji on
signs. `name_jp` is always returned. For RU locale, `name_ru` falls
back to `name_en` if not available (CRTKY-107 pending). Display
patterns are handled per-locale by the server; clients shouldn't
re-format.

---

## Example prompts that work well

### Find a place to live (most common use case)

> "I'm looking at moving to Tokyo. Single, work near Shinjuku, want
> walkable food scene and not too quiet at night. Budget ¥120k. Use
> the Tokyo MCP to give me 5 options with reasoning."

The agent should call `recommend(query=…, max_rent=120000, max_commute=20)`,
then for the top 1–2 also call `get_station(slug)` to ground the prose.

### Compare neighborhoods

> "Compare Shimokitazawa, Koenji, and Sangenjaya for a 35-year-old
> couple with a small kid. Where's safer, cheaper, more family-friendly?"

Use `compare_stations(['shimokitazawa','koenji','sangenjaya'])` then
narrate the deltas. Don't forget to check `confidence.safety` for each.

### Explore by vibe

> "Show me stations that feel like Kichijoji."

`find_similar(slug='kichijoji', limit=10)` → narrate top results,
mentioning their composite_score and one differentiator each.

### Cross-lingual search (Russian / Japanese)

> "Найди тихий район для семьи с парками рядом."

`semantic_search(query='тихий район для семьи с парками', locale='ru')`.
The e5-large model is multilingual — RU queries find stations with
matching RU descriptions. Same for JP.

### Methodology questions

> "How is the food rating computed and how confident are you for
> Akabane specifically?"

1. `get_methodology()` for the formula
2. `get_station('akabane')` and quote the `confidence.food` and
   `sources.food` fields

---

## What this MCP is NOT

- **Not a real-time data source.** Ratings are recomputed on a monthly
  cadence; live-camera scraping is roughly weekly. Don't use this for
  "what's open right now".
- **Not a routing engine.** `transit_minutes` is a geographic model.
  For real itineraries, use a maps API.
- **Not a real estate listing service.** `rent` is monthly-average
  pricing context, not specific available units. Don't quote "ある
  １ K available at ¥118k" — that's a misread.
- **Not exhaustive outside Greater Tokyo.** Coverage is 1493 stations
  in the metro region. Stations in Hakone, Atami, etc. are included
  but data quality drops sharply.

---

## Updating these guidelines

When the dataset changes (new descriptions, new sources, more
AI-researched stations), update both this file AND the `instructions`
field in `mcp/src/city_rating_mcp/server.py:mcp = FastMCP(...)` so
agents reading the protocol-level instructions see the same caveats.

For maintenance details (refresh cadence, rebuild commands, deploy)
see `mcp/README.md`. For the dataset's deeper "honesty" notes see the
"Data readiness & coverage honesty" section in repo-root `CLAUDE.md`.
