#!/usr/bin/env python3
"""
Export computed ratings from NocoDB to demo-ratings.ts.
Preserves AI-researched entries (those with descriptions) from existing file.
Replaces heuristic entries with data-driven computed ratings.

Usage: python3 scripts/export-ratings.py [--dry-run] [--output PATH] [--allow-missing]

By default the script fails (exit 1) if any station in stations.json has no
computed rating, which prevents shipping a partial demo-ratings.ts. Pass
--allow-missing to tolerate a partial run (e.g. a newly-added station that has
not yet been scraped/computed).
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
    cats = ["transport", "rent", "daily_essentials", "safety", "food",
            "green", "gym_sports", "vibe", "nightlife", "crowd"]

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


def _computed_meta(computed_row, field, cat, default):
    """Read one category from a computed row's JSON-string metadata column."""
    val = computed_row.get(field) if computed_row else None
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            val = None
    if isinstance(val, dict):
        return val.get(cat, default)
    return default


def backfill_daily_essentials(entry_text, computed_row):
    """
    Fill daily_essentials into an AI-researched entry from the computed pipeline.

    CRTKY-129: the AI-researched entries predate the daily_essentials category
    (PR #81), so their ratings, confidence and sources objects have no
    daily_essentials key — and the CRTKY-83 merge only runs for entries without
    a confidence block, so it never revisits them. The frontend then substituted
    a hardcoded 5 (data.ts) that fed the composite score at 14% weight.

    No researcher ever rated this category, so there is no editorial value to
    preserve: the computed rating, confidence and sources are the honest ones.
    Keys that are already present are left untouched.

    Returns (entry_text, status) with status one of:
      'present' — the entry already had a daily_essentials rating
      'filled'  — the rating was filled from computed data
      'missing' — no rating and no computed value to fill it from
    """
    computed_value = computed_row.get("daily_essentials") if computed_row else None
    ratings = re.search(r"ratings: \{([^}]*)\}", entry_text)
    existing = re.search(r"daily_essentials: (\d+)", ratings.group(1)) if ratings else None
    if existing:
        status = "present"
        # A researcher-set value follows the CRTKY-83 rule: agreement with the
        # pipeline inherits its metadata, disagreement is editorial.
        inherits = computed_value is not None and int(existing.group(1)) == int(computed_value)
    else:
        if computed_value is None or not ratings:
            return entry_text, "missing"
        entry_text = (
            entry_text[:ratings.end() - 1].rstrip()
            + f", daily_essentials: {int(computed_value)} "
            + entry_text[ratings.end() - 1:]
        )
        status = "filled"
        inherits = True

    if inherits:
        conf_level = _computed_meta(computed_row, "confidence", "daily_essentials", "estimate")
        srcs_list = _computed_meta(computed_row, "sources", "daily_essentials", [])
    else:
        conf_level, srcs_list = "editorial", ["ai_research"]
    srcs_ts = "[" + ", ".join(f"'{s}'" for s in srcs_list) + "]"
    for field, literal in (("confidence", f"'{conf_level}'"), ("sources", srcs_ts)):
        # confidence values have no brackets; sources values are flat [...] arrays
        block = re.search(rf"{field}: \{{([^{{}}]*)\}}", entry_text)
        if block and "daily_essentials:" not in block.group(1):
            entry_text = (
                entry_text[:block.end() - 1].rstrip()
                + f", daily_essentials: {literal} "
                + entry_text[block.end() - 1:]
            )
    return entry_text, status


STATION_LEVEL_RENT_SOURCES = {"suumo", "homes"}


