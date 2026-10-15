"""Offline characterization harness for CRTKY-166; never opens a live store."""
import contextlib
import importlib.util
import io
import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def load_compute(path=None, *, source=None):
    utils = types.ModuleType('utils')
    utils.NocoDB = None
    utils.load_stations = None
    with patch.dict(sys.modules, {'utils': utils}):
        spec = importlib.util.spec_from_file_location('characterized_compute', path or ROOT / 'scripts/compute-ratings.py')
        module = importlib.util.module_from_spec(spec)
        if source is None:
            spec.loader.exec_module(module)
        else:
            exec(compile(source, str(spec.origin), "exec"), module.__dict__)
    return module


def fixture_inputs():
    """Synthetic branch coverage, not claimed to be a production source census."""
    names = ['both', 'hp-only', 'osm-only', 'zero', 'null-osm', 'missing-osm',
             'missing-hp', 'missing-livability', 'tie-a', 'tie-b', 'estat', 'ward', 'regression']
    stations = [dict(slug=s, lat=35.6 + i / 100, lng=139.7, prefecture='Tokyo', line_count=i % 5)
                for i, s in enumerate(names)]
    tables = {key: [] for key in ('hotpepper', 'osm_pois', 'osm_extended', 'osm_livability', 'station_wards')}
    for i, slug in enumerate(names):
        n = i if slug not in ('tie-a', 'tie-b') else 3
        tables['hotpepper'].append(dict(slug=slug, total_count=20*n, midnight_count=n,
            izakaya_count=n, bar_count=n, cafe_count=n, scraped_at='2026-09-01'))
        tables['osm_pois'].append(dict(slug=slug, food_count=10*n, gym_count=n % 3,
            green_count=n, green_area_sqm=n*100, nightlife_count=n,
            convenience_store_count=n, scraped_at='2026-09-02'))
        tables['osm_extended'].append(dict(slug=slug, cultural_venue_count=n % 2,
            pedestrian_street_count=n % 3, karaoke_count=n, nightclub_count=n,
            hostel_count=n, scraped_at='2026-09-03'))
        tables['osm_livability'].append(dict(slug=slug, supermarket_count=n, pharmacy_count=n,
            clinic_count=n, dentist_count=n, bank_count=n, laundry_count=n,
            post_office_count=n, school_count=n, kindergarten_count=n, scraped_at='2026-09-04'))
        tables['station_wards'].append(dict(slug=slug, city_name='Shared' if slug != 'regression' else 'Unseen'))
    for row in tables['hotpepper']:
        if row['slug'] == 'both': row['total_count'] = 30
        if row['slug'] in ('osm-only', 'zero', 'null-osm'): row['total_count'] = 0
    for row in tables['osm_pois']:
        if row['slug'] == 'both': row['food_count'] = 10
        if row['slug'] in ('hp-only', 'zero'): row['food_count'] = 0
        if row['slug'] == 'null-osm': row['food_count'] = None
    for table, slug in [('hotpepper','missing-hp'), ('osm_pois','missing-osm'), ('osm_livability','missing-livability')]:
        tables[table] = [r for r in tables[table] if r['slug'] != slug]
    rent = {s: {'1k_1ldk': 80000 + i*10000, 'source': 'suumo'} for i,s in enumerate(names[:10])}
    rent['estat'] = {'1k_1ldk': 90000, 'source': 'estat'}
    safety = {s: {'rate': i, 'confidence':'strong', 'source':'fixture_police'} for i,s in enumerate(names[:-1])}
    pax = {s: {'daily_passengers': i*10000, 'confidence':'moderate'} for i,s in enumerate(names[::2])}
    return stations, tables, rent, safety, pax


def replay_compute(module, inputs, *, redirects=None):
    stations, tables, rent, safety, pax = inputs
    captured = []
    class OfflineDB:
        def __init__(self, table): self.table = table
        def get_all_records(self): return tables[self.table]
    class FrozenDate(date):
        @classmethod
        def today(cls): return cls(2026, 10, 15)
    def capture(store, records, recovery_dir, **kwargs):
        captured.extend(records)
        return 'offline-memory-only'
    with contextlib.ExitStack() as stack:
        replacements = dict(NocoDB=OfflineDB, load_stations=lambda: stations,
            load_slug_redirects=lambda: redirects or {}, load_rent_data=lambda: rent,
            load_station_safety=lambda: (safety, '2024'), load_passengers=lambda: (pax, '2024'),
            # Missing/invalid inputs deliberately exercise historical compute semantics;
            # source admission and store integrity have separate integration tests.
            check_sources=lambda *args: {}, NocoRatingStore=lambda db: None,
            replace_ratings=capture, date=FrozenDate)
        for name, value in replacements.items(): stack.enter_context(patch.object(module, name, value))
        stack.enter_context(patch.object(sys, 'argv', ['compute', '--no-strict', '--max-source-age-days=90']))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        module.main()
    return captured


def replay_bangkok(module):
    """Replay committed rounded aggregate signals, not the geometry builder."""
    import json
    signals = json.loads((ROOT / 'data/bangkok/signals.json').read_text())
    result = {}
    for layer in ('districts', 'station_areas'):
        rows = signals[layer]
        ratings = {key: module.percentile_normalize({s:r['raw'][key] for s,r in rows.items()}, invert=key=='crowd')
                   for key in ('food','nightlife','daily_essentials','gym_sports','vibe','green','transport','crowd')}
        ratings['rent'] = {s: module.rent_to_affordability(r['raw']['rent']) for s,r in rows.items()}
        thresholds = [(100,30),(20,10),(60,30),(10,5),(15,20)] if layer=='districts' else [(80,20),(10,4),(40,15),(6,3),(6,8)]
        keys = ('food','nightlife','essentials','sports','culture')
        confidence = {s: {k: module.two_source_confidence(r['facts'][k]>=a,r['osm_counts'][k]>=b)
                          for k,(a,b) in zip(keys,thresholds)} for s,r in rows.items()}
        result[layer] = dict(ratings=ratings, confidence=confidence,
            anchors=module.anchors([sum(r['ratings'].values()) / 10 for r in rows.values()]))
    return result
