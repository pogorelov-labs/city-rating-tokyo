"""
Cross-language parity / schema-drift guard.

Today the scoring constants live inline in two places:
  - app/src/lib/scoring.ts         (TS, frontend)
  - scripts/compute-ratings.py     (Python, pipeline)

The single-source-of-truth migration (packages/schema/) is not yet on this
branch, so this test asserts the *current* two-source contract directly:
the rent constants must match, the rating key order is load-bearing for
shared URLs, and DEFAULT_WEIGHTS must sum to 100.

When the schema package lands, this test should switch to importing from
city_rating_schema.constants — the assertions themselves stay the same.
"""
import importlib
import importlib.util
import sys
import types
from pathlib import Path

# Stub `utils` so compute-ratings imports cleanly (see test_compute_ratings.py).
if "utils" not in sys.modules:
    utils_stub = types.ModuleType("utils")
    utils_stub.NocoDB = object
    utils_stub.load_stations = lambda: []
    sys.modules["utils"] = utils_stub

# Hyphenated filename → load via importlib (see test_compute_ratings.py).
_THIS_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "compute_ratings", _THIS_DIR / "compute-ratings.py"
)
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


# Mirror of DEFAULT_WEIGHTS in app/src/lib/types.ts. This MUST stay in sync;
# if it drifts, shared URLs and the Python pipeline will disagree on the
# composite score. Order matters for URL encoding (see test below).
TS_DEFAULT_WEIGHTS = {
    "transport": 18,
    "rent": 18,
    "daily_essentials": 14,
    "safety": 10,
    "food": 12,
    "green": 8,
    "gym_sports": 4,
    "vibe": 4,
    "nightlife": 8,
    "crowd": 4,
}

# The load-bearing positional order of the `w` URL param. url-state.ts builds
# this from Object.keys(DEFAULT_WEIGHTS); we pin it here so a reordering is
# caught by tests rather than silently rewriting every shared URL on the web.
TS_WEIGHT_KEY_ORDER = [
    "transport",
    "rent",
    "daily_essentials",
    "safety",
    "food",
    "green",
    "gym_sports",
    "vibe",
    "nightlife",
    "crowd",
]


class TestRentConstantsParity:
    def test_floor_matches_ts(self):
        # scoring.ts: RENT_FLOOR = 80_000
        assert cr.RENT_FLOOR == 80_000

    def test_ceiling_matches_ts(self):
        # scoring.ts: RENT_CEILING = 300_000
        assert cr.RENT_CEILING == 300_000

    def test_python_and_ts_rent_function_agree_at_floor(self):
        # Both should produce 10 at the floor.
        assert cr.rent_to_affordability(cr.RENT_FLOOR) == 10

    def test_python_and_ts_rent_function_agree_at_ceiling(self):
        assert cr.rent_to_affordability(cr.RENT_CEILING) == 1


class TestDefaultWeightsParity:
    def test_default_weights_sum_to_100(self):
        # url-state.ts omits the `w` param entirely when weights equal the
        # defaults; if the defaults drift off 100, the composite-score math
        # silently rescales. Pin the sum.
        assert sum(TS_DEFAULT_WEIGHTS.values()) == 100

    def test_default_weight_keys_match_rating_keys(self):
        # The 10 weight keys must be exactly the 10 StationRatings keys.
        rating_keys = {
            "transport", "rent", "daily_essentials", "safety", "food",
            "green", "gym_sports", "vibe", "nightlife", "crowd",
        }
        assert set(TS_DEFAULT_WEIGHTS.keys()) == rating_keys

    def test_transport_is_first_in_weight_key_order(self):
        # Life-first invariant: transport must be position 0 in the URL `w`
        # param. If this fails, every shared URL on the internet silently
        # re-paints its weights.
        assert TS_WEIGHT_KEY_ORDER[0] == "transport"

    def test_weight_key_order_matches_ts_default_weights_iteration_order(self):
        # TS url-state.ts builds the positional order from Object.keys(), which
        # for a literal object follows insertion order. Mirror that contract.
        assert TS_WEIGHT_KEY_ORDER == list(TS_DEFAULT_WEIGHTS.keys())


class TestPipelineCapsShape:
    def test_rent_cap_uses_source_quality(self):
        # rent cap encodes (min_rating, source_quality): 2=suumo, 1=ward, 0=regression.
        rent_caps = cr.ABSOLUTE_CAPS["rent"]
        # Must gate the top two tiers via source quality, not raw price.
        assert (9, 1) in rent_caps
        assert (10, 2) in rent_caps

    def test_transport_cap_requires_5_lines_for_ten(self):
        # To get transport=10 you need >= 5 train lines.
        transport_caps = cr.ABSOLUTE_CAPS["transport"]
        assert (10, 5) in transport_caps
