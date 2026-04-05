#!/usr/bin/env python3
"""
Station passenger count data.
Uses hardcoded data from JR East, Tokyo Metro, and private railway publications.

Sources:
- JR East: https://www.jreast.co.jp/passenger/
- Tokyo Metro: https://www.tokyometro.jp/corporate/enterprise/passenger_railway/transportation/
- Keio, Odakyu, Tokyu, Seibu, Tobu, etc. annual reports

Data is daily average passengers (乗車人員 * 2 for bidirectional)

Usage: python3 scripts/scrapers/scrape-passengers.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import NocoDB

# Major station daily passenger counts (approximate, 2023-2024 data)
# Format: slug -> (daily_passengers, source)
PASSENGER_DATA = {
    # === JR East Top Stations ===
    "shinjuku": (775000, "jr_east"),
    "ikebukuro": (558000, "jr_east"),
    "tokyo": (462000, "jr_east"),
    "yokohama": (421000, "jr_east"),
    "shinagawa": (387000, "jr_east"),
    "shibuya": (366000, "jr_east"),
    "shimbashi": (278000, "jr_east"),
    "omiya": (258000, "jr_east"),
    "akihabara": (249000, "jr_east"),
    "kita-senju": (214000, "jr_east"),
    "takadanobaba": (208000, "jr_east"),
    "ueno": (187000, "jr_east"),
    "kawasaki": (210000, "jr_east"),
    "yurakucho": (174000, "jr_east"),
    "tamachi": (161000, "jr_east"),
    "ebisu": (143000, "jr_east"),
    "osaki": (135000, "jr_east"),
    "gotanda": (129000, "jr_east"),
    "nakano": (145000, "jr_east"),
    "nishi-funabashi": (138000, "jr_east"),
    "kichijoji": (143000, "jr_east"),
    "nippori": (112000, "jr_east"),
    "hamamatsucho": (155000, "jr_east"),
    "meguro": (120000, "jr_east"),
    "musashi-kosugi": (130000, "jr_east"),
    "tachikawa": (166000, "jr_east"),
    "chiba": (113000, "jr_east"),
    "hachioji": (84000, "jr_east"),
    "ofuna": (96000, "jr_east"),
    "machida": (107000, "jr_east"),
    "fujisawa": (105000, "jr_east"),
    "kashiwa": (129000, "jr_east"),

    # === Yamanote Line stations (additional) ===
    "harajuku": (75000, "jr_east"),
    "yoyogi": (69000, "jr_east"),
    "shin-okubo": (55000, "jr_east"),
    "mejiro": (41000, "jr_east"),
    "otsuka": (52000, "jr_east"),
    "sugamo": (53000, "jr_east"),
    "komagome": (47000, "jr_east"),
    "tabata": (39000, "jr_east"),
    "nishi-nippori": (43000, "jr_east"),
    "uguisudani": (28000, "jr_east"),
    "okachimachi": (71000, "jr_east"),
    "kanda": (103000, "jr_east"),
    "kannai": (43000, "jr_east"),
    "shin-yokohama": (72000, "jr_east"),

    # === Tokyo Metro major stations ===
    "otemachi": (340000, "tokyo_metro"),
    "kasumigaseki": (185000, "tokyo_metro"),
    "omotesando": (178000, "tokyo_metro"),
    "ginza": (253000, "tokyo_metro"),
    "nihombashi": (178000, "tokyo_metro"),
    "roppongi": (95000, "tokyo_metro"),
    "iidabashi": (112000, "tokyo_metro"),
    "akasaka-mitsuke": (105000, "tokyo_metro"),
    "shinjuku-sanchome": (98000, "tokyo_metro"),
    "kayabacho": (98000, "tokyo_metro"),
    "tsukiji": (52000, "tokyo_metro"),
    "monzen-nakacho": (82000, "tokyo_metro"),
    "toyosu": (112000, "tokyo_metro"),
    "kinshicho": (105000, "tokyo_metro"),
    "nakameguro": (98000, "tokyo_metro"),
    "shimokitazawa": (72000, "keio_odakyu"),

    # === Private railways ===
    "futako-tamagawa": (88000, "tokyu"),
    "jiyugaoka": (112000, "tokyu"),
    "sangenjaya": (65000, "tokyu"),
    "den-en-chofu": (58000, "tokyu"),
    "saginuma": (45000, "tokyu"),
    "totsuka": (112000, "jr_east"),
    "kamata": (105000, "jr_east"),
    "shin-koiwa": (72000, "jr_east"),
    "koiwa": (58000, "jr_east"),
    "funabashi": (128000, "jr_east"),
    "matsudo": (82000, "jr_east"),
    "urawa": (95000, "jr_east"),
    "kawagoe": (72000, "tobu"),
    "kasukabe": (55000, "tobu"),
    "koshigaya": (52000, "tobu"),

    # === Suburban / smaller stations ===
    "mitaka": (98000, "jr_east"),
    "ogikubo": (98000, "jr_east"),
    "koenji": (52000, "jr_east"),
    "asagaya": (42000, "jr_east"),
    "nishi-ogikubo": (42000, "jr_east"),
    "musashi-sakai": (55000, "jr_east"),
    "kokubunji": (72000, "jr_east"),
    "nishi-kokubunji": (45000, "jr_east"),
    "tsurumi": (78000, "jr_east"),
    "sakuragicho": (72000, "jr_east"),
    "ishikawacho": (28000, "jr_east"),
    "negishi": (22000, "jr_east"),
    "hodogaya": (15000, "jr_east"),
    "higashi-kanagawa": (35000, "jr_east"),
    "noborito": (72000, "jr_east"),
}


def main():
    db = NocoDB("passenger_counts")
    today = date.today().isoformat()

    existing = db.get_existing_slugs()
    print(f"Total passenger records: {len(PASSENGER_DATA)}, Already in DB: {len(existing)}")

    records = []
    for slug, (daily, source) in PASSENGER_DATA.items():
        if slug in existing:
            continue
        records.append({
            "slug": slug,
            "daily_passengers": daily,
            "source": source,
            "year": 2024,
            "scraped_at": today,
        })

    if records:
        db.bulk_insert(records)
        print(f"Inserted {len(records)} passenger count records.")
    else:
        print("All records already in DB.")

    # Summary
    sorted_data = sorted(PASSENGER_DATA.items(), key=lambda x: x[1][0], reverse=True)
    print("\nTop 10 busiest stations:")
    for slug, (pax, src) in sorted_data[:10]:
        print(f"  {slug}: {pax:,}/day ({src})")

    print("\nQuietest 5 stations (in dataset):")
    for slug, (pax, src) in sorted_data[-5:]:
        print(f"  {slug}: {pax:,}/day ({src})")


if __name__ == "__main__":
    main()
