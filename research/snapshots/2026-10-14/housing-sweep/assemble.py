#!/usr/bin/env python3
"""Assemble housing-bangkok.json + housing-bangkok.csv + LICENSE.txt.

Merges the 46 freshly swept khets (results.json, written by sweep_overpass.py)
with the 4 khets already counted in
research/bangkok/notes/2026-10-13-housing-crtky148.md section 2.
"""
import csv
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# note section 2 rows (counted 2026-10-13 by the prior session, rel-ids verified
# against raw/registry.json): apartments, residential, dormitory, commercial,
# mixed_use, towers>=20, stations, mirror, osm3s snapshot
NOTE_ROWS = {
    "watthana":    dict(apartments=212, residential=18, dormitory=1, commercial=247,
                        mixed_use=0, towers_20plus=136, stations_in_khet=1,
                        mirror="overpass-api.de", snapshot="2026-10-13T22:20Z",
                        rel_id=2938036, osm_name_en="Vadhana", quadrant="NW",
                        source="note 2026-10-13-housing-crtky148.md §2"),
    "bang-na":     dict(apartments=36, residential=15, dormitory=0, commercial=22,
                        mixed_use=0, towers_20plus=10, stations_in_khet=5,
                        mirror="overpass-api.de", snapshot="2026-10-13T22:26Z",
                        rel_id=3146412, osm_name_en="Bang Na", quadrant="SW",
                        source="note 2026-10-13-housing-crtky148.md §2"),
    "khlong-toei": dict(apartments=250, residential=66, dormitory=0, commercial=156,
                        mixed_use=0, towers_20plus=106, stations_in_khet=9,
                        mirror="overpass.kumi.systems", snapshot="2026-07-15T15:22Z",
                        rel_id=2938033, osm_name_en="Khlong Toei", quadrant="SW",
                        source="note 2026-10-13-housing-crtky148.md §2"),
    "huai-khwang": dict(apartments=82, residential=119, dormitory=0, commercial=36,
                        mixed_use=0, towers_20plus=40, stations_in_khet=1,
                        mirror="overpass.monicz.dev", snapshot="2026-07-15T15:22Z",
                        rel_id=2938032, osm_name_en="Huai Khwang", quadrant="NW",
                        source="note 2026-10-13-housing-crtky148.md §2"),
}

SLUG_ORDER = [
    "bang-bon", "bang-kapi", "bang-khae", "bang-khen", "bang-kho-laem",
    "bang-khun-thian", "bang-na", "bang-phlat", "bang-rak", "bang-sue",
    "bangkok-noi", "bangkok-yai", "bueng-kum", "chatuchak", "chom-thong",
    "din-daeng", "don-mueang", "dusit", "huai-khwang", "khan-na-yao",
    "khlong-sam-wa", "khlong-san", "khlong-toei", "lak-si", "lat-krabang",
    "lat-phrao", "min-buri", "nong-chok", "nong-khaem", "pathum-wan",
    "phasi-charoen", "phaya-thai", "phra-khanong", "phra-nakhon",
    "pom-prap-sattru-phai", "prawet", "rat-burana", "ratchathewi", "sai-mai",
    "samphanthawong", "saphan-sung", "sathon", "suan-luang", "taling-chan",
    "thawi-watthana", "thon-buri", "thung-khru", "wang-thonglang", "watthana",
    "yan-nawa",
]

QUOTA = {"apartments", "residential", "dormitory", "commercial", "mixed_use"}


