"""
Pure-function unit tests for scripts/compute-ratings.py.

compute-ratings.py is structured as a script: its module-level imports pull in
`utils` (which imports `requests`) and run argparse only under `__main__`. To
unit-test the pure math functions (log_percentile_normalize,
rent_to_affordability, apply_absolute_cap) without dragging in the network
stack, we stub `utils` in sys.modules before importing. The functions under
test have no dependency on utils themselves.
"""
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

# --- Stub the `utils` module compute-ratings.py imports at module top ----------
# compute-ratings.py line 32: `from utils import NocoDB, load_stations`.
# utils.py imports `requests`, which is not installed in the test environment
# and isn't needed for the pure math functions we're testing here.
if "utils" not in sys.modules:
    utils_stub = types.ModuleType("utils")
    utils_stub.NocoDB = object  # placeholder; never called from these tests
    utils_stub.load_stations = lambda: []
    sys.modules["utils"] = utils_stub

# Load the module under test. The filename is hyphenated (compute-ratings.py),
# which is not a valid Python identifier, so we use importlib instead of a
# plain `import`. pytest's pythonpath only helps for valid module names.
_THIS_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "compute_ratings", _THIS_DIR / "compute-ratings.py"
)
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


# -----------------------------------------------------------------------------
# rent_to_affordability
# -----------------------------------------------------------------------------
class TestRentToAffordability:
    def test_floor_yields_ten(self):
        assert cr.rent_to_affordability(cr.RENT_FLOOR) == 10

    def test_ceiling_yields_one(self):
        assert cr.rent_to_affordability(cr.RENT_CEILING) == 1

    def test_below_floor_clamps_to_ten(self):
        assert cr.rent_to_affordability(10_000) == 10

    def test_above_ceiling_clamps_to_one(self):
        assert cr.rent_to_affordability(cr.RENT_CEILING + 100_000) == 1

    def test_midpoint(self):
        mid = (cr.RENT_FLOOR + cr.RENT_CEILING) // 2
        # t = 0.5 → 10 - 9*0.5 = 5.5 → round(5.5) = 6 (Python banker's rounding
        # would give 6 for round(5.5); compute-ratings uses builtin round)
        assert cr.rent_to_affordability(mid) == 6

    def test_none_returns_none(self):
        assert cr.rent_to_affordability(None) is None

    def test_zero_returns_none(self):
        # The guard is `if not price or price <= 0` → 0 is falsy → None
        assert cr.rent_to_affordability(0) is None

    def test_negative_returns_none(self):
        assert cr.rent_to_affordability(-50_000) is None

    def test_parity_with_ts_constants(self):
        # Cross-language invariant: the Python rent floor/ceiling MUST match
        # the TS constants in app/src/lib/scoring.ts (RENT_FLOOR=80_000,
        # RENT_CEILING=300_000). If this fails, shared URLs / SSG ratings will
        # silently diverge between frontend and pipeline.
        assert cr.RENT_FLOOR == 80_000
        assert cr.RENT_CEILING == 300_000


