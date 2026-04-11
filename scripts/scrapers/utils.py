#!/usr/bin/env python3
"""
Shared utilities for city-rating data scrapers.
Provides: station loading, NocoDB client, rate limiter.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests

ROOT = Path(__file__).resolve().parent.parent.parent

# NocoDB configuration
NOCODB_API_URL = os.environ.get("NOCODB_API_URL", "https://nocodb.pogorelov.dev")
NOCODB_API_TOKEN = os.environ.get("NOCODB_API_TOKEN", "3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt")

# Table IDs (created via API)
TABLE_IDS = {
    "osm_pois": "mnnuqtldvt4jxlj",
    "hotpepper": "mfk9j2qoj2bkeoo",
    "hostels": "ms9awzjv9j6suh7",
    "crime_stats": "mxitpnomlom3j3q",
    "passenger_counts": "m36bbxcv8t0asur",
    "computed_ratings": "mkp046vo42kj55w",
    "osm_extended": "mrpqu8o796e6xzk",
    "station_wards": "m74rdmspn3trrqc",
    "station_crime": "mxwixub7d0q5i00",
}


def load_stations() -> List[Dict]:
    """Load all stations from data/stations.json."""
    path = ROOT / "data" / "stations.json"
    return json.loads(path.read_text())


class NocoDB:
    """Simple NocoDB v2 API client."""

    def __init__(self, table_name: str):
        self.table_id = TABLE_IDS[table_name]
        self.base_url = f"{NOCODB_API_URL}/api/v2/tables/{self.table_id}"
        self.headers = {
            "xc-token": NOCODB_API_TOKEN,
            "Content-Type": "application/json",
        }

    def get_existing_slugs(self, field: str = "slug") -> Set[str]:
        """Get all existing slugs/keys in the table (for incremental scraping)."""
        slugs = set()
        offset = 0
        limit = 200
        while True:
            resp = requests.get(
                f"{self.base_url}/records",
                headers=self.headers,
                params={"fields": field, "limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("list", [])
            if not rows:
                break
            for row in rows:
                val = row.get(field)
                if val:
                    slugs.add(val)
            if len(rows) < limit:
                break
            offset += limit
        return slugs

    def upsert_record(self, record: dict):
        """Insert a single record. NocoDB auto-generates Id."""
        resp = requests.post(
            f"{self.base_url}/records",
            headers=self.headers,
            json=record,
        )
        resp.raise_for_status()
        return resp.json()

    def bulk_insert(self, records: List[Dict], batch_size: int = 100):
        """Insert records in batches."""
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            resp = requests.post(
                f"{self.base_url}/records",
                headers=self.headers,
                json=batch,
            )
            resp.raise_for_status()
        return len(records)

    def update_record(self, record_id: int, fields: dict):
        """Update an existing record by its NocoDB Id."""
        resp = requests.patch(
            f"{self.base_url}/records",
            headers=self.headers,
            json=[{"Id": record_id, **fields}],
        )
        resp.raise_for_status()
        return resp.json()

    def get_all_records(self, fields: Optional[List[str]] = None) -> List[Dict]:
        """Fetch all records from the table."""
        all_rows = []
        offset = 0
        limit = 200
        params = {"limit": limit}
        if fields:
            params["fields"] = ",".join(fields)
        while True:
            params["offset"] = offset
            resp = requests.get(
                f"{self.base_url}/records",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("list", [])
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < limit:
                break
            offset += limit
        return all_rows


class RateLimiter:
    """Simple rate limiter with configurable delay."""

    def __init__(self, delay_seconds: float = 2.0):
        self.delay = delay_seconds
        self.last_request = 0.0

    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()
