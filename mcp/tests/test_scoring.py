"""MCP's shared-anchor adapter retains its public fallback and index rules."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from city_rating_mcp.scoring import composite_score, passes_dealbreakers, percentile_anchors


CASES = json.loads((Path(__file__).resolve().parents[2] / 'packages/schema/fixtures/composite-score.json').read_text())


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
def test_composite_matches_frontend_fixture(case):
    assert composite_score(case['ratings'], case['weights']) == case['expected']


def test_missing_ratings_and_missing_weighted_values():
    assert composite_score(None) is None
    assert composite_score({'food': 9}, {'food': 0, 'safety': 1}) == 0.0


@pytest.mark.parametrize('entry,filters', [
    ({'rent': {'1k_1ldk': 50_000}}, {'min_rent': 60_000}),
    ({'rent': {'1k_1ldk': 100_000}}, {'max_rent': 90_000}),
    ({'transit_minutes': {'hub': 45}}, {'max_commute': 30}),
    ({'transit_minutes': {'hub': 10}}, {'min_commute': 20}),
    ({'ratings': {'food': 3}}, {'category_mins': {'food': 4}}),
    ({'environment': {'elevation_m': 4}}, {'hide_flood_risk': True}),
    ({'environment': {'seismic_risk_tier': 'very_high'}}, {'hide_high_seismic': True}),
    ({'livecams': []}, {'has_live_camera': True}),
])
def test_each_dealbreaker_excludes(entry, filters):
    assert passes_dealbreakers(entry, **filters)[0] is False


def test_missing_rent_is_flagged_only_when_filter_active():
    assert passes_dealbreakers({}, max_rent=100_000) == (True, {'rent_unknown': True})
    assert passes_dealbreakers({}) == (True, {'rent_unknown': False})


@pytest.mark.parametrize('values,expected', [
    ([], {'p5':1.0,'p50':5.5,'p95':10.0}),
    ([7], {'p5':7,'p50':7,'p95':7}),
    ([9,1,5,2], {'p5':1,'p50':5,'p95':9}),
    (list(range(20)), {'p5':1,'p50':10,'p95':19}),
])
def test_anchor_contract(values, expected):
    before = list(values)
    assert percentile_anchors(values) == expected
    assert values == before


def test_empty_fallback_is_not_shared_mutable_state():
    first = percentile_anchors([])
    first['p5'] = -1
    assert percentile_anchors([])['p5'] == 1.0
