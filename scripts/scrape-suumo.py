#!/usr/bin/env python3
"""
Suumo rent scraper for Tokyo station neighborhoods.
Scrapes average rent prices (1K/1LDK and 2LDK) for 40-55 sqm apartments
within 10 min walk of each station.

Strategy: Use Suumo's ward-based search (sc parameter) since station codes
require reverse-engineering. We search by ward + area filter + layout filter.

Usage: python3 scripts/scrape-suumo.py [--stations N] [--delay SECONDS]
"""

import json
import re
import sys
import time
import statistics
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

# Ward codes for Suumo (Tokyo 23 special wards)
WARD_CODES = {
    'chiyoda': '13101', 'chuo': '13102', 'minato': '13103',
    'shinjuku': '13104', 'bunkyo': '13105', 'taito': '13106',
    'sumida': '13107', 'koto': '13108', 'shinagawa': '13109',
    'meguro': '13110', 'ota': '13111', 'setagaya': '13112',
    'shibuya': '13113', 'nakano': '13114', 'suginami': '13115',
    'toshima': '13116', 'kita': '13117', 'arakawa': '13118',
    'itabashi': '13119', 'nerima': '13120', 'adachi': '13121',
    'katsushika': '13122', 'edogawa': '13123',
}

# Station -> ward mapping for our key stations
STATION_WARD = {
    'shinjuku': 'shinjuku', 'shibuya': 'shibuya', 'ikebukuro': 'toshima',
    'tokyo': 'chiyoda', 'ueno': 'taito', 'akihabara': 'chiyoda',
    'shinagawa': 'shinagawa', 'nakano': 'nakano', 'kichijoji': None,  # Musashino city
    'shimokitazawa': 'setagaya', 'ebisu': 'shibuya', 'meguro': 'meguro',
    'koenji': 'suginami', 'sangenjaya': 'setagaya', 'nakameguro': 'meguro',
    'asakusa': 'taito', 'roppongi': 'minato', 'ginza': 'chuo',
    'jiyugaoka': 'meguro', 'harajuku': 'shibuya', 'yoyogi': 'shibuya',
    'takadanobaba': 'shinjuku', 'sugamo': 'toshima', 'gotanda': 'shinagawa',
    'komagome': 'toshima', 'tabata': 'kita', 'otsuka': 'toshima',
    'mejiro': 'toshima', 'osaki': 'shinagawa', 'hamamatsucho': 'minato',
    'omotesando': 'shibuya', 'azabu-juban': 'minato',
    'kiyosumi-shirakawa': 'koto', 'monzen-nakacho': 'koto',
    'iidabashi': 'chiyoda', 'jimbocho': 'chiyoda',
    'kinshicho': 'sumida', 'toyosu': 'koto',
    'yurakucho': 'chiyoda', 'kanda': 'chiyoda', 'okachimachi': 'taito',
    'shimbashi': 'minato', 'tamachi': 'minato', 'otemachi': 'chiyoda',
    'shin-okubo': 'shinjuku', 'uguisudani': 'taito',
    'kita-senju': 'adachi', 'akabane': 'kita', 'nerima': 'nerima',
    'oji': 'kita', 'nagatacho': 'chiyoda', 'aoyama-itchome': 'minato',
    'roppongi-itchome': 'minato', 'shinjuku-sanchome': 'shinjuku',
    'kudanshita': 'chiyoda', 'nihonbashi': 'chuo', 'mitsukoshimae': 'chuo',
    'korakuen': 'bunkyo', 'nezu': 'bunkyo', 'sendagi': 'bunkyo',
    'yushima': 'bunkyo', 'tsukiji': 'chuo', 'nishi-nippori': 'arakawa',
    'nippori': 'arakawa', 'ogikubo': 'suginami', 'asagaya': 'suginami',
    'kamata': 'ota',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ja,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml',
}

def build_suumo_url(ward_code, layout_codes, min_area=40, max_area=55, page=1):
    """Build Suumo search URL for a ward with specific filters."""
    params = {
        'ar': '030',       # Kanto
        'bs': '040',       # Chintai (rental)
        'ta': '13',        # Tokyo
        'sc': ward_code,   # Ward
        'cb': '0.0',       # Min rent (万円) - no minimum
        'ct': '9999999',   # Max rent - no max
        'mb': str(min_area),  # Min area sqm
        'mt': str(max_area),  # Max area sqm
        'et': '10',        # Max walk minutes
        'cn': '9999999',   # No construction year limit
        'pc': '50',        # Results per page
        'page': str(page),
    }
    # Add multiple md params for layouts
    base = 'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?'
    query = urlencode(params)
    for md in layout_codes:
        query += f'&md={md}'
    return base + query


