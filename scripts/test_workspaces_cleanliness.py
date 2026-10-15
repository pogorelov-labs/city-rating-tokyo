"""Offline audit regression: evidence counts, source parity and invalid joins."""
import copy
import csv
import json

import pytest

from audit_workspaces_cleanliness import ROOT, SNAPSHOT, audit, coworking_summary, waste_summary


def test_committed_evidence_matches_audit():
    result = audit()
    expected = json.loads((ROOT / 'research/notes/2026-10-15-workspaces-cleanliness-audit.json').read_text())
    assert result == expected
    assert result['coworking']['tokyo']['without_coordinates'] == 74
    assert result['coworking']['bangkok']['without_coordinates'] == 49
    assert result['coworking_total_without_coordinates'] == 123
    assert result['waste']['rows'] == 459
    assert result['waste']['district_rows'] == 450
    assert result['waste']['district_zero_daily_values']['2017'] == 50
    assert result['waste']['annual_tonnes_excluding_other']['2018'] == '3692869.44'


@pytest.mark.parametrize('lat,lng', [(13.7, None), (None, 100.5), (True, 100), ('13', 100),
                                   (float('nan'), 100), (91, 100), (13, 181)])
def test_invalid_or_partial_coordinates_are_not_silently_counted(lat, lng):
    with pytest.raises(ValueError):
        coworking_summary({'count': 1, 'locations': [{'lat': lat, 'lng': lng, 'brand': 'fixture',
                           'address': 'fixture', 'source_url': 'https://example.org'}]})


def test_missing_coordinates_remain_missing_and_no_locator_rows_are_exported():
    row = {'lat': None, 'lng': None, 'brand': 'fixture', 'address': 'private locator address',
           'name': 'private locator name', 'source_url': 'https://example.org/location/private'}
    summary = coworking_summary({'count': 1, 'locations': [row]})
    assert summary['without_coordinates'] == 1
    assert summary['with_coordinates'] == 0
    assert 'private' not in json.dumps(summary)


@pytest.fixture
def waste_inputs():
    base = ROOT / SNAPSHOT / 'cleanliness-bangkok'
    def rows(name):
        with (base / name).open(encoding='utf-8-sig') as stream:
            return list(csv.DictReader(stream))
    codes = json.loads((base / 'khet-codes.json').read_text())
    return [rows('waste-by-khet-tidy.csv'), rows('garbage-by-khet.csv'), codes,
            {r['slug'] for r in codes}]


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'wrong_slug', 'wrong_year', 'edited_tons',
                                   'edited_daily', 'duplicate_code', 'unknown_code', 'missing_district'])
def test_waste_rejects_ambiguous_joins_and_changed_source_values(waste_inputs, change):
    rows, raw, codes, slugs = copy.deepcopy(waste_inputs)
    if change == 'duplicate': rows.append(dict(rows[-1]))
    elif change == 'missing': rows.pop()
    elif change == 'wrong_slug': rows[-1]['slug'] = 'wrong'
    elif change == 'wrong_year': rows[-1]['year_be'] = '2562'
    elif change == 'edited_tons': rows[-1]['waste_tons'] = '1'
    elif change == 'edited_daily': rows[-1]['waste_tons_per_day'] = '1'
    elif change == 'duplicate_code': codes[-1] = dict(codes[0])
    elif change == 'unknown_code': rows[-1]['dcode'] = '1051'
    elif change == 'missing_district': slugs.remove(next(iter(slugs)))
    with pytest.raises(ValueError):
        waste_summary(rows, raw, codes, slugs)
