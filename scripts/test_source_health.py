import copy
import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from source_health import (HP_FIELDS, MIN_COVERAGE, check_source_mix, check_sources,
                           conservative_month, decode_dates, encode_dates, station_dates)

ROOT = Path(__file__).resolve().parent.parent


def healthy():
    return {name: {"a": {"scraped_at": "2026-10-01", "food_count": 3,
                          **{field: 2 for field in HP_FIELDS}}} for name in MIN_COVERAGE}


def test_healthy_and_observed_zero_are_valid():
    tables = healthy()
    tables["hotpepper"]["a"]["midnight_count"] = 0
    assert check_sources(["a"], tables, 90, date(2026, 10, 15))["hotpepper"]["stale"] == 0


@pytest.mark.parametrize("value", [None, "", "garbage", "2026-02-30", "2026-01-01", "2027-01-01"])
def test_invalid_stale_future_dates_fail(value):
    tables = healthy()
    tables["hotpepper"]["a"]["scraped_at"] = value
    with pytest.raises(ValueError, match="Source canary failed"):
        check_sources(["a"], tables, 90, date(2026, 10, 15))


@pytest.mark.parametrize("field", HP_FIELDS)
@pytest.mark.parametrize("value", [None, -1, True, 1.5, "5"])
def test_incomplete_counts_fail(field, value):
    tables = healthy()
    tables["hotpepper"]["a"][field] = value
    with pytest.raises(ValueError, match="incomplete count"):
        check_sources(["a"], tables, 90, date(2026, 10, 15))


def test_missing_table_and_all_zero_source_fail():
    tables = healthy()
    tables["osm_pois"] = {}
    tables["hotpepper"]["a"]["total_count"] = 0
    with pytest.raises(ValueError, match="incomplete coverage"):
        check_sources(["a"], tables, 90, date(2026, 10, 15))


def test_source_dates_are_row_specific_and_unknown_is_not_today():
    tables = healthy()
    tables["hotpepper"]["a"]["scraped_at"] = "2026-04-23T12:30:00Z"
    dates = station_dates("a", tables)
    assert dates["hotpepper"] == "2026-04-23"
    assert conservative_month(dates) == "2026-04"
    assert decode_dates(encode_dates(dates)) == dates
    dates["hotpepper"] = None
    assert conservative_month(dates) == "unknown"
    assert all(v is None for v in station_dates("missing", tables).values())


@pytest.mark.parametrize("value", ["{bad", '[]', '{"hotpepper":"2026-04-01"}', '{"v":2}'])
def test_malformed_metadata_rejected(value):
    with pytest.raises((ValueError, TypeError)):
        decode_dates(value)


def test_legacy_metadata_retains_actual_month():
    assert decode_dates(None) == {}
    assert conservative_month({}, "2026-04") == "2026-04"
    assert conservative_month({}, None) == "unknown"


def test_source_mix_loss_fails_without_changing_scoring():
    previous = [{"sources": '{"food":["hotpepper","osm"]}'} for _ in range(100)]
    check_source_mix(previous[:95], previous)
    with pytest.raises(ValueError, match="hotpepper: 100 -> 94"):
        check_source_mix(previous[:94], previous)


@pytest.mark.parametrize("corruption", ["stale", "incomplete"])
def test_real_refresh_shell_canary_aborts_before_compute(tmp_path, corruption):
    # The real shell's terminal fixture mode runs without tokens, git or NocoDB.
    tables = copy.deepcopy(healthy())
    if corruption == "stale":
        tables["hotpepper"]["a"]["scraped_at"] = "2026-01-01"
    else:
        del tables["hotpepper"]["a"]["midnight_count"]
    fixture = tmp_path / "sources.json"
    fixture.write_text(json.dumps({"today": "2026-10-15", "slugs": ["a"], "tables": tables}))
    result = subprocess.run(["bash", str(ROOT / "scripts/refresh-ratings.sh"),
                             f"--check-sources-fixture={fixture}", "--max-source-age-days=90"],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "Source canary failed" in result.stderr
    assert "Running compute" not in result.stdout
    assert "Committing" not in result.stdout
