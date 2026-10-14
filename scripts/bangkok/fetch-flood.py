#!/usr/bin/env python3
"""Bangkok flood exposure from ThaiFloodRisk open data (CRTKY-186, ADR #1).

Downloads the pinned Zenodo archive (CC BY 4.0), verifies its SHA-256,
and distills two per-district CSVs into data/bangkok/flood.json:

  1. bangkok-street-flooding-2021-2026.csv  — BMA Drainage and Sewerage
     Department reported standing-water episodes per khet, 2021–2026
     (episodes / days / max depth / median duration).
  2. bangkok-2011-flood-by-district.csv     — GISTDA satellite-derived share
     of each district flooded in 2011 (the long-memory signal; covers the
     districts that report ~0 recent episodes).

Doctrine (same as scripts/scrapers/ingest-crime-open-data.py): the source
archive is SHA-pinned; a checksum mismatch is FATAL; coverage gates verify
all 50 khets join via the alias table.

Usage:
  uv run scripts/bangkok/fetch-flood.py            # fetch + verify + write
  uv run scripts/bangkok/fetch-flood.py --offline  # rebuild from a cached zip

Refresh: re-run when a new Zenodo version is published (v1.0.0 = 2026-10-09);
update VERSION + SHA below together.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bangkok" / "flood.json"
CACHE = ROOT / "data" / "bangkok" / "raw" / "thaifloodrisk.zip"

VERSION = "v1.0.0"
# Concept DOI 10.5281/zenodo.23260465 → version record 23260466 (v1.0.0).
ARCHIVE_URL = "https://zenodo.org/api/records/23260466/files/aroblase/thailand-flood-data-v1.0.0.zip/content"
ARCHIVE_SHA256 = "8ce4a1c95771f56204d979dafcb61df44f4f2aee4e19fbf40adc75ebbb8b8ddf"
ARCHIVE_SIZE = 68_400

# thaifloodrisk slugs (minus the `bangkok-` prefix) that differ from the
# repo's district slugs — verified by diffing the two lists (research note
# §1.4). Join on this table, never on a naive prefix strip.
SLUG_ALIASES = {
    "bung-kum": "bueng-kum",
    "sathorn": "sathon",
    "yannawa": "yan-nawa",
    "noi": "bangkok-noi",   # tf strips only the prefix once: bangkok-bangkok-noi → noi
    "yai": "bangkok-yai",
}

# 2011 CSV spells some district names differently (research note §2 +
# verified diff against districts.json name_en).
NAME_FIXES = {
    "Rat Thewi": "Ratchathewi",
    "Bang Su": "Bang Sue",
    "Bung Kum": "Bueng Kum",
    "Khanna Yao": "Khan Na Yao",
    "Sa Thon": "Sathon",
    "Thung Khu": "Thung Khru",
    "Wang Thong Lang": "Wang Thonglang",
    "Yannawa": "Yan Nawa",
}

STREET_CSV = "data/bangkok-street-flooding-2021-2026.csv"
FLOOD2011_CSV = "data/bangkok-2011-flood-by-district.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def fetch(offline: bool) -> bytes:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if offline:
        if not CACHE.exists():
            sys.exit("FATAL: --offline but no cached archive at " + str(CACHE))
    else:
        import urllib.request

        print(f"Downloading {ARCHIVE_URL} …")
        req = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "city-rating/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            CACHE.write_bytes(resp.read())
        print(f"  saved {CACHE} ({CACHE.stat().st_size:,} bytes)")
    actual = sha256(CACHE)
    if actual != ARCHIVE_SHA256:
        sys.exit(
            f"FATAL: archive SHA-256 mismatch.\n  expected {ARCHIVE_SHA256}\n  actual   {actual}\n"
            "A new Zenodo version likely shipped — review it, then bump VERSION/ARCHIVE_SHA256 together."
        )
    if CACHE.stat().st_size != ARCHIVE_SIZE:
        sys.exit(f"FATAL: archive size {CACHE.stat().st_size} != pinned {ARCHIVE_SIZE}")
    return CACHE.read_bytes()


def read_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    """Read a member as UTF-8 with BOM (the archive CSVs carry a BOM)."""
    with zf.open(name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        return list(csv.DictReader(text))


def tf_slug_to_repo(row_slug: str) -> str:
    s = row_slug.removeprefix("bangkok-")
    return SLUG_ALIASES.get(s, s)


def parse(archive: bytes, repo_slugs: list[str]) -> dict:
    zf = zipfile.ZipFile(io.BytesIO(archive))
    prefix = next(n for n in zf.namelist() if n.endswith(STREET_CSV)).rsplit("/", 2)[0]

    street = read_csv(zf, f"{prefix}/{STREET_CSV}")
    assert len(street) == 50, f"expected 50 street-flooding rows, got {len(street)}"

    out: dict[str, dict] = {}
    for r in street:
        slug = tf_slug_to_repo(r["slug"])
        if slug not in repo_slugs:
            sys.exit(f"FATAL: slug {slug!r} (from {r['slug']!r}) not in districts.json — extend SLUG_ALIASES")
        out[slug] = {
            "episodes_total": int(r["episodes"]),
            "episodes_by_year": {str(y): int(r[f"episodes_{y}"]) for y in range(2021, 2027)},
            "days_total": int(r["days"]),
            "max_height_cm": int(r["max_height_cm"]) if r["max_height_cm"] else None,
            "median_duration_min": int(r["median_duration_min"]) if r["median_duration_min"] else None,
        }

    # 2011 share: rows are subdistrict-level; the district column is repeated.
    rows11 = read_csv(zf, f"{prefix}/{FLOOD2011_CSV}")
    share11: dict[str, float] = {}
    share1224: dict[str, float] = {}
    for r in rows11:
        name = NAME_FIXES.get(r["district_en"], r["district_en"])
        share11[name] = float(r["district_share_flooded_2011_pct"])
        share1224[name] = float(r["district_share_flooded_2012_2024_pct"])

    # join by English name against districts.json
    districts = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "districts.json").read_text())
    items = districts if isinstance(districts, list) else districts["districts"]
    name_to_slug = {NAME_FIXES.get(d["name_en"], d["name_en"]): d["slug"] for d in items}
    for name, slug in name_to_slug.items():
        if slug not in out:
            sys.exit(f"FATAL: 2011 join missed district {name!r} ({slug})")
        out[slug]["share_flooded_2011_pct"] = share11.get(name)
        out[slug]["share_flooded_2012_2024_pct"] = share1224.get(name)

    # Gates (ingest-crime doctrine).
    assert sum(v["episodes_total"] for v in out.values()) == 1762, "episode total drifted from 1,762"
    missing = [s for s, v in out.items() if v["share_flooded_2011_pct"] is None]
    assert not missing, f"2011 share missing for: {missing}"
    zeros = sum(1 for v in out.values() if v["episodes_total"] == 0)
    assert zeros == 3, f"expected 3 zero-episode districts, got {zeros}"

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="Use the cached archive; no network")
    args = ap.parse_args()

    archive = fetch(args.offline)
    districts = json.loads((ROOT / "app" / "src" / "data" / "bangkok" / "districts.json").read_text())
    items = districts if isinstance(districts, list) else districts["districts"]
    repo_slugs = sorted(d["slug"] for d in items)

    per_khet = parse(archive, repo_slugs)
    doc = {
        "_meta": {
            "source": "ThaiFloodRisk.com (2026), republishing BMA Drainage and Sewerage "
                      "Department street-flooding records and GISTDA 2011 satellite flood share",
            "url": "https://thaifloodrisk.com/en/open-data",
            "zenodo": "https://doi.org/10.5281/zenodo.23260465",
            "version": VERSION,
            "archive_sha256": ARCHIVE_SHA256,
            "license": "CC BY 4.0",
            "fetched": "2026-10-14",
            "notes": "Episodes are *reported* standing-water episodes on main roads "
                     "(2021–2026 window, one weather regime; 2025–2026 dominate). The 2011 "
                     "share is satellite-derived long memory and covers districts with ~0 "
                     "recent reports. Not a hazard model — relative ranking only.",
        },
        "districts": {slug: per_khet[slug] for slug in repo_slugs},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(ROOT)} ({len(per_khet)} districts)")
    top = sorted(per_khet.items(), key=lambda kv: -kv[1]["episodes_total"])[:5]
    for slug, v in top:
        print(f"  {slug:22s} episodes={v['episodes_total']:3d}  2011 share={v['share_flooded_2011_pct']}%")


if __name__ == "__main__":
    main()