def parse_listings(html):
    """Parse rent prices from Suumo listing page."""
    soup = BeautifulSoup(html, 'html.parser')
    rents = []

    for item in soup.select('.cassetteitem'):
        for detail in item.select('.js-cassette_link'):
            rent_el = detail.select_one('.cassetteitem_price--rent')
            layout_el = detail.select_one('.cassetteitem_madori')
            area_el = detail.select_one('.cassetteitem_menseki')

            if not rent_el:
                continue

            rent_text = rent_el.get_text(strip=True)
            layout_text = layout_el.get_text(strip=True) if layout_el else ''
            area_text = area_el.get_text(strip=True) if area_el else ''

            # Parse rent: "12.5万円" -> 125000
            rent_match = re.search(r'([\d.]+)万円', rent_text)
            if not rent_match:
                continue
            rent_yen = int(float(rent_match.group(1)) * 10000)

            # Parse area: "45.2m2" -> 45.2
            area_match = re.search(r'([\d.]+)', area_text)
            area_sqm = float(area_match.group(1)) if area_match else 0

            rents.append({
                'rent': rent_yen,
                'layout': layout_text,
                'area': area_sqm,
            })

    return rents


def scrape_ward_rents(ward_code, delay=3):
    """Scrape rents for a specific ward."""
    # 1K/1LDK (md=02,04)
    small_rents = []
    url = build_suumo_url(ward_code, ['02', '04'])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            small_rents = parse_listings(resp.text)
        time.sleep(delay)
    except Exception as e:
        print(f'  Error fetching 1K/1LDK: {e}')

    # 2LDK (md=07)
    large_rents = []
    url = build_suumo_url(ward_code, ['07'])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            large_rents = parse_listings(resp.text)
        time.sleep(delay)
    except Exception as e:
        print(f'  Error fetching 2LDK: {e}')

    return small_rents, large_rents


def main():
    delay = 3
    max_stations = 999

    if '--delay' in sys.argv:
        idx = sys.argv.index('--delay')
        delay = float(sys.argv[idx + 1])
    if '--stations' in sys.argv:
        idx = sys.argv.index('--stations')
        max_stations = int(sys.argv[idx + 1])

    # Load current station data
    stations_path = Path(__file__).parent.parent / 'app' / 'src' / 'data' / 'stations.json'
    stations = json.loads(stations_path.read_text())

    # Group stations by ward to minimize requests
    ward_stations = {}
    for station in stations:
        slug = station['slug']
        if slug not in STATION_WARD:
            continue
        ward = STATION_WARD[slug]
        if ward is None:
            continue
        if ward not in ward_stations:
            ward_stations[ward] = []
        ward_stations[ward].append(slug)

    print(f'Scraping {len(ward_stations)} wards covering {sum(len(v) for v in ward_stations.values())} stations')
    print(f'Delay: {delay}s between requests\n')

    # Scrape ward by ward
    ward_rents = {}
    scraped_wards = 0

    for ward, station_slugs in ward_stations.items():
        if scraped_wards >= max_stations:
            break

        ward_code = WARD_CODES.get(ward)
        if not ward_code:
            continue

        print(f'[{scraped_wards+1}/{len(ward_stations)}] Scraping {ward} ({ward_code}) for: {", ".join(station_slugs)}')

        small_rents, large_rents = scrape_ward_rents(ward_code, delay)

        small_prices = [r['rent'] for r in small_rents if 35 <= r['area'] <= 55]
        large_prices = [r['rent'] for r in large_rents if 40 <= r['area'] <= 70]

        median_small = int(statistics.median(small_prices)) if small_prices else None
        median_large = int(statistics.median(large_prices)) if large_prices else None

        print(f'  1K/1LDK: {len(small_prices)} listings, median={median_small}')
        print(f'  2LDK:    {len(large_prices)} listings, median={median_large}')

        ward_rents[ward] = {
            '1k_1ldk': median_small,
            '2ldk': median_large,
            'sample_small': len(small_prices),
            'sample_large': len(large_prices),
        }

        scraped_wards += 1

    # Map ward rents to individual stations
    rent_data = {}
    for station in stations:
        slug = station['slug']
        ward = STATION_WARD.get(slug)
        if ward and ward in ward_rents:
            wr = ward_rents[ward]
            rent_data[slug] = {
                '1k_1ldk': wr['1k_1ldk'],
                '2ldk': wr['2ldk'],
                'source': 'suumo',
                'updated': time.strftime('%Y-%m'),
                'ward': ward,
            }

    # Save
    output_path = Path(__file__).parent.parent / 'data' / 'rent' / 'rent-averages.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rent_data, indent=2, ensure_ascii=False))

    print(f'\nDone! {len(rent_data)} stations with rent data')
    print(f'Saved to {output_path}')


if __name__ == '__main__':
    main()