def main():
    results = json.loads((HERE / "results.json").read_text())
    rows = {}
    for slug, r in results.items():
        rows[slug] = {**{k: r[k] for k in ("apartments", "residential", "dormitory",
                                           "commercial", "mixed_use", "towers_20plus",
                                           "stations_in_khet")},
                      "rel_id": r["rel_id"], "osm_name_en": r["osm_name_en"],
                      "quadrant": r["quadrant"], "snapshot": r["snapshot"],
                      "mirror": r["mirror"], "source": "sweep 2026-10-14"}
    for slug, r in NOTE_ROWS.items():
        rows.setdefault(slug, r)

    missing = [s for s in SLUG_ORDER if s not in rows]
    if missing:
        raise SystemExit(f"not swept yet: {missing}")
    assert len(rows) == 50

    for slug, r in rows.items():
        r["buildings_total"] = sum(r[k] for k in QUOTA)
        if r["mixed_use"] != 0:
            print(f"WARN mixed_use>0 in {slug}: {r['mixed_use']}")

    # --- housing-bangkok.json --------------------------------------------
    khets = [{"khet": slug,
              "buildings_total": rows[slug]["buildings_total"],
              "apartments": rows[slug]["apartments"],
              "residential": rows[slug]["residential"],
              "towers_20plus": rows[slug]["towers_20plus"],
              "stations_in_khet": rows[slug]["stations_in_khet"]}
             for slug in SLUG_ORDER]
    registry_stamp = json.loads((HERE / "raw" / "registry.json").read_text())[
        "osm3s"]["timestamp_osm_base"]
    sweeps = sorted({r["snapshot"] for s, r in rows.items() if r["source"].startswith("sweep")})
    out = {
        "meta": {
            "city": "bangkok",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": "Overpass API per-khet area() counts (one request per khet), "
                      "method per research/bangkok/notes/2026-10-13-housing-crtky148.md §2",
            "definitions": {
                "buildings_total": "building=apartments+residential+dormitory+commercial"
                                   "+mixed_use (ways+multipolygon relations), mapped stock only",
                "apartments": "building=apartments (condo proxy, mapped)",
                "residential": "building=residential (low-rise/townhouse, mapped)",
                "towers_20plus": "building:levels>=20, mapped lower bound (no 10-19 band "
                                 "tagged in Bangkok)",
                "stations_in_khet": "railway=station with station=subway|light_rail|"
                                    "monorail inside khet polygon; OSM station=* sub-tag "
                                    "coverage is patchy — treat as indicative (note §5)",
            },
            "registry_snapshot": registry_stamp,
            "sweep_snapshots": sweeps,
            "rows_source": "46 khets swept 2026-10-14 (sweep_overpass.py); 4 khets from "
                           "research/bangkok/notes/2026-10-13-housing-crtky148.md §2 "
                           "(watthana, bang-na, khlong-toei, huai-khwang)",
            "license": "ODbL 1.0, (c) OpenStreetMap contributors — see LICENSE.txt",
            "coverage_note": "OSM building coverage of Bangkok is partial; counts are "
                             "mapped lower bounds, not real-world stock totals",
        },
        "khets": khets,
    }
    (HERE / "housing-bangkok.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    # --- housing-bangkok.csv ---------------------------------------------
    with open(HERE / "housing-bangkok.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["khet", "rel_id", "osm_name_en", "quadrant", "apartments",
                    "residential", "dormitory", "commercial", "mixed_use",
                    "buildings_total", "towers_20plus", "stations_in_khet",
                    "snapshot", "mirror", "source"])
        for slug in SLUG_ORDER:
            r = rows[slug]
            w.writerow([slug, r["rel_id"], r["osm_name_en"], r["quadrant"],
                        r["apartments"], r["residential"], r["dormitory"],
                        r["commercial"], r["mixed_use"], r["buildings_total"],
                        r["towers_20plus"], r["stations_in_khet"],
                        r["snapshot"], r["mirror"], r["source"]])

    print("assembled: housing-bangkok.json (50 khets), housing-bangkok.csv")
    tot = {k: sum(r[k] for r in rows.values())
           for k in ("buildings_total", "apartments", "residential", "towers_20plus",
                     "stations_in_khet")}
    print("city totals:", tot)


if __name__ == "__main__":
    main()
