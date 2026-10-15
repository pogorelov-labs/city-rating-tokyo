#!/usr/bin/env python3
"""Read-only source canary. --fixture is fully offline and never starts compute."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from source_health import MIN_COVERAGE, check_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--max-source-age-days", type=int, required=True)
    args = parser.parse_args()
    if args.fixture:
        data = json.loads(args.fixture.read_text())
        slugs, tables = data["slugs"], data["tables"]
        today = date.fromisoformat(data["today"]) if "today" in data else None
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
        from utils import NocoDB, load_stations
        from slugs import index_by_slug
        slugs = [s["slug"] for s in load_stations()]
        tables = {name: index_by_slug(NocoDB(name).get_all_records())[0] for name in MIN_COVERAGE}
        today = None
    try:
        print(json.dumps(check_sources(slugs, tables, args.max_source_age_days, today), indent=2))
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
