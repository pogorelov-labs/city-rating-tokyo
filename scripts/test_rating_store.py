import copy
import json

import pytest

import rating_store as rs


class Store:
    identity = "simulated://computed_ratings"

    def __init__(self, failures=None):
        self.rows = [{"Id": i + 1, "slug": f"s{i}", "food": 3} for i in range(205)]
        self.calls = 0
        self.failures = failures or {}
        self.schema_ok = True
        self.drop_field = False

    def preflight(self):
        if not self.schema_ok:
            raise ValueError("missing column")

    def read(self):
        return copy.deepcopy(self.rows)

    def patch(self, rows):
        self.calls += 1
        failure = self.failures.get(self.calls)
        # Failure can occur AFTER part of a batch was persisted.
        for row in rows[:3] if failure else rows:
            self.rows[row["Id"] - 1].update(row)
            if self.drop_field:
                self.rows[row["Id"] - 1].pop("source_dates", None)
        if failure:
            raise failure


def candidate(store):
    return [{"slug": r["slug"], "food": 8, "source_dates": "{}"} for r in store.rows]


def test_success_keeps_ids_and_verifies(tmp_path):
    store = Store()
    path = rs.replace_ratings(store, candidate(store), tmp_path)
    assert json.loads(path.read_text())["phase"] == "committed"
    assert all(r["food"] == 8 for r in store.rows)
    assert [r["Id"] for r in store.rows] == list(range(1, 206))
    assert path.stat().st_mode & 0o777 == 0o600
    rs.assert_recovered(tmp_path)


@pytest.mark.parametrize("batch", [1, 2, 3])
def test_partial_failure_restores_all_rows(tmp_path, batch):
    store = Store({batch: RuntimeError("injected")})
    with pytest.raises(RuntimeError, match="restored and verified"):
        rs.replace_ratings(store, candidate(store), tmp_path)
    assert all(r["food"] == 3 and r.get("source_dates") is None for r in store.rows)
    rs.assert_recovered(tmp_path)


@pytest.mark.parametrize("failure", [KeyboardInterrupt(), rs.UnknownWriteOutcome()])
def test_crash_or_unknown_outcome_blocks_export_until_explicit_recovery(tmp_path, failure):
    store = Store({2: failure})
    with pytest.raises((KeyboardInterrupt, RuntimeError)):
        rs.replace_ratings(store, candidate(store), tmp_path)
    with pytest.raises(RuntimeError, match="Unresolved"):
        rs.assert_recovered(tmp_path)
    path = next(tmp_path.glob("*.json"))
    store.failures = {}
    rs.recover(store, path)
    assert all(r["food"] == 3 for r in store.rows)
    rs.assert_recovered(tmp_path)
    with pytest.raises(ValueError, match="finalized"):
        rs.recover(store, path)


def test_failed_rollback_remains_recoverable(tmp_path):
    store = Store({2: RuntimeError(), 3: RuntimeError()})
    with pytest.raises(RuntimeError, match="recovery failed"):
        rs.replace_ratings(store, candidate(store), tmp_path)
    path = next(tmp_path.glob("*.json"))
    store.failures = {}
    rs.recover(store, path)
    assert all(r["food"] == 3 for r in store.rows)


def test_no_mutation_without_schema_or_durable_journal(tmp_path, monkeypatch):
    store = Store()
    store.schema_ok = False
    with pytest.raises(ValueError, match="missing column"):
        rs.replace_ratings(store, candidate(store), tmp_path)
    assert store.calls == 0
    store.schema_ok = True
    def broken(*args):
        raise OSError("disk full")
    monkeypatch.setattr(rs.os, "fsync", broken)
    with pytest.raises(OSError):
        rs.replace_ratings(store, candidate(store), tmp_path)
    assert store.calls == 0


def test_remote_dropped_field_fails_readback_and_restores(tmp_path):
    store = Store()
    store.drop_field = True
    with pytest.raises(RuntimeError, match="restored and verified"):
        rs.replace_ratings(store, candidate(store), tmp_path)
    assert all(r["food"] == 3 for r in store.rows)


def test_membership_and_duplicate_slug_refused(tmp_path):
    store = Store()
    for rows in (candidate(store)[:-1], candidate(store) + candidate(store)[:1]):
        with pytest.raises(ValueError):
            rs.replace_ratings(store, rows, tmp_path)
    assert store.calls == 0


def test_local_concurrent_writer_refused(tmp_path):
    store = Store()
    with rs.table_lock(tmp_path), pytest.raises(RuntimeError, match="Another local"):
        rs.replace_ratings(store, candidate(store), tmp_path)
    assert store.calls == 0


def test_recovery_rejects_wrong_target_and_modified_backup(tmp_path):
    store = Store({1: KeyboardInterrupt()})
    with pytest.raises(KeyboardInterrupt):
        rs.replace_ratings(store, candidate(store), tmp_path)
    path = next(tmp_path.glob("*.json"))
    store.identity = "different://table"
    with pytest.raises(ValueError, match="backend"):
        rs.recover(store, path)
    store.identity = Store.identity
    journal = json.loads(path.read_text())
    journal["before"][0]["food"] = 10
    path.write_text(json.dumps(journal))
    with pytest.raises(ValueError, match="checksum"):
        rs.recover(store, path)


@pytest.mark.parametrize("uidt", [None, "SingleLineText", "Number"])
def test_missing_or_wrong_column_type_refused(uidt):
    columns = [{"title": "data_date", "uidt": "SingleLineText"}]
    if uidt:
        columns.append({"title": "source_dates", "uidt": uidt})
    with pytest.raises(ValueError, match="LongText"):
        rs.validate_schema({"columns": columns})


def test_schema_exact_additive_contract():
    rs.validate_schema({"columns": [{"title": "data_date", "uidt": "SingleLineText"},
                                     {"title": "source_dates", "uidt": "LongText"}]})


@pytest.mark.parametrize("status", [408, 500, 502, 503, 504])
def test_http_timeout_or_server_failure_is_unknown_and_does_not_rollback(tmp_path, monkeypatch, status):
    import requests
    store = Store()
    db = type("DB", (), {"base_url": "https://fixture.test/api/v2/tables/ratings",
                          "headers": {}, "get_all_records": store.read})()
    adapter = rs.NocoRatingStore(db)
    monkeypatch.setattr(adapter, "preflight", lambda: None)
    calls = []
    def patch(*args, **kwargs):
        calls.append(kwargs["json"])
        # The gateway responds while the upstream PATCH is still queued.
        return type("Response", (), {"ok": False, "status_code": status})()
    monkeypatch.setattr(requests, "patch", patch)
    with pytest.raises(RuntimeError, match="outcome unknown"):
        rs.replace_ratings(adapter, candidate(store), tmp_path)
    assert len(calls) == 1  # No racing compensation request.
    assert all(row["food"] == 3 for row in store.rows)
    store.patch(calls[0])  # Delayed upstream write lands AFTER the client failed.
    assert any(row["food"] == 8 for row in store.rows)
    with pytest.raises(RuntimeError, match="Unresolved"):
        rs.assert_recovered(tmp_path)
    assert json.loads(next(tmp_path.glob("*.json")).read_text())["phase"] == "prepared"