def apply_station_level_rent(entry_text, computed_row):
    """
    Let station-level rent data win over the editorial rent rating.

    Decided 2026-09-30 (research/decisions/2026-09-30-epic80-checkpoint.md, D3b):
    when the pipeline rated this station's rent from listings scraped around it
    (sources suumo/homes), that rating and its metadata replace the AI
    researcher's value. The frontend was already showing the recomputed Suumo
    value, but under an 'editorial' label — this makes the export agree with
    what is displayed, and the label honest.

    Only the rent key inside ratings/confidence/sources changes; rent_avg and
    everything else is left as is. Returns (entry_text, changed).
    """
    if not computed_row:
        return entry_text, False
    srcs = _computed_meta(computed_row, "sources", "rent", [])
    value = computed_row.get("rent")
    if value is None or not STATION_LEVEL_RENT_SOURCES & set(srcs):
        return entry_text, False
    conf = _computed_meta(computed_row, "confidence", "rent", "estimate")
    srcs_ts = "[" + ", ".join(f"'{s}'" for s in srcs) + "]"

    before = entry_text
    for field, pattern, literal in (
        ("ratings", r"\brent: \d+", f"rent: {int(value)}"),
        ("confidence", r"\brent: '\w+'", f"rent: '{conf}'"),
        ("sources", r"\brent: \[[^\]]*\]", f"rent: {srcs_ts}"),
    ):
        block = re.search(rf"{field}: \{{([^{{}}]*)\}}", entry_text)
        if not block:
            continue
        inner = re.sub(pattern, literal, block.group(1), count=1)
        entry_text = entry_text[:block.start(1)] + inner + entry_text[block.end(1):]
    return entry_text, entry_text != before


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
    cats = ["transport", "rent", "daily_essentials", "safety", "food",
            "green", "gym_sports", "vibe", "nightlife", "crowd"]
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
        f"    ratings: {{ transport: {r['transport']}, rent: {r['rent']}, "
        f"daily_essentials: {r.get('daily_essentials', 5)}, safety: {r['safety']}, "
        f"food: {r['food']}, green: {r['green']}, gym_sports: {r['gym_sports']}, "
        f"vibe: {r['vibe']}, nightlife: {r['nightlife']}, crowd: {r['crowd']} }},\n"
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
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow stations with no computed rating instead of failing (exit 1). "
             "Use for partial runs where a new station has not yet been scraped.",
    )
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
    parts.append("// daily_essentials is filled for every entry by export-ratings.py (CRTKY-129); optional only for --allow-missing runs")
    parts.append("type DemoRatings = Omit<StationRatings, 'daily_essentials'> & { daily_essentials?: number };")
    parts.append("")
    parts.append("interface DemoData {")
    parts.append("  ratings: DemoRatings;")
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
    ai_de_filled = 0
    ai_de_missing = []
    ai_rent_station_level = 0
    for slug in sorted(ai_entries.keys()):
        if slug in all_slugs:
            entry_text = ai_entries[slug]
            comp_row = computed.get(slug)
            # Fill daily_essentials from the pipeline first (CRTKY-129), so the
            # CRTKY-83 merge below sees a rating that agrees with computed.
            entry_text, de_status = backfill_daily_essentials(entry_text, comp_row)
            if de_status == "filled":
                ai_de_filled += 1
            elif de_status == "missing":
                ai_de_missing.append(slug)
            # Merge confidence metadata from computed pipeline (CRTKY-83)
            has_confidence = 'confidence:' in entry_text
            if not has_confidence:
                ai_ratings = parse_ai_ratings(entry_text)
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
            # Station-level rent beats the editorial value (D3b, 2026-09-30).
            entry_text, rent_changed = apply_station_level_rent(entry_text, comp_row)
            ai_rent_station_level += rent_changed
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

    # An AI entry with no daily_essentials rating would fall back to a synthetic
    # value in the frontend — treat it like any other missing rating.
    missing_count += len(ai_de_missing)

    parts.append("};")
    parts.append("")

    output_content = "\n".join(parts)

    print(f"\nSummary:")
    print(f"  AI-researched (preserved): {ai_count}")
    print(f"    confidence merged:       {ai_conf_merged}")
    print(f"    daily_essentials filled: {ai_de_filled}")
    print(f"    rent from station data:  {ai_rent_station_level}")
    if ai_de_missing:
        print(f"    daily_essentials MISSING: {len(ai_de_missing)} "
              f"(no computed value): {', '.join(ai_de_missing[:10])}"
              f"{' …' if len(ai_de_missing) > 10 else ''}")
    print(f"  Computed (data-driven):    {computed_count}")
    print(f"  Missing (no data):         {missing_count}")
    print(f"  Total entries:             {ai_count + computed_count}")
    print(f"  Output size:               {len(output_content)} chars")

    if missing_count > 0 and not args.allow_missing:
        print(
            f"\nERROR: {missing_count} station(s) lack a computed rating (whole entry, or daily_essentials on an AI-researched entry). "
            "Refusing to write a partial demo-ratings.ts. "
            "Re-run compute-ratings.py, or pass --allow-missing to override.",
            file=sys.stderr,
        )
        sys.exit(1)

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