# -----------------------------------------------------------------------------
# log_percentile_normalize
# -----------------------------------------------------------------------------
class TestLogPercentileNormalize:
    def test_empty_input_returns_empty(self):
        assert cr.log_percentile_normalize({}) == {}

    def test_single_station_gets_one(self):
        # With n=1, percentile = rank / max(n-1, 1) = 0 / 1 = 0 → rating 1.
        # The max(n-1, 1) guard prevents divide-by-zero but pushes the lone
        # station to the 0th percentile. This is the documented edge behaviour.
        out = cr.log_percentile_normalize({"a": 5})
        assert out["a"] == 1

    def test_all_equal_yields_uniform_high_rating(self):
        # When every value ties, midpoint ranking puts everyone at the top rank
        # → percentile 1.0 → rating 10 for all. This is the "tie" edge case
        # CRTKY-64/65 fixed: previously all tied stations would lump at one int.
        out = cr.log_percentile_normalize({"a": 5, "b": 5, "c": 5})
        # All three should receive the same rating (no spread among ties)
        assert len(set(out.values())) == 1

    def test_outlier_ranks_highest(self):
        # One clearly-higher value should get the top rating; the others lower.
        out = cr.log_percentile_normalize({"low": 1, "mid": 5, "high": 1000})
        assert out["high"] > out["mid"] > out["low"]

    def test_invert_flag_flips_ordering(self):
        # For "less is better" categories (crowd, safety), invert=True means a
        # lower raw value maps to a higher rating.
        values = {"quiet": 10, "busy": 10_000}
        normal = cr.log_percentile_normalize(values)
        inverted = cr.log_percentile_normalize(values, invert=True)
        assert normal["busy"] > normal["quiet"]
        assert inverted["quiet"] > inverted["busy"]

    def test_output_bounded_in_1_to_10(self):
        out = cr.log_percentile_normalize({f"s{i}": i for i in range(1, 50)})
        for v in out.values():
            assert 1 <= v <= 10


# -----------------------------------------------------------------------------
# apply_absolute_cap
# -----------------------------------------------------------------------------
class TestApplyAbsoluteCap:
    def test_cap_only_decreases_never_increases(self):
        caps = [(8, 100), (9, 400), (10, 1000)]
        # rating already below the cap → unchanged
        assert cr.apply_absolute_cap(5, raw_value=0, caps=caps) == 5
        # raw value far exceeds every threshold → cap allows up to 10
        assert cr.apply_absolute_cap(10, raw_value=10_000, caps=caps) == 10

    def test_cap_lowers_rating_when_raw_below_threshold(self):
        # To score >= 9 you need raw >= 400. With raw=50 you can't exceed 8.
        caps = [(8, 100), (9, 400), (10, 1000)]
        assert cr.apply_absolute_cap(10, raw_value=50, caps=caps) == 7

    def test_intermediate_threshold_boundary(self):
        # raw exactly at the 100 threshold → can score >= 8 but not >= 9
        caps = [(8, 100), (9, 400), (10, 1000)]
        assert cr.apply_absolute_cap(10, raw_value=100, caps=caps) == 8

    def test_uncapped_when_no_caps(self):
        assert cr.apply_absolute_cap(10, raw_value=0, caps=[]) == 10

    def test_rent_cap_uses_source_quality(self):
        # The rent cap encodes data source quality, not raw price:
        #   raw=2 (suumo)  → up to 10
        #   raw=1 (ward)   → up to 9
        #   raw=0 (regression) → up to 8 (implicit, since 0 < 1 fails the >=9 gate)
        rent_caps = cr.ABSOLUTE_CAPS["rent"]
        assert cr.apply_absolute_cap(10, raw_value=2, caps=rent_caps) == 10
        assert cr.apply_absolute_cap(10, raw_value=1, caps=rent_caps) == 9
        # raw=0 falls below the (9, 1) threshold → max_allowed = 8
        assert cr.apply_absolute_cap(10, raw_value=0, caps=rent_caps) == 8


# -----------------------------------------------------------------------------
# ABSOLUTE_CAPS surface — guards accidental key removal / reordering
# -----------------------------------------------------------------------------
class TestAbsoluteCapsShape:
    def test_expected_categories_present(self):
        expected = {"food", "nightlife", "transport", "green", "gym_sports", "vibe", "rent"}
        assert expected.issubset(set(cr.ABSOLUTE_CAPS.keys()))

    def test_each_cap_is_sorted_thresholds(self):
        for cat, caps in cr.ABSOLUTE_CAPS.items():
            # thresholds must be strictly increasing within a category
            thresholds = [t for _, t in caps]
            assert thresholds == sorted(thresholds), f"{cat} thresholds not sorted"
            ratings = [r for r, _ in caps]
            assert ratings == sorted(ratings), f"{cat} min-ratings not sorted"
