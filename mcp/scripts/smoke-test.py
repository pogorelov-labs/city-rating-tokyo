#!/usr/bin/env python3
"""End-to-end smoke test for all 9 MCP tools.

Requires:
  data/station-datamart.json     (scripts/build-datamart.py)
  data/embeddings.npz            (scripts/build-embeddings.py)

Run from the MCP package install (or `pip install -e mcp` from repo root).
"""

from __future__ import annotations

import sys
import time

from city_rating_mcp import server


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    section("list_categories")
    cats = server.list_categories()
    assert "rating_keys" in cats
    print(f"  rating keys: {len(cats['rating_keys'])}, locales: {cats['locales']}")
    print(f"  description fields: {cats['description_fields']}")

    section("get_methodology")
    m = server.get_methodology()
    assert "ratings" in m and len(m["ratings"]) >= 10
    print(f"  formulas covered: {len(m['ratings'])}")

    section("search_stations (default)")
    t0 = time.time()
    res = server.search_stations(limit=5)
    print(f"  total={res['total_matches']} returned={res['returned']} ({(time.time()-t0)*1000:.1f} ms)")
    for r in res["results"]:
        print(f"    {r['score']:>4} {r['slug']:<30} {r['ward'] or '-':<12} ¥{r['rent_1k_1ldk'] or '?'}")

    section("search_stations (foodie under ¥130k)")
    t0 = time.time()
    res = server.search_stations(
        weights={"food": 30, "nightlife": 15, "rent": 25, "transport": 15, "vibe": 15,
                 "daily_essentials": 0, "safety": 0, "green": 0, "gym_sports": 0, "crowd": 0},
        max_rent=130_000, limit=5,
    )
    print(f"  total={res['total_matches']} ({(time.time()-t0)*1000:.1f} ms)")
    for r in res["results"]:
        print(f"    {r['score']:>4} {r['slug']:<30} ¥{r['rent_1k_1ldk']}")

    section("get_station(shibuya, ja)")
    t0 = time.time()
    s = server.get_station("shibuya", locale="ja")
    print(f"  {s['name']} / {s['name_secondary']} ({(time.time()-t0)*1000:.1f} ms)")
    print(f"  composite={s['composite_score_default_weights']}")
    print(f"  lines={len(s['lines'])} livecams={len(s['livecams'] or [])}")
    if s.get("description"):
        print(f"  description.atmosphere: {s['description']['atmosphere'][:80]}…")

    section("compare_stations(shibuya, kichijoji, akabane)")
    t0 = time.time()
    cmp = server.compare_stations(["shibuya", "kichijoji", "akabane"])
    print(f"  profiles={len(cmp['profiles'])} missing={cmp['missing']} ({(time.time()-t0)*1000:.1f} ms)")

    section("list_pois(shibuya, food)")
    t0 = time.time()
    p = server.list_pois("shibuya", "food")
    print(f"  food: {p['categories']['food']} ({(time.time()-t0)*1000:.1f} ms)")

    # Heavy tools — first call pays the model load cost (~3 s).
    section("semantic_search('quiet riverside park', en)")
    t0 = time.time()
    sem = server.semantic_search(query="quiet riverside park with old shrines", locale="en", limit=5)
    print(f"  results={len(sem['results'])} (first call {(time.time()-t0)*1000:.0f} ms incl. model load)")
    for r in sem["results"]:
        print(f"    {r['semantic_score']:.3f}  {r['slug']:<25} {r['ward'] or '-'}")

    section("semantic_search (warm, ja, field=nightlife)")
    t0 = time.time()
    sem = server.semantic_search(query="深夜まで賑やかな飲み屋街", locale="ja", field="nightlife", limit=5)
    print(f"  results={len(sem['results'])} ({(time.time()-t0)*1000:.0f} ms)")
    for r in sem["results"]:
        print(f"    {r['semantic_score']:.3f}  {r['slug']:<25} matched={r['matched_field']}")

    section("find_similar(kichijoji, en)")
    t0 = time.time()
    sim = server.find_similar(slug="kichijoji", locale="en", limit=5)
    print(f"  ({(time.time()-t0)*1000:.0f} ms)")
    for r in sim["results"]:
        print(f"    {r['similarity']:.3f}  {r['slug']:<25} {r['ward'] or '-'}")

    section("recommend('cheap, foodie, with nightlife', filters)")
    t0 = time.time()
    rec = server.recommend(
        query="cheap foodie neighbourhood with late izakaya, not too quiet",
        max_rent=130_000, max_commute=35, hybrid_alpha=0.6, limit=5,
    )
    print(f"  pool_filtered={rec['total_after_filters']} ({(time.time()-t0)*1000:.0f} ms)")
    for r in rec["results"]:
        print(f"    blended={r['blended_score']:.3f} sem={r['semantic_score']:.3f} comp={r['score']:.1f}  {r['slug']:<25} ¥{r['rent_1k_1ldk']}")

    print("\n✓ All 9 tools responded.")


if __name__ == "__main__":
    main()
