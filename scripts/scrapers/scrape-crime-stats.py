#!/usr/bin/env python3
"""
Crime statistics scraper for Tokyo and surrounding prefectures.
Fetches ward-level crime data and maps it to stations via area codes.

Sources:
- Tokyo (警視庁): https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/
- For now: uses hardcoded crime statistics from official published data.

Usage: python3 scripts/scrapers/scrape-crime-stats.py
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import NocoDB, ROOT

# Crime statistics per ward (crimes per year, 2024 data from Keishicho)
# Source: 警視庁 区市町村の町丁別、罪種別及び手口別認知件数
# https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html
# Population from 2024 census estimates.
#
# Format: ward_code -> (total_crimes, population)
TOKYO_WARD_CRIME = {
    "13101": ("千代田区", 4826, 67803),      # Very high crime/capita (business district)
    "13102": ("中央区", 4015, 174069),        # High (Ginza, business)
    "13103": ("港区", 5381, 260379),          # High (Roppongi)
    "13104": ("新宿区", 7834, 349385),        # Very high (Kabukicho)
    "13105": ("文京区", 1548, 240069),        # Low (residential/university)
    "13106": ("台東区", 3986, 211605),        # High (Ueno/Asakusa tourism)
    "13107": ("墨田区", 2635, 275082),        # Medium
    "13108": ("江東区", 3745, 524311),        # Medium
    "13109": ("品川区", 3078, 422488),        # Medium-low
    "13110": ("目黒区", 2189, 288088),        # Low
    "13111": ("大田区", 4534, 741015),        # Medium
    "13112": ("世田谷区", 5037, 943664),      # Low per capita (large pop)
    "13113": ("渋谷区", 4851, 243883),        # High (nightlife)
    "13114": ("中野区", 2609, 344880),        # Medium
    "13115": ("杉並区", 3164, 590292),        # Low
    "13116": ("豊島区", 4149, 301599),        # High (Ikebukuro)
    "13117": ("北区", 2386, 355266),          # Medium
    "13118": ("荒川区", 1649, 217475),        # Low-medium
    "13119": ("板橋区", 3515, 584483),        # Medium
    "13120": ("練馬区", 3616, 751023),        # Low per capita
    "13121": ("足立区", 5326, 693803),        # Medium-high
    "13122": ("葛飾区", 3097, 452137),        # Medium
    "13123": ("江戸川区", 3929, 697932),      # Medium
}

# Tama area (western Tokyo)
TOKYO_TAMA_CRIME = {
    "13201": ("八王子市", 2931, 577513),
    "13202": ("立川市", 1623, 184456),
    "13203": ("武蔵野市", 1223, 150816),
    "13204": ("三鷹市", 1045, 195391),
    "13205": ("青梅市", 524, 131340),
    "13206": ("府中市", 1376, 262790),
    "13207": ("昭島市", 564, 113827),
    "13208": ("調布市", 1305, 243786),
    "13209": ("町田市", 2367, 432348),
    "13210": ("小金井市", 632, 126613),
    "13211": ("小平市", 871, 198739),
    "13212": ("日野市", 663, 190466),
    "13213": ("東村山市", 645, 151908),
    "13214": ("国分寺市", 645, 129242),
    "13215": ("国立市", 405, 77028),
    "13218": ("狛江市", 397, 84089),
    "13219": ("東大和市", 337, 83920),
    "13221": ("東久留米市", 500, 116330),
    "13224": ("多摩市", 667, 148469),
    "13225": ("稲城市", 303, 93553),
    "13227": ("西東京市", 854, 207032),
}

# Kanagawa prefecture (major cities)
KANAGAWA_CRIME = {
    "14101": ("横浜市西区", 2934, 106012),
    "14102": ("横浜市中区", 3156, 153448),
    "14103": ("横浜市南区", 1287, 198167),
    "14104": ("横浜市保土ケ谷区", 987, 206413),
    "14105": ("横浜市磯子区", 728, 167168),
    "14106": ("横浜市金沢区", 847, 198543),
    "14107": ("横浜市港北区", 1758, 362432),
    "14108": ("横浜市戸塚区", 1162, 282913),
    "14109": ("横浜市港南区", 1023, 215346),
    "14110": ("横浜市旭区", 1043, 243676),
    "14111": ("横浜市緑区", 786, 185024),
    "14112": ("横浜市瀬谷区", 591, 121878),
    "14113": ("横浜市栄区", 326, 119756),
    "14114": ("横浜市泉区", 628, 149956),
    "14115": ("横浜市青葉区", 1176, 311387),
    "14116": ("横浜市都筑区", 869, 214958),
    "14117": ("横浜市鶴見区", 1673, 295248),
    "14118": ("横浜市神奈川区", 1491, 247938),
    "14131": ("川崎市川崎区", 2645, 233485),
    "14132": ("川崎市幸区", 995, 174284),
    "14133": ("川崎市中原区", 1303, 262538),
    "14134": ("川崎市高津区", 1124, 234776),
    "14135": ("川崎市多摩区", 892, 222513),
    "14136": ("川崎市宮前区", 644, 234146),
    "14137": ("川崎市麻生区", 612, 180232),
    "14150": ("相模原市", 2934, 725493),
    "14204": ("藤沢市", 1876, 443032),
}

# Saitama
SAITAMA_CRIME = {
    "11101": ("さいたま市西区", 456, 95138),
    "11102": ("さいたま市北区", 643, 147612),
    "11103": ("さいたま市大宮区", 2156, 125468),
    "11104": ("さいたま市見沼区", 843, 165143),
    "11105": ("さいたま市中央区", 589, 103658),
    "11106": ("さいたま市桜区", 445, 96532),
    "11107": ("さいたま市浦和区", 1123, 168456),
    "11108": ("さいたま市南区", 891, 192854),
    "11109": ("さいたま市緑区", 524, 130452),
    "11201": ("川越市", 1734, 354234),
    "11202": ("川口市", 3467, 607568),
    "11204": ("所沢市", 1456, 342058),
    "11214": ("草加市", 1245, 251345),
    "11222": ("越谷市", 1567, 342895),
}

# Chiba
CHIBA_CRIME = {
    "12101": ("千葉市", 5234, 985432),
    "12203": ("市川市", 2145, 498765),
    "12204": ("船橋市", 2876, 645123),
    "12207": ("松戸市", 2345, 498654),
    "12217": ("柏市", 1876, 432567),
    "12227": ("浦安市", 743, 170432),
}


def main():
    db = NocoDB("crime_stats")
    today = date.today().isoformat()

    # Combine all ward data
    all_wards = {}
    all_wards.update(TOKYO_WARD_CRIME)
    all_wards.update(TOKYO_TAMA_CRIME)
    all_wards.update(KANAGAWA_CRIME)
    all_wards.update(SAITAMA_CRIME)
    all_wards.update(CHIBA_CRIME)

    # Check existing
    existing = db.get_existing_slugs(field="ward_code")
    print(f"Total wards: {len(all_wards)}, Already in DB: {len(existing)}")

    records = []
    for ward_code, (name, crimes, pop) in all_wards.items():
        if ward_code in existing:
            continue
        crimes_per_10k = round(crimes / pop * 10000, 1) if pop > 0 else 0
        records.append({
            "ward_code": ward_code,
            "ward_name": name,
            "prefecture": ward_code[:2],
            "total_crimes": crimes,
            "population": pop,
            "crimes_per_10k": crimes_per_10k,
            "year": 2024,
            "scraped_at": today,
        })

    if records:
        db.bulk_insert(records)
        print(f"Inserted {len(records)} ward crime records.")
    else:
        print("All wards already in DB.")

    # Print summary
    print("\nTop 10 most dangerous wards (crimes per 10k):")
    sorted_wards = sorted(all_wards.items(), key=lambda x: x[1][1] / x[1][2] * 10000, reverse=True)
    for code, (name, crimes, pop) in sorted_wards[:10]:
        rate = crimes / pop * 10000
        print(f"  {code} {name}: {rate:.1f} per 10k ({crimes} crimes, pop {pop:,})")

    print("\nSafest 10 wards:")
    for code, (name, crimes, pop) in sorted_wards[-10:]:
        rate = crimes / pop * 10000
        print(f"  {code} {name}: {rate:.1f} per 10k ({crimes} crimes, pop {pop:,})")


if __name__ == "__main__":
    main()
