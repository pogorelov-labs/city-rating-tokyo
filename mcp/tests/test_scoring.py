"""MCP's shared-anchor adapter retains its public fallback and index rules."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from city_rating_mcp.scoring import percentile_anchors


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
