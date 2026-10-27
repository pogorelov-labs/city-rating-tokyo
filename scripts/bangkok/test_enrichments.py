"""Full-build enrichment contract: exact observations, complete joins, no loss."""
import copy
import json
from pathlib import Path

import pytest

from enrichments import apply_enrichments

ROOT = Path(__file__).resolve().parents[2]
DISTRICT_FIELDS = {'michelin_stars', 'michelin_bib', 'embassies_800m'}
AREA_FIELDS = {'hotels_800m', 'attractions_800m', 'tourist_badge'}


def load(path):
    return json.loads((ROOT / path).read_text())


def outputs():
    return (load('app/src/data/bangkok/districts.json')['districts'],
            load('app/src/data/bangkok/stations.json')['areas'])


def test_applied_values_match_frozen_observations_and_committed_fields():
    districts, areas = outputs()
    original = copy.deepcopy((districts, areas))
    historic = load('scripts/fixtures/bangkok-population/adoption/districts.json')['districts']
    expected_districts = {r['slug']: {k: v for k, v in r['facts'].items() if k in DISTRICT_FIELDS}
                          for r in historic}
    tourism = load('data/tourism/proximity.json')['stations']['bangkok']
    michelin = load('data/michelin/proximity.json')['districts']
    assert len(areas) == len(tourism) == 133
    assert len(michelin) == 9
    # Recreate the spatial builder's omission before composing. No zero fallback.
    for row in districts:
        row['facts'] = {k: v for k, v in row['facts'].items() if k not in DISTRICT_FIELDS}
    for row in areas:
        for key in AREA_FIELDS:
            row.pop(key, None)
    apply_enrichments(ROOT, districts, areas)
    for row in districts:
        actual = {k: v for k, v in row['facts'].items() if k in DISTRICT_FIELDS}
        assert actual == expected_districts[row['slug']]
        if row['slug'] in michelin:
            assert actual['michelin_stars'] == michelin[row['slug']]['stars']
            assert actual['michelin_bib'] == michelin[row['slug']]['bib_gourmand']
    by_id = {r['id']: r for r in areas}
    for area_id, facts in by_id.items():
        assert {k: facts[k] for k in ('hotels_800m', 'attractions_800m')} == tourism[area_id]
        assert facts['tourist_badge'] is (facts['hotels_800m'] >= 50 or facts['attractions_800m'] >= 8)
    assert sum(f['hotels_800m'] > 0 for f in by_id.values()) == 99
    assert sum(f['attractions_800m'] > 0 for f in by_id.values()) == 66
    assert sum(f['tourist_badge'] for f in by_id.values()) == 19
    for area_id, hotels, attractions in [('nana', 197, 3), ('asok', 156, 4)]:
        assert {k: by_id[area_id][k] for k in AREA_FIELDS} == dict(hotels_800m=hotels, attractions_800m=attractions, tourist_badge=True)
    assert sum('michelin_stars' in r['facts'] for r in districts) == 9
    assert sum(r['facts'].get('michelin_stars', 0) for r in districts) == 8
    assert sum(r['facts'].get('michelin_bib', 0) for r in districts) == 12
    embassy = {r['slug']: r['facts']['embassies_800m'] for r in districts if 'embassies_800m' in r['facts']}
    assert embassy == {'bang-rak': 3, 'khlong-toei': 1, 'pathum-wan': 9, 'sathon': 2, 'watthana': 1}
    assert sum(embassy.values()) == 16
    assert (districts, areas) == original  # committed fields also cannot disappear
    once = copy.deepcopy((districts, areas))
    apply_enrichments(ROOT, districts, areas)
    assert (districts, areas) == once


@pytest.mark.parametrize('missing', ['area', 'district', 'tourism', 'michelin', 'embassy'])
def test_missing_join_or_source_fails_before_mutation(tmp_path, missing):
    import shutil
    for path in ['data/bangkok/enrichments-baseline.json', 'data/tourism/proximity.json', 'data/michelin/proximity.json']:
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
    districts, areas = outputs()
    if missing == 'area':
        areas.pop()
    elif missing == 'district':
        districts.pop()
    elif missing in ('tourism', 'michelin'):
        (tmp_path / f'data/{missing}/proximity.json').unlink()
    else:
        path = tmp_path / 'data/bangkok/enrichments-baseline.json'
        doc = json.loads(path.read_text())
        doc['embassies_800m']['nonexistent'] = 1
        path.write_text(json.dumps(doc))
    before = copy.deepcopy((districts, areas))
    with pytest.raises((ValueError, FileNotFoundError)):
        apply_enrichments(tmp_path, districts, areas)
    assert (districts, areas) == before


def test_resident_weight_rounding_can_cross_transport_median_threshold():
    import ratings as r
    ratings = [5, 5, 6]
    weights = [.1019, .1019, .204]
    assert r.weighted_median(ratings, weights) == 6
    encoded = r.encoded_resident_weights(weights)
    assert encoded == [25, 25, 51]  # this side of the threshold still yields 6
    weights = [.1021, .1021, .2043]
    assert r.weighted_median(ratings, weights) == 6
    encoded = r.encoded_resident_weights(weights)
    assert encoded == [26, 26, 51]
    assert r.weighted_median(ratings, encoded) == 5
    assert r.weighted_median(ratings, [w / 250 for w in encoded]) == 5
