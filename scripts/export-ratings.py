#!/usr/bin/env python3
"""
Export computed ratings from NocoDB to demo-ratings.ts.
Preserves AI-researched entries (those with descriptions) from existing file.
Replaces heuristic entries with data-driven computed ratings.

Usage: python3 scripts/export-ratings.py [--dry-run] [--output PATH]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
from utils import NocoDB, load_stations

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "app" / "src" / "data" / "demo-ratings.ts"


def parse_existing_ai_entries(ts_path):
    """
    Parse the existing demo-ratings.ts to extract AI-researched entries.
    These are entries that have a `description` field.
    Returns dict of slug -> raw TypeScript object string.
    """
    content = ts_path.read_text()

    # Find all entries with description field
    # We'll parse the TS file structurally:
    # Each entry is: 'slug': { ratings: ..., transit_minutes: ..., rent_avg: ..., description: ... },
    ai_entries = {}

    # Split by top-level entries in DEMO_RATINGS
    # Pattern: slug followed by opening brace, content, closing brace
    # We look for entries that contain 'description:'
    lines = content.split('\n')

    current_slug = None
    current_lines = []
    brace_depth = 0
    in_entry = False

    for line in lines:
        # Detect start of a new entry
        slug_match = re.match(r"^\s+'?([a-z0-9-]+)'?\s*:\s*\{", line)
        if slug_match and not in_entry:
            current_slug = slug_match.group(1)
            current_lines = [line]
            # Count braces
            brace_depth = line.count('{') - line.count('}')
            in_entry = True
            continue

        if in_entry:
            current_lines.append(line)
            brace_depth += line.count('{') - line.count('}')

            if brace_depth <= 0:
                # Entry complete
                entry_text = '\n'.join(current_lines)
                if 'description:' in entry_text:
                    ai_entries[current_slug] = entry_text
                in_entry = False
                current_slug = None
                current_lines = []

    return ai_entries


def parse_ai_ratings(entry_text):
    """Extract the 9 rating integers from a raw TS AI entry string."""
    m = re.search(r'ratings:\s*\{([^}]+)\}', entry_text)
    if not m:
        return {}
    inner = m.group(1)
    ratings = {}
    for pair in re.findall(r'(\w+)\s*:\s*(\d+)', inner):
        ratings[pair[0]] = int(pair[1])
    return ratings


def merge_ai_confidence(entry_text, ai_ratings, computed_row):
    """
    Build merged confidence/sources for an AI-researched entry.

    Policy (CRTKY-83):
    - For each category, if the AI rating == computed rating → inherit
      computed confidence + sources (data backs the researcher's judgment).
    - If they differ → 'editorial' confidence, sources ['ai_research']
      (human researcher chose a different value than data alone suggests).
    - If no computed data exists → all categories get 'editorial'.
    """
    cats = ["food", "nightlife", "transport", "rent", "safety",
            "green", "gym_sports", "vibe", "crowd"]

    # Parse computed confidence/sources from NocoDB JSON strings
    comp_conf = {}
    comp_srcs = {}
    if computed_row:
        for field, target in [("confidence", comp_conf), ("sources", comp_srcs)]:
            val = computed_row.get(field)
            if isinstance(val, str):
                try:
                    target.update(json.loads(val))
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(val, dict):
                target.update(val)

    merged_conf = {}
    merged_srcs = {}
    for cat in cats:
        ai_val = ai_ratings.get(cat)
        comp_val = computed_row.get(cat) if computed_row else None

        # Compare: if both exist and match, inherit computed metadata
        if comp_val is not None and ai_val is not None and int(ai_val) == int(comp_val):
            merged_conf[cat] = comp_conf.get(cat, 'estimate')
            merged_srcs[cat] = comp_srcs.get(cat, [])
        else:
            merged_conf[cat] = 'editorial'
            merged_srcs[cat] = ['ai_research']

    data_date = computed_row.get("data_date", "2026-04") if computed_row else "2026-04"

    # Format as TS object strings
    conf_parts = [f"{c}: '{merged_conf[c]}'" for c in cats]
    conf_str = "{ " + ", ".join(conf_parts) + " }"

    srcs_parts = []
    for c in cats:
        s = merged_srcs[c]
        if isinstance(s, list):
            arr = "[" + ", ".join(f"'{x}'" for x in s) + "]"
        else:
            arr = "[]"
        srcs_parts.append(f"{c}: {arr}")
    srcs_str = "{ " + ", ".join(srcs_parts) + " }"

    return conf_str, srcs_str, data_date


def format_ratings_entry(slug, data, rent_data=None, transit_data=None):
    """Format a computed rating entry as TypeScript."""
    r = data
    rent = rent_data or {}

    rent_1k = rent.get("1k_1ldk") or "null"
    rent_2ldk = rent.get("2ldk") or "null"
    rent_source = rent.get("source", "computed")
    rent_updated = rent.get("updated", "2026-04")

    # Transit minutes from pre-computed transit-times.json (CRTKY-81)
    t = transit_data or {}
    transit = ("{ shibuya: %d, shinjuku: %d, tokyo: %d, ikebukuro: %d, shinagawa: %d }"
               % (t.get("shibuya", 30), t.get("shinjuku", 30), t.get("tokyo", 30),
                  t.get("ikebukuro", 30), t.get("shinagawa", 30)))

    safe_slug = f"'{slug}'" if '-' in slug else slug

    # Parse confidence and sources from NocoDB JSON string columns
    conf = {}
    srcs = {}
    data_date = r.get("data_date", "2026-04")
    for field, target in [("confidence", conf), ("sources", srcs)]:
        val = r.get(field)
        if isinstance(val, str):
            try:
                target.update(json.loads(val))
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(val, dict):
            target.update(val)

    # Format confidence object
    cats = ["food", "nightlife", "transport", "rent", "safety", "green", "gym_sports", "vibe", "crowd"]
    conf_parts = [f"{c}: '{conf.get(c, 'estimate')}'" for c in cats]
    conf_str = "{ " + ", ".join(conf_parts) + " }"

    # Format sources object
    srcs_parts = []
    for c in cats:
        s = srcs.get(c, [])
        if isinstance(s, list):
            arr = "[" + ", ".join(f"'{x}'" for x in s) + "]"
        else:
            arr = "[]"
        srcs_parts.append(f"{c}: {arr}")
    srcs_str = "{ " + ", ".join(srcs_parts) + " }"

    return (
        f"  {safe_slug}: {{\n"
        f"    ratings: {{ food: {r['food']}, nightlife: {r['nightlife']}, transport: {r['transport']}, "
        f"rent: {r['rent']}, safety: {r['safety']}, green: {r['green']}, "
        f"gym_sports: {r['gym_sports']}, vibe: {r['vibe']}, crowd: {r['crowd']} }},\n"
        f"    transit_minutes: {transit},\n"
        f"    rent_avg: {{ '1k_1ldk': {rent_1k}, '2ldk': {rent_2ldk}, "
        f"source: '{rent_source}', updated: '{rent_updated}' }},\n"
        f"    confidence: {conf_str},\n"
        f"    sources: {srcs_str},\n"
        f"    data_date: '{data_date}',\n"
        f"  }},"
    )


def main():
    parser = argparse.ArgumentParser(description="Export computed ratings to demo-ratings.ts")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing file")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output path")
    args = parser.parse_args()

    output_path = Path(args.output)
    stations = load_stations()
    all_slugs = {s["slug"] for s in stations}

    # 1. Parse existing AI-researched entries
    print("Parsing existing AI-researched entries...")
    ai_entries = {}
    if output_path.exists():
        ai_entries = parse_existing_ai_entries(output_path)
    print(f"  AI-researched entries: {len(ai_entries)}")

    # 2. Load computed ratings from NocoDB
    print("Loading computed ratings from NocoDB...")
    db = NocoDB("computed_ratings")
    computed_rows = db.get_all_records()
    computed = {r["slug"]: r for r in computed_rows if r.get("slug")}
    print(f"  Computed ratings: {len(computed)}")

    # 3. Load rent data
    print("Loading rent data...")
    rent_data = {}
    for fname in ["rent-averages-v2.json", "rent-averages.json"]:
        path = ROOT / "data" / "rent" / fname
        if path.exists():
            rent_data = json.loads(path.read_text())
            break
    if not rent_data:
        path = ROOT / "app" / "src" / "data" / "rent-averages.json"
        if path.exists():
            rent_data = json.loads(path.read_text())
    print(f"  Rent data: {len(rent_data)} stations")

    # 4. Load transit times from transit-times.json (CRTKY-81)
    transit_times = {}
    transit_path = ROOT / "data" / "transit-times.json"
    if transit_path.exists():
        transit_raw = json.loads(transit_path.read_text())
        transit_times = transit_raw.get("transit_times", {})
    print(f"  Transit times: {len(transit_times)} stations")

    # 5. Build output
    ai_count = 0
    computed_count = 0
    missing_count = 0

    parts = []
    parts.append("import { StationRatings, TransitMinutes, RentAvg, StationConfidence, StationSources } from '@/lib/types';")
    parts.append("")
    parts.append("interface DemoData {")
    parts.append("  ratings: StationRatings;")
    parts.append("  transit_minutes: TransitMinutes;")
    parts.append("  rent_avg: RentAvg;")
    parts.append("  confidence?: StationConfidence;")
    parts.append("  sources?: StationSources;")
    parts.append("  data_date?: string;")
    parts.append("  description?: {")
    parts.append("    atmosphere: string;")
    parts.append("    landmarks: string;")
    parts.append("    food: string;")
    parts.append("    nightlife: string;")
    parts.append("  };")
    parts.append("}")
    parts.append("")
    parts.append("export const DEMO_RATINGS: Record<string, DemoData> = {")

    # First: AI-researched entries (ratings preserved, confidence merged)
    parts.append("  // === AI-researched ratings (preserved, confidence merged) ===")
    ai_conf_merged = 0
    for slug in sorted(ai_entries.keys()):
        if slug in all_slugs:
            entry_text = ai_entries[slug]
            # Merge confidence metadata from computed pipeline (CRTKY-83)
            has_confidence = 'confidence:' in entry_text
            if not has_confidence:
                ai_ratings = parse_ai_ratings(entry_text)
                comp_row = computed.get(slug)
                conf_str, srcs_str, data_date = merge_ai_confidence(
                    entry_text, ai_ratings, comp_row
                )
                # Insert confidence/sources/data_date before the closing '},'
                # Find the last '},' and insert before it
                last_brace = entry_text.rstrip().rstrip(',')
                indent = "    "
                inject = (
                    f"\n{indent}confidence: {conf_str},"
                    f"\n{indent}sources: {srcs_str},"
                    f"\n{indent}data_date: '{data_date}',"
                    f"\n  }},"
                )
                # Replace the final '},\n' or '},' with injected block
                entry_text = re.sub(r'\s*\},?\s*$', inject, entry_text)
                ai_conf_merged += 1
            parts.append(entry_text)
            ai_count += 1

    parts.append("")
    parts.append("  // === Data-driven computed ratings ===")

    # Then: computed entries (for stations not in AI set)
    for station in stations:
        slug = station["slug"]
        if slug in ai_entries:
            continue  # Already added above

        if slug in computed:
            rent = rent_data.get(slug, {})
            transit = transit_times.get(slug, {})
            entry = format_ratings_entry(slug, computed[slug], rent, transit)
            parts.append(entry)
            computed_count += 1
        else:
            missing_count += 1

    parts.append("};")
    parts.append("")

    output_content = "\n".join(parts)

    print(f"\nSummary:")
    print(f"  AI-researched (preserved): {ai_count}")
    print(f"    confidence merged:       {ai_conf_merged}")
    print(f"  Computed (data-driven):    {computed_count}")
    print(f"  Missing (no data):         {missing_count}")
    print(f"  Total entries:             {ai_count + computed_count}")
    print(f"  Output size:               {len(output_content)} chars")

    if args.dry_run:
        print("\nDry run — not writing file.")
        # Print a sample
        for line in output_content.split('\n')[15:25]:
            print(f"  {line}")
        return

    output_path.write_text(output_content)
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
