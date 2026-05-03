"""API-key authentication + per-key rate limiting for the HTTP transport.

Keys live in NocoDB table `api_keys` (see mcp/README.md → "API key schema"
for the column layout — must be created manually in the NocoDB UI).

Lifecycle:
  user submits the site form → row created with status=pending
  admin flips status → 'active' in NocoDB UI
  MCP server refreshes its key cache every REFRESH_SECONDS
  request arrives with `Authorization: Bearer <key>`
    → hash, look up, check status, deduct from token bucket → allow / 401 / 429

Security notes:
- Plaintext keys are NEVER stored. The site shows the key once at issue
  time and stores SHA-256 in NocoDB. The MCP only ever sees hashes.
- Cache refresh is tolerant of NocoDB outages — old cache survives.
- Rate limiter is in-memory and per-process, which is fine for our
  single-instance deploy. If we ever scale horizontally, move this to
  Redis or accept per-instance limits.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("city_rating_mcp.auth")

NOCODB_URL_ENV = "NOCODB_API_URL"
NOCODB_TOKEN_ENV = "NOCODB_API_TOKEN"
NOCODB_API_KEYS_TABLE_ENV = "NOCODB_API_KEYS_TABLE_ID"

# Default refresh: every 5 minutes. Lowered to 30s in dev via env.
REFRESH_SECONDS_ENV = "MCP_KEY_REFRESH_SECONDS"
DEFAULT_REFRESH_SECONDS = 300

# Single bucket per key, refilled at the per-minute rate.
DEFAULT_RATE_PER_MIN = 60


def hash_key(plaintext: str) -> str:
    """SHA-256 hex digest. Same function used by the site at issue time
    and the MCP at validation — keep them in sync if either changes."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


@dataclass
class KeyRecord:
    key_hash: str
    status: str  # 'active' | 'pending' | 'revoked'
    rate_limit_per_min: int = DEFAULT_RATE_PER_MIN
    email: str | None = None
    note: str | None = None


@dataclass
class _Bucket:
    """Token bucket; tokens refill at rate_per_min/60 per second."""
    tokens: float
    capacity: float
    rate_per_sec: float
    last: float = field(default_factory=time.monotonic)

    def take(self, n: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate_per_sec)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class KeyStore:
    """In-memory cache of active keys; refreshes from NocoDB on a timer.

    Auth flow lives in `validate(bearer)`, which returns
    (allowed, reason). Reason values:
      - "ok"           → forward the request
      - "missing"      → no Authorization header
      - "unknown"      → key hash not in cache
      - "pending"      → admin hasn't approved
      - "revoked"      → previously approved, now revoked
      - "rate_limited" → over per-minute budget
      - "unavailable"  → cache cold and NocoDB unreachable
    """

    def __init__(
        self,
        nocodb_url: str | None = None,
        nocodb_token: str | None = None,
        table_id: str | None = None,
        refresh_seconds: int | None = None,
    ):
        self.nocodb_url = (nocodb_url or os.getenv(NOCODB_URL_ENV, "")).rstrip("/")
        self.nocodb_token = nocodb_token or os.getenv(NOCODB_TOKEN_ENV, "")
        self.table_id = table_id or os.getenv(NOCODB_API_KEYS_TABLE_ENV, "")
        self.refresh_seconds = int(
            refresh_seconds
            or os.getenv(REFRESH_SECONDS_ENV, str(DEFAULT_REFRESH_SECONDS))
        )

        self._records: dict[str, KeyRecord] = {}
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.RLock()
        self._last_refresh: float = 0.0
        self._cache_ready = threading.Event()

    @property
    def configured(self) -> bool:
        return bool(self.nocodb_url and self.nocodb_token and self.table_id)

    def _fetch(self) -> list[dict[str, Any]] | None:
        """Pull all rows from the api_keys table. Returns None on error
        so the caller can keep the existing cache."""
        if not self.configured:
            return None
        import requests  # lazy: tests don't need this

        url = f"{self.nocodb_url}/api/v2/tables/{self.table_id}/records"
        out: list[dict[str, Any]] = []
        offset = 0
        page = 200
        try:
            while True:
                resp = requests.get(
                    url,
                    headers={"xc-token": self.nocodb_token},
                    params={"limit": page, "offset": offset},
                    timeout=10,
                )
                resp.raise_for_status()
                payload = resp.json()
                rows = payload.get("list", []) or []
                out.extend(rows)
                if len(rows) < page:
                    break
                offset += page
        except Exception as e:  # network / 5xx / parse errors
            LOG.warning("api_keys fetch failed (%s); keeping previous cache", e)
            return None
        return out

    def refresh(self) -> bool:
        """Pull fresh records and rebuild the cache. Returns True on success."""
        rows = self._fetch()
        if rows is None:
            return False

        new_records: dict[str, KeyRecord] = {}
        for row in rows:
            kh = (row.get("key_hash") or row.get("KeyHash") or "").strip().lower()
            if not kh:
                continue
            new_records[kh] = KeyRecord(
                key_hash=kh,
                status=(row.get("status") or "pending").strip().lower(),
                rate_limit_per_min=int(row.get("rate_limit_per_min") or DEFAULT_RATE_PER_MIN),
                email=row.get("email"),
                note=row.get("notes"),
            )

        with self._lock:
            self._records = new_records
            # Drop buckets for keys that are gone or no longer active.
            self._buckets = {
                k: b
                for k, b in self._buckets.items()
                if (rec := new_records.get(k)) is not None and rec.status == "active"
            }
            self._last_refresh = time.time()
            self._cache_ready.set()

        LOG.info("api_keys cache refreshed: %d total / %d active",
                 len(new_records),
                 sum(1 for r in new_records.values() if r.status == "active"))
        return True

    async def refresh_loop(self) -> None:
        """Async background task — lives for the server's lifetime."""
        # Initial blocking attempt so the first request finds a cache.
        self.refresh()
        while True:
            await asyncio.sleep(self.refresh_seconds)
            try:
                self.refresh()
            except Exception:
                LOG.exception("background refresh raised")

    def validate(self, bearer: str | None) -> tuple[bool, str]:
        if not bearer:
            return False, "missing"
        if not self.configured:
            # Auth disabled → allow everything. Caller controls this via
            # MCP_AUTH_REQUIRED in server.py; we never silently bypass.
            return True, "ok"
        if not self._cache_ready.is_set():
            return False, "unavailable"

        bearer = bearer.strip()
        # Tolerate "Bearer " prefix or raw key.
        if bearer.lower().startswith("bearer "):
            bearer = bearer[7:].strip()
        kh = hash_key(bearer)

        with self._lock:
            rec = self._records.get(kh)
            if rec is None:
                return False, "unknown"
            if rec.status != "active":
                return False, rec.status or "unknown"

            bucket = self._buckets.get(kh)
            if bucket is None:
                rate = max(1, rec.rate_limit_per_min)
                bucket = _Bucket(
                    tokens=float(rate),
                    capacity=float(rate),
                    rate_per_sec=rate / 60.0,
                )
                self._buckets[kh] = bucket
            elif bucket.capacity != rec.rate_limit_per_min:
                # Admin tweaked the limit — adopt new rate immediately.
                bucket.capacity = float(rec.rate_limit_per_min)
                bucket.rate_per_sec = rec.rate_limit_per_min / 60.0
                bucket.tokens = min(bucket.tokens, bucket.capacity)

            if not bucket.take(1.0):
                return False, "rate_limited"
        return True, "ok"
