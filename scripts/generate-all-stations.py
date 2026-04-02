#!/usr/bin/env python3
"""
Generate expanded stations.json with ALL Greater Tokyo stations.
Uses pykakasi for kanji→romaji conversion, with manual overrides for known stations.
"""

import json
import re
from pathlib import Path
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parent.parent

# Load raw data
raw = json.loads((ROOT / "package" / "stations.json").read_text())

# Load existing stations for manual romaji preservation
existing = json.loads((ROOT / "data" / "stations.json").read_text())
EXISTING_MAP = {s["name_jp"]: s["name_en"] for s in existing}

# Greater Tokyo prefectures
TARGET_PREFS = {"13", "14", "11", "12"}

# Initialize kakasi
kks = kakasi()

def kanji_to_romaji(kanji: str) -> str:
    """Convert kanji station name to romaji."""
    # Use existing mapping first
    if kanji in EXISTING_MAP:
        return EXISTING_MAP[kanji]

    result = kks.convert(kanji)
    parts = []
    for item in result:
        hepburn = item["hepburn"]
        if hepburn:
            parts.append(hepburn.capitalize())
        else:
            # Keep as-is (numbers, latin chars)
            parts.append(item["orig"])

    name = "-".join(parts) if len(parts) > 1 else parts[0] if parts else kanji
    # Clean up double dashes, trailing dashes
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name


def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


# Filter Greater Tokyo
tokyo_stations = [s for s in raw if s.get("prefecture") in TARGET_PREFS]
print(f"Greater Tokyo stations (raw): {len(tokyo_stations)}")

stations = []
seen_slugs = set()

for group in tokyo_stations:
    kanji = group["name_kanji"]
    first = (group.get("stations") or [{}])[0]

    if not first or not first.get("lat") or not first.get("lon"):
        continue

    romaji = kanji_to_romaji(kanji)
    slug = slugify(romaji)

    if slug in seen_slugs:
        continue
    seen_slugs.add(slug)

    line_ids = [s["ekidata_line_id"] for s in group.get("stations", []) if s.get("ekidata_line_id")]
    line_count = len(line_ids) if line_ids else 1

    stations.append({
        "slug": slug,
        "name_en": romaji,
        "name_jp": kanji,
        "lat": first["lat"],
        "lng": first["lon"],
        "lines": line_ids,
        "line_count": line_count,
        "prefecture": group["prefecture"],
        "ratings": None,
        "rent_avg": None,
        "transit_minutes": None,
    })

# Sort: most connected first, then alphabetical
stations.sort(key=lambda s: (-s["line_count"], s["name_en"]))

# Stats
by_pref = {}
for s in stations:
    by_pref[s["prefecture"]] = by_pref.get(s["prefecture"], 0) + 1

print(f"\nTotal stations: {len(stations)}")
print(f"  Tokyo (13): {by_pref.get('13', 0)}")
print(f"  Kanagawa (14): {by_pref.get('14', 0)}")
print(f"  Saitama (11): {by_pref.get('11', 0)}")
print(f"  Chiba (12): {by_pref.get('12', 0)}")

print(f"\nTop 20 most connected:")
for i, s in enumerate(stations[:20]):
    print(f"  {i+1}. {s['name_en']} ({s['name_jp']}) - {s['line_count']} lines")

# Check how many new vs existing
existing_slugs = {s["slug"] for s in existing}
new_slugs = {s["slug"] for s in stations} - existing_slugs
print(f"\nExisting stations kept: {len(existing_slugs & {s['slug'] for s in stations})}")
print(f"New stations added: {len(new_slugs)}")

# Write output
out_path = ROOT / "data" / "stations.json"
out_path.write_text(json.dumps(stations, indent=2, ensure_ascii=False))
print(f"\nWritten to {out_path}")

# Also write to app data
app_path = ROOT / "app" / "src" / "data" / "stations.json"
app_path.write_text(json.dumps(stations, indent=2, ensure_ascii=False))
print(f"Written to {app_path}")
