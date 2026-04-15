#!/usr/bin/env python3
"""
Show CRTKY-109 generation progress.

Usage:
    python3 scripts/queue-status.py            # summary
    python3 scripts/queue-status.py --next 10  # list next 10 to generate
    python3 scripts/queue-status.py --failed   # list descriptions that look broken
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DM_PATH = ROOT / "data" / "station-datamart.json"
PROMPT_DIR = ROOT / "data" / "prompts"
DESC_DIR = ROOT / "data" / "descriptions"


def validate_description(d: dict) -> list[str]:
    """Return a list of issues with this description (empty = OK)."""
    issues = []
    if not isinstance(d, dict):
        return ["not a dict"]
    for lang in ["en", "ja", "ru"]:
        if lang not in d:
            issues.append(f"missing {lang}")
            continue
        block = d[lang]
        if not isinstance(block, dict):
            issues.append(f"{lang} not a dict")
            continue
        for field in ["atmosphere", "landmarks", "food", "nightlife"]:
            if field not in block:
                issues.append(f"{lang}.{field} missing")
            elif not isinstance(block[field], str):
                issues.append(f"{lang}.{field} not a string")
            elif not block[field].strip():
                issues.append(f"{lang}.{field} empty")
    return issues


def main():
    with open(DM_PATH) as f:
        dm = json.load(f)

    stations = dm["stations"]
    order = dm["generation_order"]

    # All 1493 stations need generation (including the ~252 that previously
    # had single-field RU editorial descriptions — those get regenerated into
    # structured {en,ja,ru} × {atmosphere,landmarks,food,nightlife}).
    needs_gen = list(order)
    has_existing = [s for s in order if stations[s].get("has_existing_description")]

    # Check output directory
    done_files = list(DESC_DIR.glob("*.json"))
    done_slugs = {f.stem for f in done_files}

    # Validate each
    valid = 0
    invalid = []
    for f in done_files:
        try:
            with open(f) as fh:
                d = json.load(fh)
            issues = validate_description(d)
            if issues:
                invalid.append((f.stem, issues))
            else:
                valid += 1
        except Exception as e:
            invalid.append((f.stem, [f"read error: {e}"]))

    remaining = [s for s in needs_gen if s not in done_slugs]

    # Prompts directory
    prompt_files = list(PROMPT_DIR.glob("*.md"))
    orphan_prompts = [f.stem for f in prompt_files if f.stem in done_slugs]

    print(f"=== CRTKY-109 Generation Status ===")
    print(f"Total stations:             {len(stations)}")
    print(f"  with legacy RU desc:      {len(has_existing)}  (regenerating — not preserved)")
    print(f"  all need generation:      {len(needs_gen)}")
    print(f"")
    print(f"Generated:                  {len(done_slugs)}")
    print(f"  valid output:             {valid}")
    print(f"  invalid/broken:           {len(invalid)}")
    print(f"")
    print(f"Remaining to generate:      {len(remaining)}")
    print(f"")
    print(f"Prompts on disk:            {len(prompt_files)}")
    print(f"  orphaned (already done):  {len(orphan_prompts)}  (safe to delete)")

    if "--next" in sys.argv:
        i = sys.argv.index("--next")
        n = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 10
        print(f"\n=== Next {min(n, len(remaining))} to generate (score desc) ===")
        for slug in remaining[:n]:
            st = stations[slug]
            print(f"  {slug:35s} score={st['composite_score']:4.1f}  {st['name_en']} ({st['name_jp']})")

    if "--failed" in sys.argv and invalid:
        print(f"\n=== Invalid output files ===")
        for slug, issues in invalid[:20]:
            print(f"  {slug}: {', '.join(issues)}")


if __name__ == "__main__":
    main()
