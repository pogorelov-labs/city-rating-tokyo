"""Recoverable (NOT atomic) updates to the fixed computed_ratings population.

One writer/export host and a maintenance window are required. The filesystem
lock is local; it is not a distributed NocoDB transaction or lease.
"""
import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

DEFAULT_RECOVERY_DIR = Path.home() / ".local/state/city-rating/computed-ratings"
TERMINAL = {"committed", "restored"}


class UnknownWriteOutcome(RuntimeError):
    """A timed-out/disconnected request may still be executing on the server."""


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def durable_json(path, data):
    """Publish only after data fsync, then fsync the containing directory."""
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


@contextmanager
def table_lock(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "writer.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another local ratings writer/export is running") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def assert_recovered(directory):
    for path in sorted(Path(directory).glob("*.json")):
        journal = json.loads(path.read_text())
        if journal.get("phase") not in TERMINAL:
            raise RuntimeError(f"Unresolved ratings journal: {path}; recover before compute/export")


def by_slug(rows):
    result = {}
    for row in rows:
        slug = row.get("slug")
        if not slug or slug in result:
            raise ValueError("Missing/duplicate computed slug; manual repair required")
        result[slug] = row
    return result


def projection(rows, fields):
    return sorted(({field: row.get(field) for field in fields} for row in rows), key=lambda r: r["slug"])


def verify(store, expected, fields):
    actual = store.read()
    by_slug(actual)
    if projection(actual, fields) != projection(expected, fields):
        raise RuntimeError("Computed-ratings readback mismatch; do not export")


def patch_all(store, rows):
    for start in range(0, len(rows), 100):
        store.patch(rows[start:start + 100])


def replace_ratings(store, records, directory=DEFAULT_RECOVERY_DIR, validate=None):
    """Persist preimages before PATCH; restore on failure; leave journal on crash.

    Only the same unique slug set and existing IDs are supported. No DELETE or
    INSERT is used, including recovery. Bootstrap/membership changes need a
    separate migration. Any uncertain or failed write aborts export even when
    restoration succeeds.
    """
    directory = Path(directory)
    with table_lock(directory):
        assert_recovered(directory)
        store.preflight()
        previous = store.read()
        before, after = by_slug(previous), by_slug(records)
        if not before or before.keys() != after.keys():
            raise ValueError("Replacement requires identical nonempty slug sets; no rows written")
        ids = [r.get("Id") for r in previous]
        if any(i is None for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("Missing/duplicate row IDs; no rows written")
        if validate:
            validate(records, previous)
        fields = sorted(set().union(*(r.keys() for r in records)) | {"Id"})
        target = [{**after[slug], "Id": before[slug]["Id"]} for slug in sorted(after)]
        backup = projection(previous, fields)
        journal = {"version": 1, "target": store.identity, "phase": "prepared",
                   "fields": fields, "before": backup, "after": target,
                   "before_sha256": fingerprint(backup), "after_sha256": fingerprint(target)}
        path = directory / f"{uuid4().hex}.json"
        durable_json(path, journal)  # A failed fsync cannot be followed by a remote mutation.
        try:
            patch_all(store, target)
            verify(store, target, fields)
        except UnknownWriteOutcome:
            raise RuntimeError(f"Write outcome unknown; stop writers, settle requests, then recover {path}") from None
        except Exception:
            # PATCH is idempotent by Id. A failed rollback remains explicitly pending.
            try:
                patch_all(store, backup)
                verify(store, backup, fields)
            except Exception:
                raise RuntimeError(f"Update and recovery failed; stop exports and recover {path}") from None
            journal["phase"] = "restored"
            durable_json(path, journal)
            raise RuntimeError(f"Update failed; previous ratings restored and verified ({path})") from None
        journal["phase"] = "committed"
        durable_json(path, journal)
        return path


def recover(store, path):
    """Explicit operator restore after stopping all writers and settling requests."""
    path = Path(path).resolve()
    with table_lock(path.parent):
        journal = json.loads(path.read_text())
        if journal.get("version") != 1 or journal.get("target") != store.identity:
            raise ValueError("Journal version/backend does not match; refusing recovery")
        if journal.get("phase") in TERMINAL:
            raise ValueError("Journal already finalized; refusing to overwrite a later generation")
        for key in ("before", "after"):
            if fingerprint(journal[key]) != journal[key + "_sha256"]:
                raise ValueError("Journal checksum mismatch; refusing recovery")
        current = by_slug(store.read())
        before = by_slug(journal["before"])
        if current.keys() != before.keys() or any(current[s].get("Id") != before[s]["Id"] for s in before):
            raise ValueError("Remote membership/IDs changed; manual reconciliation required")
        store.preflight()
        patch_all(store, journal["before"])
        verify(store, journal["before"], journal["fields"])
        journal["phase"] = "restored"
        durable_json(path, journal)


class NocoRatingStore:
    def __init__(self, db):
        self.db = db
        self.identity = db.base_url

    def read(self):
        return self.db.get_all_records()

    def preflight(self):
        import requests
        root = self.db.base_url.split("/api/v2/tables/")[0]
        try:
            response = requests.get(f"{root}/api/v2/meta/tables/{self.db.table_id}",
                                    headers=self.db.headers, timeout=30)
            response.raise_for_status()
            metadata = response.json()
        except (requests.RequestException, ValueError):
            raise RuntimeError("Cannot verify ratings schema; table-metadata read permission required; no writes") from None
        validate_schema(metadata)

    def patch(self, rows):
        import requests
        try:
            response = requests.patch(f"{self.db.base_url}/records", headers=self.db.headers,
                                      json=rows, timeout=60)
        except requests.RequestException:
            # Do not expose tokens, response bodies or authenticated request URLs.
            raise UnknownWriteOutcome("NocoDB PATCH outcome unknown") from None
        if not response.ok:
            raise RuntimeError(f"NocoDB PATCH rejected (HTTP {response.status_code})")


def validate_schema(metadata):
    columns = metadata.get("columns", []) if isinstance(metadata, dict) else []
    matching = [c for c in columns if c.get("title") == "source_dates"]
    if len(matching) != 1 or matching[0].get("uidt") != "LongText":
        raise ValueError("computed_ratings.source_dates must exist with type LongText; no writes")
    legacy = [c for c in columns if c.get("title") == "data_date"]
    if len(legacy) != 1 or legacy[0].get("uidt") != "SingleLineText":
        raise ValueError("computed_ratings.data_date must remain SingleLineText; no writes")
