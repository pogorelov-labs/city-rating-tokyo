#!/usr/bin/env python3
"""
Suumo rent scraper v2 — full coverage using station-area-codes.json mapping.
Scrapes by area code (ward/city), then assigns to individual stations.

Covers: Tokyo 23 wards + Tama cities + Kanagawa + Saitama + Chiba

Usage: python3 scripts/scrape-suumo-v2.py [--delay SECONDS]
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ja,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml',
}


def detect_prefecture(area_code):
    """Detect prefecture from Suumo area code for URL building."""
    if area_code.startswith('13'):
        return '13'  # Tokyo
    elif area_code.startswith('14'):
        return '14'  # Kanagawa
    elif area_code.startswith('11'):
        return '11'  # Saitama
    elif area_code.startswith('12'):
        return '12'  # Chiba
    return '13'


def build_suumo_url(area_code, layout_codes, min_area=40, max_area=55):
    """Build Suumo search URL."""
    pref = detect_prefecture(area_code)
    params = {
        'ar': '030',
        'bs': '040',
        'ta': pref,
        'sc': area_code,
        'cb': '0.0',
        'ct': '9999999',
        'mb': str(min_area),
        'mt': str(max_area),
        'et': '10',
        'cn': '9999999',
        'pc': '50',
    }
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
            area_el = detail.select_one('.cassetteitem_menseki')
            if not rent_el:
                continue
            rent_text = rent_el.get_text(strip=True)
            area_text = area_el.get_text(strip=True) if area_el else ''
            rent_match = re.search(r'([\d.]+)万円', rent_text)
            if not rent_match:
                continue
            rent_yen = int(float(rent_match.group(1)) * 10000)
            area_match = re.search(r'([\d.]+)', area_text)
            area_sqm = float(area_match.group(1)) if area_match else 0
            rents.append({'rent': rent_yen, 'area': area_sqm})
    return rents


def scrape_area(area_code, delay=2.5):
    """Scrape rents for a specific area code."""
    # 1K/1LDK
    small_rents = []
    url = build_suumo_url(area_code, ['02', '04'])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            small_rents = parse_listings(resp.text)
        time.sleep(delay)
    except Exception as e:
        print(f'  Error 1K/1LDK: {e}')

    # 2LDK
    large_rents = []
    url = build_suumo_url(area_code, ['07'])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            large_rents = parse_listings(resp.text)
        time.sleep(delay)
    except Exception as e:
        print(f'  Error 2LDK: {e}')

    small_prices = [r['rent'] for r in small_rents if 35 <= r['area'] <= 55]
    large_prices = [r['rent'] for r in large_rents if 40 <= r['area'] <= 70]

    return {
        '1k_1ldk': int(statistics.median(small_prices)) if small_prices else None,
        '2ldk': int(statistics.median(large_prices)) if large_prices else None,
        'sample_small': len(small_prices),
        'sample_large': len(large_prices),
    }


def main():
    delay = 2.5
    if '--delay' in sys.argv:
        idx = sys.argv.index('--delay')
        delay = float(sys.argv[idx + 1])

    # Load station-area mapping
    mapping_path = Path(__file__).parent / 'station-area-codes.json'
    mapping = json.loads(mapping_path.read_text())
    station_map = mapping['stationAreaMap']

    # Group by unique area codes
    code_to_area = {}
    for slug, info in station_map.items():
        code = info['area_code']
        if code not in code_to_area:
            code_to_area[code] = {
                'key': info['area_key'],
                'name': info['area_name'],
                'stations': [],
            }
        code_to_area[code]['stations'].append(slug)

    total_codes = len(code_to_area)
    print(f'Scraping {total_codes} unique area codes covering {len(station_map)} stations')
    print(f'Delay: {delay}s between requests\n')

    # Load existing data to skip already scraped
    output_path = Path(__file__).parent.parent / 'data' / 'rent' / 'rent-averages-v2.json'
    existing = {}
    if output_path.exists():
        existing = json.loads(output_path.read_text())

    area_rents = {}
    scraped = 0

    for code, area_info in sorted(code_to_area.items()):
        # Check if we already have data for all stations in this area
        all_have_data = all(slug in existing for slug in area_info['stations'])
        if all_have_data:
            print(f'[skip] {area_info["name"]} ({code}) — already scraped')
            # Reuse existing
            for slug in area_info['stations']:
                area_rents[slug] = existing[slug]
            continue

        scraped += 1
        stations_str = ', '.join(area_info['stations'][:5])
        if len(area_info['stations']) > 5:
            stations_str += f' +{len(area_info["stations"]) - 5} more'

        print(f'[{scraped}/{total_codes}] {area_info["name"]} ({code}): {stations_str}')

        result = scrape_area(code, delay)

        print(f'  1K/1LDK: {result["sample_small"]} listings, median={result["1k_1ldk"]}')
        print(f'  2LDK:    {result["sample_large"]} listings, median={result["2ldk"]}')

        # Assign to all stations in this area
        for slug in area_info['stations']:
            area_rents[slug] = {
                '1k_1ldk': result['1k_1ldk'],
                '2ldk': result['2ldk'],
                'source': 'suumo',
                'updated': time.strftime('%Y-%m'),
                'area_code': code,
                'area_name': area_info['name'],
            }

        # Save incrementally
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(area_rents, indent=2, ensure_ascii=False))

    # Final save
    output_path.write_text(json.dumps(area_rents, indent=2, ensure_ascii=False))

    # Also copy to app data
    app_path = Path(__file__).parent.parent / 'app' / 'src' / 'data' / 'rent-averages.json'
    app_path.write_text(json.dumps(area_rents, indent=2, ensure_ascii=False))

    with_data = sum(1 for v in area_rents.values() if v['1k_1ldk'] is not None)
    print(f'\nDone! {len(area_rents)} stations total, {with_data} with rent data')
    print(f'Saved to {output_path} and {app_path}')


if __name__ == '__main__':
    main()
