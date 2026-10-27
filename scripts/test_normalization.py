"""CRTKY-166: preserved numeric/provenance contracts and stdlib import boundary."""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from normalization_replay import ROOT, fixture_inputs, load_compute, replay_bangkok, replay_compute

sys.path.insert(0, str(ROOT / 'packages/schema/python'))
from city_rating_schema.normalize import midpoint_percentile, percentile_anchors, rent_to_affordability

FIXTURES = ROOT / 'scripts/fixtures/normalization'


def load_bangkok():
    spec = importlib.util.spec_from_file_location('bangkok_math', ROOT / 'scripts/bangkok/ratings.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tokyo_full_compute_golden():
    expected = json.loads((FIXTURES / 'tokyo-golden.json').read_text())['rows']
    rows = replay_compute(load_compute(), fixture_inputs())
    # Includes every serialized confidence/source/date field, not only scores.
    assert json.dumps(rows) == json.dumps(expected)
    by_slug = {r['slug']: r for r in rows}
    for slug in ('osm-only', 'zero', 'missing-hp'):
        assert json.loads(by_slug[slug]['confidence'])['food'] == 'estimate'
        assert json.loads(by_slug[slug]['sources'])['food'] == []


def test_bangkok_committed_aggregate_golden():
    expected = json.loads((FIXTURES / 'bangkok-refresh-2026-10-24-golden.json').read_text())['output']
    # JSON comparison also preserves source ordering and dictionary insertion order.
    assert json.dumps(replay_bangkok(load_bangkok())) == json.dumps(expected)


def test_bangkok_historical_aggregate_golden():
    expected = json.loads((FIXTURES / 'bangkok-golden.json').read_text())['output']
    signals = json.loads((ROOT / 'scripts/fixtures/bangkok-population/adoption/signals.json').read_text())
    assert json.dumps(replay_bangkok(load_bangkok(), signals)) == json.dumps(expected)


def test_bangkok_refresh_golden_changes_have_complete_review_evidence():
    old = json.loads((FIXTURES / 'bangkok-golden.json').read_text())['output']
    new = json.loads((FIXTURES / 'bangkok-refresh-2026-10-24-golden.json').read_text())['output']
    changes = {}
    def collect(before, after, path=()):
        if isinstance(before, dict) and isinstance(after, dict):
            assert before.keys() == after.keys()
            for key in before:
                collect(before[key], after[key], path + (key,))
        elif before != after:
            changes['.'.join(path)] = (before, after)
    collect(old, new)
    review = json.loads((ROOT / 'research/bangkok/notes/2026-10-26-frozen-refresh-review.json').read_text())
    assert {row['path']: (row['before'], row['after']) for row in review['golden_changes']} == changes
    assert all(row['acceptance'] for row in review['golden_changes'])


@pytest.mark.parametrize('invert,expected', [(False, [1, 2, 4, 6, 7, 8, 10]), (True, [10, 8, 7, 6, 4, 2, 1])])
def test_rank_half_to_even_and_order(invert, expected):
    values = {str(i): i for i in range(7)}
    result = midpoint_percentile(values, invert=invert)
    assert list(result) == list(values)
    assert list(result.values()) == expected


def test_ties_singletons_and_transform_collision():
    assert midpoint_percentile({}) == {}
    assert load_compute().log_percentile_normalize(None) == {}
    assert load_bangkok().percentile_normalize(None) == {}
    assert midpoint_percentile({'one': 5}) == {'one': 1}
    assert midpoint_percentile({'one': 5}, invert=True) == {'one': 10}
    assert midpoint_percentile({'a':5,'b':5,'c':5}) == dict(a=6,b=6,c=6)
    a = 1e20
    b = math.nextafter(a, math.inf)
    assert a != b and math.log1p(a) == math.log1p(b)
    assert midpoint_percentile({'a':a,'b':b}) == dict(a=1,b=10)
    assert load_compute().log_percentile_normalize({'a':a,'b':b}) == dict(a=6,b=6)
    # Invalid inputs are not silently dropped/coerced by the shared primitive.
    with pytest.raises(ValueError): midpoint_percentile({'bad': -1}, pre=math.log1p)
    with pytest.raises(TypeError): midpoint_percentile({'bad': None}, pre=math.log1p)


@pytest.mark.parametrize('floor,ceiling', [(80000,300000),(8000,38000)])
def test_rent_missing_clamp_and_rounding(floor, ceiling):
    assert [rent_to_affordability(v,floor,ceiling) for v in (None,0,-1)] == [None]*3
    assert rent_to_affordability(1,floor,ceiling) == 10
    assert rent_to_affordability(ceiling*2,floor,ceiling) == 1
    assert rent_to_affordability((floor+ceiling)/2,floor,ceiling) == 6
    assert [rent_to_affordability(floor+(ceiling-floor)*t,floor,ceiling) for t in (1/6,1/2,5/6)] == [8,6,2]


def test_anchors_keep_small_population_and_empty_contracts():
    assert percentile_anchors([9,1,5,2]) == dict(p5=1,p50=5,p95=9)
    assert percentile_anchors([7]) == dict(p5=7,p50=7,p95=7)
    with pytest.raises(IndexError): load_bangkok().anchors([])


def test_minimal_import_does_not_attempt_pydantic():
    code = f'''
import sys, importlib.abc, warnings
sys.path.insert(0, {str(ROOT / 'scripts/bangkok')!r})
class BlockModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('pydantic', 'city_rating_schema.models')):
            raise AssertionError('stdlib consumer attempted ' + fullname)
sys.meta_path.insert(0, BlockModels())
with warnings.catch_warnings():
    warnings.simplefilter('error')
    import ratings
    assert ratings.percentile_normalize({{'a':1,'b':2}}) == {{'a':1,'b':10}}
    assert ratings.two_source_confidence(False,True) == ('moderate',['osm'])
    from city_rating_schema.normalize import rent_to_affordability
    assert rent_to_affordability(None,80000,300000) is None
'''
    result = subprocess.run([sys.executable, '-S', '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_public_schema_models_still_resolve_lazily():
    code = '''
import city_rating_schema as schema
assert 'city_rating_schema.models' not in __import__('sys').modules
from city_rating_schema import StationRatings
from city_rating_schema.models import StationRatings as Direct
assert StationRatings is Direct
assert schema.RENT_FLOOR == 80000
try: schema.nonexistent
except AttributeError: pass
else: raise AssertionError('unknown attribute must raise')
'''
    import os
    result = subprocess.run([sys.executable, '-c', code], capture_output=True,text=True,
        env={**os.environ,'PYTHONPATH':str(ROOT / 'packages/schema/python')})
    assert result.returncode == 0, result.stderr


def test_missing_pydantic_keeps_optional_public_model_fallback():
    code = f'''
import sys, warnings
sys.path.insert(0,{str(ROOT / 'packages/schema/python')!r})
import city_rating_schema as schema
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    assert schema.StationRatings is None
    assert schema.WeightConfig is None
assert len(caught) == 1 and 'pydantic not installed' in str(caught[0].message)
assert schema.RENT_FLOOR == 80000
'''
    result = subprocess.run([sys.executable,'-S','-c',code],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('a,b,expected', [
    (True,True,('strong',['overture','osm'])),
    (True,False,('moderate',['overture'])),
    (False,True,('moderate',['osm'])),
    (False,False,('estimate',['overture','osm'])),
])
def test_bangkok_confidence_and_source_order(a,b,expected):
    assert load_bangkok().two_source_confidence(a,b) == expected
