#!/usr/bin/env python3
"""
Fix wapuro-romaji station names → Hepburn romanization.

Wapuro artifacts: ou→o, uu→u, oo→o (long vowel markers used for keyboard
input, not official station signage).

Also applies manual overrides for known wrong-reading kanji (大島=Ojima not Oshima).
"""

import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATIONS_FILE = DATA_DIR / "stations.json"

# ── Manual overrides: wrong readings or exceptions ──
# These can't be fixed by simple vowel rules because the kanji reading is wrong.
# Format: old_slug → (correct_name_en, correct_slug)
OVERRIDES = {
    # 大島 on Toei Shinjuku line = おおじま (Ōjima), not おおしま (Ōshima)
    "ooshima": ("Ojima", "ojima"),
    "nishi-ooshima": ("Nishi-Ojima", "nishi-ojima"),
    # 広尾 = Hiroo is the OFFICIAL spelling (not a wapuro artifact)
    "hiroo": ("Hiroo", "hiroo"),
    # 下落合 = Shimo-Ochiai (the oo spans morpheme boundary: shimo + ochiai)
    "shimoochiai": ("Shimo-Ochiai", "shimo-ochiai"),
    # スポーツセンター = Sports Center (katakana loan word)
    "supootsusentaa": ("Sports-Center", "sports-center"),
    # 東京テレポート = Tokyo Teleport
    "toukyou-terepooto": ("Tokyo-Teleport", "tokyo-teleport"),
    # 福浦 = ふくうら (fuku + ura) — 'uu' is morpheme boundary, not long vowel
    "fukuura": ("Fukuura", "fukuura"),
    # 勝浦 = かつうら (katsu + ura) — same
    "katsuura": ("Katsuura", "katsuura"),
    # 湖北 (Abiko, Chiba) and 江北 (Adachi, Tokyo) both romanize to Kohoku.
    # Disambiguate by ward/city in the slug.
    "kohoku": ("Kohoku", "kohoku-abiko"),
    "kouhoku": ("Kohoku", "kohoku-adachi"),
}


def wapuro_to_hepburn(text: str) -> str:
    """Convert wapuro-romaji long vowels to Hepburn (ASCII, no macrons)."""
    # Order matters: do 'ou' before 'oo' to avoid interference
    result = re.sub(r"ou", "o", text, flags=re.IGNORECASE)
    result = re.sub(r"uu", "u", result, flags=re.IGNORECASE)
    result = re.sub(r"oo", "o", result, flags=re.IGNORECASE)
    return result


def fix_capitalization(name: str) -> str:
    """Capitalize first letter of each hyphen-separated part."""
    parts = name.split("-")
    fixed = []
    for p in parts:
        if not p:
            fixed.append(p)
        elif p[0] == "(" or p[0] == ")":
            # Preserve parenthesized parts like (-Daini-...)
            fixed.append(p)
        else:
            fixed.append(p[0].upper() + p[1:])
    return "-".join(fixed)


def convert_station(station: dict) -> tuple[dict, dict | None]:
    """
    Returns (updated_station, change_record | None).
    change_record is None if no changes were made.
    """
    old_name = station["name_en"]
    old_slug = station["slug"]

    # Check for manual override first
    if old_slug in OVERRIDES:
        new_name, new_slug = OVERRIDES[old_slug]
    else:
        new_name = fix_capitalization(wapuro_to_hepburn(old_name))
        new_slug = wapuro_to_hepburn(old_slug)

    if new_name == old_name and new_slug == old_slug:
        return station, None

    updated = {**station, "name_en": new_name, "slug": new_slug}
    change = {
        "old_slug": old_slug,
        "new_slug": new_slug,
        "old_name": old_name,
        "new_name": new_name,
        "name_jp": station["name_jp"],
        "is_override": old_slug in OVERRIDES,
    }
    return updated, change


def main():
    dry_run = "--dry-run" in sys.argv

    with open(STATIONS_FILE) as f:
        stations = json.load(f)

    updated_stations = []
    changes = []
    slug_map = {}  # old_slug → new_slug (for redirect generation)

    for s in stations:
        updated, change = convert_station(s)
        updated_stations.append(updated)
        if change:
            changes.append(change)
            if change["old_slug"] != change["new_slug"]:
                slug_map[change["old_slug"]] = change["new_slug"]

    # Report
    print(f"Total stations: {len(stations)}")
    print(f"Changed: {len(changes)} ({len(changes)/len(stations)*100:.1f}%)")
    print(f"Slug changes: {len(slug_map)}")
    print(f"Manual overrides: {sum(1 for c in changes if c['is_override'])}")
    print()

    if changes:
        print("=== Changes ===")
        print()
        for c in sorted(changes, key=lambda x: x["old_slug"]):
            flag = " [OVERRIDE]" if c["is_override"] else ""
            print(
                f"  {c['old_slug']:40s} → {c['new_slug']:35s}  "
                f"{c['name_jp']:10s}  ({c['old_name']} → {c['new_name']}){flag}"
            )

    if dry_run:
        print(f"\n[DRY RUN] No files written.")
        return

    # Write updated stations (both copies: data/ for scripts, app/src/data/ for Next.js)
    app_stations_file = Path(__file__).resolve().parent.parent / "app" / "src" / "data" / "stations.json"
    for fpath in [STATIONS_FILE, app_stations_file]:
        with open(fpath, "w") as f:
            json.dump(updated_stations, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Updated {fpath}")

    # Write slug redirect map (for Next.js redirects or proxy rules)
    redirect_file = DATA_DIR / "slug-redirects.json"
    with open(redirect_file, "w") as f:
        json.dump(slug_map, f, indent=2, ensure_ascii=False)
    print(f"✓ Wrote {len(slug_map)} redirects to {redirect_file}")


if __name__ == "__main__":
    main()
