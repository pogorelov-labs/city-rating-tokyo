#!/usr/bin/env python3
"""Read-only, idempotent rollout check for the additive ratings metadata column."""
import sys
from pathlib import Path

from rating_store import NocoRatingStore


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent / "scrapers"))
    from utils import NocoDB
    NocoRatingStore(NocoDB("computed_ratings")).preflight()
    print("Schema verified: data_date SingleLineText; source_dates LongText. No writes.")


if __name__ == "__main__":
    main()
