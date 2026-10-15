#!/usr/bin/env python3
"""Restore an unfinished ratings journal. Stop all remote writers first."""
import argparse
import sys
from pathlib import Path

from rating_store import NocoRatingStore, recover


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--writers-stopped", action="store_true", required=True,
                        help="Confirm all writers are stopped and in-flight API requests settled")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
    from utils import NocoDB
    recover(NocoRatingStore(NocoDB("computed_ratings")), args.journal)
    print("Previous ratings restored and verified. No export or commit performed.")


if __name__ == "__main__":
    main()
