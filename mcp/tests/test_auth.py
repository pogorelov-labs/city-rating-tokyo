"""KeyStore unit tests — the first MCP test suite (CRTKY-155/161).

Everything here is in-memory: no NocoDB, no HTTP, no fastembed. The tests
that touch network code monkeypatch `_fetch` or `requests.get`.

Run: pytest mcp/tests/ (from the mcp/ dir or with PYTHONPATH=src).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from city_rating_mcp.auth import (  # noqa: E402
    DEFAULT_RATE_PER_MIN,
    KeyRecord,
    KeyStore,
    _Bucket,
    _coerce_rate,
    hash_key,
)


def make_store(**env) -> KeyStore:
    """Configured store with an empty warm cache."""
    store = KeyStore(
        nocodb_url=env.get("url", "https://nocodb.example"),
        nocodb_token=env.get("token", "t"),
        table_id=env.get("table", "tbl"),
        refresh_seconds=1,
    )
    store._cache_ready.set()
    return store


def seed(store: KeyStore, key: str = "k1", status: str = "active", rate: int = 60) -> str:
    kh = hash_key(key)
    store._records[kh] = KeyRecord(key_hash=kh, status=status, rate_limit_per_min=rate)
    return kh


# --- fail-open regression (audit C1) --------------------------------------


def test_unconfigured_store_rejects_any_bearer():
    """MCP_AUTH_REQUIRED=true + missing NocoDB env must NOT validate anyone.

    This is the regression test for the fail-open bug: validate() used to
    return (True, "ok") for any bearer on an unconfigured store, while the
    startup log claimed every request would be rejected.
    """
    store = KeyStore(nocodb_url="", nocodb_token="", table_id="")
    assert store.configured is False
    assert store.validate("Bearer anything") == (False, "unavailable")


def test_unconfigured_store_still_requires_a_header():
    store = KeyStore(nocodb_url="", nocodb_token="", table_id="")
    assert store.validate(None) == (False, "missing")


def test_configured_but_cold_cache_is_unavailable():
    store = KeyStore(nocodb_url="u", nocodb_token="t", table_id="tbl")
    assert store._cache_ready.is_set() is False
    assert store.validate("Bearer x") == (False, "unavailable")


# --- validate matrix -------------------------------------------------------


def test_validate_active_key_ok():
    store = make_store()
    seed(store, "k1", "active")
    assert store.validate(None) == (False, "missing")
    assert store.validate("Bearer k1") == (True, "ok")


def test_validate_raw_bearer_without_prefix():
    store = make_store()
    seed(store, "k1", "active")
    assert store.validate("k1") == (True, "ok")


def test_validate_unknown_key():
    store = make_store()
    seed(store, "k1", "active")
    assert store.validate("Bearer nope") == (False, "unknown")


def test_validate_pending_and_revoked():
    store = make_store()
    seed(store, "p", "pending")
    seed(store, "r", "revoked")
    assert store.validate("Bearer p") == (False, "pending")
    assert store.validate("Bearer r") == (False, "revoked")


def test_validate_rate_limited_when_bucket_empty():
    store = make_store()
    kh = seed(store, "k", "active", rate=60)
    store._buckets[kh] = _Bucket(tokens=0.0, capacity=60.0, rate_per_sec=1.0)
    assert store.validate("Bearer k") == (False, "rate_limited")


def test_validate_adopts_new_rate_mid_flight():
    """Admin raises the limit → the existing bucket follows on next use."""
    store = make_store()
    kh = seed(store, "k", "active", rate=60)
    store._buckets[kh] = _Bucket(tokens=30.0, capacity=60.0, rate_per_sec=1.0)
    seed(store, "k", "active", rate=120)  # re-seed with a new rate
    assert store.validate("Bearer k") == (True, "ok")
    assert store._buckets[kh].capacity == 120.0
    assert store._buckets[kh].tokens <= 120.0


# --- refresh resilience (audit C3) -----------------------------------------


def test_coerce_rate_malformed_values():
    assert _coerce_rate(None) == DEFAULT_RATE_PER_MIN
    assert _coerce_rate("") == DEFAULT_RATE_PER_MIN
    assert _coerce_rate("abc") == DEFAULT_RATE_PER_MIN
    assert _coerce_rate("30") == 30
    assert _coerce_rate(0) == 1  # clamped to >= 1
    assert _coerce_rate(-5) == 1


def test_refresh_survives_malformed_row():
    """A junk rate_limit_per_min must not raise out of refresh()."""
    store = make_store()
    store._fetch = lambda: [  # type: ignore[method-assign]
        {"key_hash": hash_key("k"), "status": "ACTIVE", "rate_limit_per_min": "junk"},
    ]
    assert store.refresh() is True
    rec = store._records[hash_key("k")]
    assert rec.status == "active"
    assert rec.rate_limit_per_min == DEFAULT_RATE_PER_MIN


def test_refresh_normalizes_hash_case_and_default_status():
    store = make_store()
    store._fetch = lambda: [  # type: ignore[method-assign]
        {"key_hash": hash_key("k").upper(), "rate_limit_per_min": None},
    ]
    store.refresh()
    rec = store._records[hash_key("k")]
    assert rec is not None
    assert rec.status == "pending"  # default when the column is empty


def test_refresh_failure_keeps_previous_cache():
    store = make_store()
    seed(store, "old", "active")
    store._fetch = lambda: None  # type: ignore[method-assign]
    assert store.refresh() is False
    assert store.validate("Bearer old") == (True, "ok")


def test_refresh_drops_buckets_of_revoked_keys():
    store = make_store()
    kh = seed(store, "k", "active")
    store._buckets[kh] = _Bucket(tokens=60.0, capacity=60.0, rate_per_sec=1.0)
    store._fetch = lambda: [  # type: ignore[method-assign]
        {"key_hash": kh, "status": "revoked"},
    ]
    store.refresh()
    assert kh not in store._buckets
    assert store.validate("Bearer k") == (False, "revoked")


def test_refresh_loop_initial_failure_does_not_kill_task(monkeypatch):
    """Audit C3: the initial refresh used to sit outside the try/except —
    one raise and the loop died, leaving the cache cold forever (503×∞)."""
    import asyncio

    store = make_store()
    # NB: refresh_seconds=0 through the constructor falls back to the default
    # (falsy `or`), so set the attribute directly for a fast timer.
    store.refresh_seconds = 0.01
    calls = {"n": 0}

    def boom_then_ok():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("malformed row exploded")
        seed(store, "k", "active")
        store._fetch = lambda: []  # type: ignore[method-assign]
        return True

    monkeypatch.setattr(store, "refresh", boom_then_ok)

    async def scenario():
        task = asyncio.create_task(store.refresh_loop())
        await asyncio.sleep(0.2)
        assert not task.done(), "refresh_loop must survive an initial refresh failure"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert calls["n"] >= 2  # the timer retry ran after the initial failure


# --- bucket math -----------------------------------------------------------


def test_bucket_refill_over_time(monkeypatch):
    from city_rating_mcp import auth as auth_module

    fake_now = [1000.0]
    monkeypatch.setattr(auth_module.time, "monotonic", lambda: fake_now[0])
    b = _Bucket(tokens=0.0, capacity=60.0, rate_per_sec=1.0, last=1000.0)
    assert b.take() is False
    fake_now[0] += 10.0  # 10 seconds × 1 token/s
    assert b.take() is True
    assert b.tokens == pytest.approx(9.0)


def test_bucket_exhausts_then_refills_and_adopts_lower_rate(monkeypatch):
    from city_rating_mcp import auth as auth_module

    now = [1000.0]
    monkeypatch.setattr(auth_module.time, "monotonic", lambda: now[0])
    store = make_store()
    key_hash = seed(store, "k", rate=2)
    store._buckets[key_hash] = _Bucket(tokens=2, capacity=2, rate_per_sec=2 / 60, last=now[0])
    assert store.validate("Bearer k") == (True, "ok")
    assert store.validate("Bearer k") == (True, "ok")
    assert store.validate("Bearer k") == (False, "rate_limited")
    now[0] += 30
    assert store.validate("Bearer k") == (True, "ok")
    seed(store, "k", rate=1)
    now[0] += 60
    assert store.validate("Bearer k") == (True, "ok")
    assert store._buckets[key_hash].capacity == 1
    assert store.validate("Bearer k") == (False, "rate_limited")
