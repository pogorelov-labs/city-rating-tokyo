"""
Cross-language parity / schema-drift guard.

Reads the ACTUAL generated TS constants from app/src/lib/schema/constants.ts
(the vendored copy that the frontend imports) and compares every value against
the Python city_rating_schema package. This catches real cross-language drift:
if someone edits constants.json and re-runs codegen, both sides update; if
someone hand-edits one side, this test fails.

Also verifies the load-bearing invariants:
  - RATING_KEYS order (positional URL decode depends on it)
  - DEFAULT_WEIGHTS values + sum (composite-score math)
  - RENT_FLOOR / RENT_CEILING (rent scoring)
  - ABSOLUTE_CAPS shape (pipeline tier gating)
"""
import importlib
import importlib.util
import json
import re
import sys
import types
import warnings
from pathlib import Path

# Make the schema package importable.
_THIS_DIR = Path(__file__).resolve().parent
_REPO = _THIS_DIR.parent
_SCHEMA_PY = _REPO / "packages" / "schema" / "python"
if str(_SCHEMA_PY) not in sys.path:
    sys.path.insert(0, str(_SCHEMA_PY))

# Suppress the "pydantic not installed" warning if it fires; we only need constants.
warnings.simplefilter("ignore")
from city_rating_schema.constants import (  # noqa: E402
    RATING_KEYS,
    DEFAULT_WEIGHTS,
    DEFAULT_FILTERS,
    RENT_FLOOR,
    RENT_CEILING,
    PIPELINE_ONLY,
)

# Stub `utils` so compute-ratings imports cleanly (see test_compute_ratings.py).
if "utils" not in sys.modules:
    utils_stub = types.ModuleType("utils")
    utils_stub.NocoDB = object
    utils_stub.load_stations = lambda: []
    sys.modules["utils"] = utils_stub

# compute-ratings.py has a hyphenated filename — load via importlib.
_spec = importlib.util.spec_from_file_location(
    "compute_ratings", _THIS_DIR / "compute-ratings.py"
)
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)

# --- Read the ACTUAL generated TS constants from disk ---
# This is what makes the test a real cross-language guard: we parse the values
# from the file the frontend actually imports, not a hardcoded mirror.
_TS_CONSTANTS = (_REPO / "app" / "src" / "lib" / "schema" / "constants.ts").read_text()


def _extract_ts_array(name: str) -> list[str]:
    """Extract a string array from the generated TS, preserving order."""
    m = re.search(rf'export const {name} = \[(.*?)\] as const', _TS_CONSTANTS, re.DOTALL)
    if not m:
        raise AssertionError(f"Could not find {name} in generated TS constants")
    return re.findall(r'"(\w+)"', m.group(1))


def _extract_ts_number(name: str) -> int:
    """Extract a numeric constant from the generated TS."""
    m = re.search(rf'export const {name} = (\d+)', _TS_CONSTANTS)
    if not m:
        raise AssertionError(f"Could not find {name} in generated TS constants")
    return int(m.group(1))


def _extract_ts_weights() -> dict[str, int]:
    """Extract DEFAULT_WEIGHTS from the generated TS, preserving key order."""
    m = re.search(r'export const DEFAULT_WEIGHTS[^{]*\{(.*?)\}', _TS_CONSTANTS, re.DOTALL)
    if not m:
        raise AssertionError("Could not find DEFAULT_WEIGHTS in generated TS")
    pairs = re.findall(r'"(\w+)":\s*(\d+)', m.group(1))
    return {k: int(v) for k, v in pairs}


TS_RATING_KEYS = _extract_ts_array("RATING_KEYS")
TS_RENT_FLOOR = _extract_ts_number("RENT_FLOOR")
TS_RENT_CEILING = _extract_ts_number("RENT_CEILING")
TS_DEFAULT_WEIGHTS = _extract_ts_weights()


class TestCrossLanguageRentConstants:
    """RENT_FLOOR and RENT_CEILING must be identical across TS and Python."""

    def test_rent_floor_matches(self):
        assert TS_RENT_FLOOR == RENT_FLOOR == 80000

    def test_rent_ceiling_matches(self):
        assert TS_RENT_CEILING == RENT_CEILING == 300000

    def test_compute_ratings_uses_same_floor(self):
        # compute-ratings.py imports from city_rating_schema, so this should
        # always pass post-consolidation — but it guards against someone
        # re-introducing a local override.
        assert cr.RENT_FLOOR == RENT_FLOOR


class TestCrossLanguageRatingKeysOrder:
    """RATING_KEYS order is the load-bearing positional URL invariant.

    If this fails, every shared ?w= URL on the internet silently repaints
    its weights. Never reorder, never sort.
    """

    def test_ts_rating_keys_match_python(self):
        assert TS_RATING_KEYS == list(RATING_KEYS)

    def test_first_key_is_transport(self):
        # Life-first order: transport at position 0.
        assert TS_RATING_KEYS[0] == "transport"
        assert RATING_KEYS[0] == "transport"

    def test_ten_keys(self):
        assert len(TS_RATING_KEYS) == 10
        assert len(RATING_KEYS) == 10

    def test_compute_ratings_categories_match(self):
        # compute-ratings.py uses list(RATING_KEYS) for its categories list.
        assert list(cr.RATING_KEYS) == list(RATING_KEYS)


class TestCrossLanguageDefaultWeights:
    """DEFAULT_WEIGHTS must match across TS and Python, in the same order."""

    def test_ts_weights_match_python(self):
        assert TS_DEFAULT_WEIGHTS == DEFAULT_WEIGHTS

    def test_weights_sum_to_100(self):
        # If the sum drifts off 100, the composite-score math silently rescales.
        assert sum(TS_DEFAULT_WEIGHTS.values()) == 100
        assert sum(DEFAULT_WEIGHTS.values()) == 100

    def test_weight_keys_match_rating_keys(self):
        assert list(TS_DEFAULT_WEIGHTS.keys()) == TS_RATING_KEYS
        assert list(DEFAULT_WEIGHTS.keys()) == list(RATING_KEYS)


class TestPipelineCapsShape:
    """Absolute caps gate rating tiers by raw thresholds. Shape must be stable."""

    def test_rent_cap_uses_source_quality(self):
        # rent cap encodes (min_rating, source_quality): 2=suumo, 1=ward, 0=regression.
        rent_caps = cr.ABSOLUTE_CAPS["rent"]
        assert (9, 1) in rent_caps
        assert (10, 2) in rent_caps

    def test_transport_cap_requires_5_lines_for_ten(self):
        transport_caps = cr.ABSOLUTE_CAPS["transport"]
        assert (10, 5) in transport_caps

    def test_schema_pipeline_only_matches_compute_ratings(self):
        # The caps in PIPELINE_ONLY (schema package) must match what
        # compute-ratings.py actually uses.
        schema_caps = PIPELINE_ONLY.absolute_caps
        for cat, caps in cr.ABSOLUTE_CAPS.items():
            assert cat in schema_caps, f"{cat} missing from schema PIPELINE_ONLY"
            assert [tuple(t) for t in schema_caps[cat]] == caps, (
                f"{cat} caps differ between schema and compute-ratings"
            )
