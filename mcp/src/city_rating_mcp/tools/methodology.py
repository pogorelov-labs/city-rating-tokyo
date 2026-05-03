"""get_methodology — formulas, confidence levels, sources.

This is plain text the LLM can quote when explaining a rating to a user.
Trimmed from CLAUDE.md "Rating Formulas (v3)" + "Data readiness & coverage
honesty" + the /methodology page. Keep it accurate or users get hallucinated
explanations of how their score was computed.
"""

from __future__ import annotations

METHODOLOGY = {
    "overview": (
        "City-rating Tokyo covers 1493 stations across Greater Tokyo. Each "
        "station gets ten 1-10 ratings from data-driven pipelines. The "
        "homepage composite score is a weighted average — users tune the "
        "weights, the dealbreaker filters cut hard."
    ),
    "ratings": {
        "transport": "line_count + log(daily_passengers). Caps: 8 needs ≥2 lines, 9 ≥3, 10 ≥5.",
        "rent": "Inverted: cheaper → higher. Suumo listings (273 stations) → ward average (713 more) → log-linear distance regression. Floor ¥80k, ceiling ¥300k.",
        "daily_essentials": "Weighted log-counts of supermarket, pharmacy, clinic, dentist, school, post office, bank, laundry. Source: OSM osm_livability table (1493/1493).",
        "safety": "Weighted crime rate per adjusted population. Tokyo: Keishicho neighborhood polygons (615 stations). Other prefectures: ward/municipality fallback.",
        "food": "log(HotPepper total) * 0.6 + log(OSM food) * 0.4. Caps: 8 ≥100 venues, 9 ≥400, 10 ≥1000.",
        "green": "Park area + count + large-park bonus + water proximity. Source: OSM polygons.",
        "gym_sports": "OSM gym_count. Caps: 8 ≥7, 9 ≥12, 10 ≥20.",
        "vibe": "Cultural venues + pedestrian streets + cafe density + cultural shop ratio. AI-researched override for ~252 stations.",
        "nightlife": "HotPepper midnight + izakaya + bar + OSM nightlife + karaoke + hostels.",
        "crowd": "Inverted quietness. Daily passengers (MLIT S12, 94% coverage). HotPepper density fallback.",
    },
    "weights_default": {
        "transport": 18, "rent": 18, "daily_essentials": 14, "safety": 10,
        "food": 12, "green": 8, "gym_sports": 4, "vibe": 4, "nightlife": 8,
        "crowd": 4,
    },
    "confidence_levels": {
        "strong": "Direct measurement — Suumo rent, HotPepper for food, MLIT for crowd, etc.",
        "moderate": "Data exists but with caveats — ward-level rent, prefecture-level safety.",
        "estimate": "Formula or proxy — distance regression, fallback heuristics. Treat as ballpark.",
        "editorial": "Curated by AI research (not pipeline). ~252 stations have hand-authored values that diverge from the pipeline output.",
    },
    "honesty": [
        "100% coverage means all 1493 slugs participate in normalization, NOT that every number is equally grounded.",
        "Rent: real Suumo data covers a minority; most stations are ward-average or regression. Check `confidence.rent`.",
        "Safety: Tokyo polygons are neighborhood-level; outside Tokyo it's coarser.",
        "Transit times: geographic model (Haversine + line connectivity) calibrated against 252 ground-truth points (MAE 5.5 min). Not GTFS routing yet.",
        "Last train times: Sat/Sun/Holiday are combined in source — no separate Sunday breakdown.",
        "Live cameras are 3rd-party YouTube streams; video IDs go stale when streams end.",
    ],
    "site": "https://city-rating.pogorelov.dev",
    "details": "https://city-rating.pogorelov.dev/methodology",
}


def get_methodology() -> dict:
    return METHODOLOGY
