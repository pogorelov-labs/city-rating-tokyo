"""FastMCP server entry point.

Exposes the city-rating Tokyo dataset over MCP. Three transports:
- `stdio` (default) for local Claude Desktop / Claude Code testing
- `http` for the Coolify deployment behind a Caddy/Nginx TLS terminator
- `sse` if a client requires the legacy Server-Sent Events transport

The datamart is loaded once at startup. Tools are pure functions over
the in-memory store — no per-request I/O, response budget < 10 ms for
the light tools at 1493 stations.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from .auth import KeyStore
from .data import Datamart
from .embeddings import EmbeddingStore
from .scoring import RATING_KEYS
from .tools.methodology import get_methodology as _methodology
from .tools.pois import CATEGORY_FIELDS
from .tools.pois import list_pois as _list_pois
from .tools.search import search_stations as _search
from .tools.semantic import (
    find_similar as _find_similar,
)
from .tools.semantic import (
    recommend as _recommend,
)
from .tools.semantic import (
    semantic_search as _semantic_search,
)
from .tools.station import compare_stations as _compare
from .tools.station import get_station as _get

LOG = logging.getLogger("city_rating_mcp")

mcp = FastMCP(
    name="city-rating-tokyo",
    instructions=(
        "Greater Tokyo neighbourhood ratings across 1493 train stations. "
        "Use search_stations for ranked recommendations under user weights "
        "and dealbreakers, get_station for a full profile, compare_stations "
        "side-by-side, list_pois for raw signal counts, and get_methodology "
        "before quoting how a rating was computed. All locale params accept "
        "'en' (default), 'ja', or 'ru'."
    ),
)


# Lazy stores — load on first tool call so `--help` and HTTP startup
# don't pay the file-read cost when artifacts are missing. EmbeddingStore
# also defers fastembed model load to the first query (~3 s otherwise).
_DM: Datamart | None = None
_ES: EmbeddingStore | None = None


def _datamart() -> Datamart:
    global _DM
    if _DM is None:
        _DM = Datamart.load()
        LOG.info("datamart loaded: %d stations", len(_DM))
    return _DM


def _embeddings() -> EmbeddingStore:
    global _ES
    if _ES is None:
        _ES = EmbeddingStore.load()
    return _ES


VALID_LOCALES = {"en", "ja", "ru"}
VALID_FIELDS = {"atmosphere", "landmarks", "food", "nightlife"}


def _check_locale(locale: str) -> str:
    if locale not in VALID_LOCALES:
        raise ValueError(f"locale must be one of {sorted(VALID_LOCALES)}, got '{locale}'")
    return locale


@mcp.tool
def search_stations(
    weights: dict[str, float] | None = None,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_commute: float | None = None,
    max_commute: float | None = None,
    category_mins: dict[str, float] | None = None,
    has_live_camera: bool = False,
    hide_flood_risk: bool = False,
    hide_high_seismic: bool = False,
    locale: str = "en",
    limit: int = 20,
) -> dict[str, Any]:
    """Top-N Tokyo stations by weighted composite score under hard filters.

    Args:
        weights: Per-category weight overrides (0–100, any key from
            transport/rent/daily_essentials/safety/food/green/gym_sports/
            vibe/nightlife/crowd). Missing keys use the site defaults.
            A weight of 0 drops the dimension from the score entirely.
        min_rent, max_rent: 1K-1LDK monthly rent in JPY. Site default
            range is 80000–300000.
        min_commute, max_commute: Minutes to the nearest of Shibuya,
            Shinjuku, Tokyo, Ikebukuro, Shinagawa.
        category_mins: Per-rating floor, e.g. {"safety": 7}.
        has_live_camera: Require at least one YouTube live cam ≤300m.
        hide_flood_risk: Drop stations under 5 m elevation.
        hide_high_seismic: Drop stations in J-SHIS very_high tier.
        locale: 'en' | 'ja' | 'ru'. Affects display name only.
        limit: 1–200, default 20.
    """
    return _search(
        _datamart(),
        weights=weights,
        min_rent=min_rent,
        max_rent=max_rent,
        min_commute=min_commute,
        max_commute=max_commute,
        category_mins=category_mins,
        has_live_camera=has_live_camera,
        hide_flood_risk=hide_flood_risk,
        hide_high_seismic=hide_high_seismic,
        locale=_check_locale(locale),
        limit=limit,
    )


@mcp.tool
def get_station(slug: str, locale: str = "en") -> dict[str, Any]:
    """Full profile for one station: ratings, confidence, sources, rent,
    transit, last train, environment, signals, ward, lines, livecams,
    multilingual description.
    """
    return _get(_datamart(), slug=slug, locale=_check_locale(locale))


@mcp.tool
def compare_stations(slugs: list[str], locale: str = "en") -> dict[str, Any]:
    """Side-by-side full profiles for 2–5 stations."""
    return _compare(_datamart(), slugs=slugs, locale=_check_locale(locale))


@mcp.tool
def list_pois(slug: str, category: str | None = None) -> dict[str, Any]:
    """Per-station signal counts.

    Args:
        slug: Station slug (e.g. 'shibuya', 'kichijoji').
        category: One of food/nightlife/green/vibe/gym/essentials,
            or None for all six.
    """
    if category is not None and category not in CATEGORY_FIELDS:
        raise ValueError(
            f"category must be one of {sorted(CATEGORY_FIELDS)} or null"
        )
    return _list_pois(_datamart(), slug=slug, category=category)


@mcp.tool
def get_methodology() -> dict[str, Any]:
    """Rating formulas, confidence levels, source caveats. Quote this when
    explaining how a number was derived — don't guess."""
    return _methodology()


@mcp.custom_route("/mcp/healthz", methods=["GET"])
async def _healthz(_request):
    """Coolify healthcheck. No auth, no work — keeps the server's liveness
    signal independent of NocoDB / fastembed model state.

    Path is `/mcp/healthz` (not `/healthz`) so the entire MCP service can
    be exposed under a single Traefik `PathPrefix(/mcp)` rule, sharing
    `city-rating.pogorelov.dev` with the Next.js frontend."""
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("ok")


@mcp.tool
def list_categories() -> dict[str, Any]:
    """Static reference: the 10 rating dimensions the dataset supports."""
    return {
        "rating_keys": list(RATING_KEYS),
        "label_en": {
            "transport": "Transport",
            "rent": "Affordability",
            "daily_essentials": "Daily Essentials",
            "safety": "Safety",
            "food": "Food & Dining",
            "green": "Parks & Green",
            "gym_sports": "Gym & Sports",
            "vibe": "Vibe & Atmosphere",
            "nightlife": "Nightlife",
            "crowd": "Quietness",
        },
        "poi_categories": list(CATEGORY_FIELDS.keys()),
        "locales": sorted(VALID_LOCALES),
        "description_fields": sorted(VALID_FIELDS),
    }


@mcp.tool
def semantic_search(
    query: str,
    locale: str = "en",
    field: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Find stations whose descriptions best match a free-form query.

    Args:
        query: Natural-language phrase. Embedded with multilingual-e5-base.
            Best when in the same locale as `locale`, but cross-lingual
            queries also work (the model is multilingual).
        locale: 'en' | 'ja' | 'ru'. Selects which description set to search.
        field: None to search the per-station aggregate (one vector per
            station — best for general queries). Or one of
            'atmosphere' | 'landmarks' | 'food' | 'nightlife' to constrain.
        limit: 1–50, default 10.
    """
    if field is not None and field not in VALID_FIELDS:
        raise ValueError(f"field must be null or one of {sorted(VALID_FIELDS)}")
    return _semantic_search(
        _datamart(), _embeddings(),
        query=query, locale=_check_locale(locale), field=field, limit=limit,
    )


@mcp.tool
def find_similar(slug: str, locale: str = "en", limit: int = 10) -> dict[str, Any]:
    """Stations most semantically similar to `slug` (cosine on description vectors).

    Useful for "I like Kichijoji, what else feels like that?" The seed
    station is excluded from results.
    """
    return _find_similar(
        _datamart(), _embeddings(),
        slug=slug, locale=_check_locale(locale), limit=limit,
    )


@mcp.tool
def recommend(
    query: str,
    weights: dict[str, float] | None = None,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_commute: float | None = None,
    max_commute: float | None = None,
    category_mins: dict[str, float] | None = None,
    has_live_camera: bool = False,
    hide_flood_risk: bool = False,
    hide_high_seismic: bool = False,
    locale: str = "en",
    hybrid_alpha: float = 0.5,
    limit: int = 10,
) -> dict[str, Any]:
    """Hybrid recommender: semantic intent + structured weights + hard filters.

    The right tool when a user describes what they want in words AND
    has dealbreakers. Pipeline: semantic top-60 → drop anything that
    fails the filters → re-rank by `hybrid_alpha * cosine + (1-α) * composite/10`.

    Args:
        query: What the user wants in their own words.
        weights, min/max rent/commute, category_mins, has_live_camera,
            hide_flood_risk, hide_high_seismic: Same as search_stations.
        hybrid_alpha: 0=pure structured (matches search_stations),
            1=pure semantic, default 0.5.
        locale: 'en' | 'ja' | 'ru'.
        limit: 1–50, default 10.
    """
    return _recommend(
        _datamart(), _embeddings(),
        query=query, weights=weights,
        min_rent=min_rent, max_rent=max_rent,
        min_commute=min_commute, max_commute=max_commute,
        category_mins=category_mins,
        has_live_camera=has_live_camera,
        hide_flood_risk=hide_flood_risk,
        hide_high_seismic=hide_high_seismic,
        locale=_check_locale(locale),
        hybrid_alpha=hybrid_alpha,
        limit=limit,
    )


def _auth_middleware_factory(store: KeyStore):
    """Build a Starlette BaseHTTPMiddleware that gates every HTTP request
    on a valid `Authorization: Bearer <key>` matching an *active* row in
    the NocoDB api_keys table. Health probes on `/healthz` skip auth."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse, Response

    HTTP_STATUS = {
        "missing": (401, "missing or malformed Authorization header"),
        "unknown": (401, "unknown API key"),
        "pending": (403, "API key is pending admin approval"),
        "revoked": (403, "API key has been revoked"),
        "rate_limited": (429, "rate limit exceeded — slow down"),
        "unavailable": (503, "auth backend warming up; try again shortly"),
    }

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # Match both legacy `/healthz` and the path-prefixed `/mcp/healthz`.
            # Coolify is wired to the latter; the former survives for direct
            # container probes during dev.
            if request.url.path in ("/healthz", "/mcp/healthz"):
                return Response(b"ok", media_type="text/plain")
            auth = request.headers.get("authorization")
            ok, reason = store.validate(auth)
            if ok:
                return await call_next(request)
            status, msg = HTTP_STATUS.get(reason, (401, reason))
            headers = {"WWW-Authenticate": "Bearer"}
            if reason == "rate_limited":
                headers["Retry-After"] = "5"
            return JSONResponse(
                {"error": reason, "message": msg},
                status_code=status,
                headers=headers,
            )

    return AuthMiddleware


def _check_runtime_artifacts() -> None:
    """Probe data/model paths at startup so a missing volume mount fails
    loud (with file paths) instead of breaking semantic tools at first
    use. Datamart is mandatory; embeddings + descriptions are warned
    about (light tools work without them)."""
    from pathlib import Path

    datamart = os.getenv("CITY_RATING_DATAMART", "")
    if not datamart or not Path(datamart).exists():
        LOG.error(
            "Datamart not found at %r — light tools will fail. "
            "Stage 1 of the Dockerfile builds it; for local dev run "
            "scripts/build-datamart.py.", datamart,
        )

    embeddings = os.getenv("CITY_RATING_EMBEDDINGS", "")
    if not embeddings or not Path(embeddings).exists():
        LOG.warning(
            "Embeddings not found at %r — semantic_search / find_similar / "
            "recommend will raise on first call. In production this file "
            "must be bind-mounted from a Coolify persistent volume "
            "(see mcp/README 'Embeddings: host volume'). For local dev: "
            "python3 scripts/build-embeddings.py.", embeddings,
        )
    else:
        size_mb = Path(embeddings).stat().st_size / 1024 / 1024
        LOG.info("Embeddings file present at %s (%.1f MB).", embeddings, size_mb)


def _serve_http(host: str, port: int, path: str) -> None:
    """HTTP transport with NocoDB-backed bearer-token auth."""
    import uvicorn
    from starlette.middleware import Middleware

    _check_runtime_artifacts()

    auth_required = os.getenv("MCP_AUTH_REQUIRED", "true").lower() not in ("false", "0", "no")
    store = KeyStore() if auth_required else None
    middleware = []

    if store is not None:
        if not store.configured:
            LOG.warning(
                "MCP_AUTH_REQUIRED=true but NocoDB env not set "
                "(NOCODB_API_URL / NOCODB_API_TOKEN / NOCODB_API_KEYS_TABLE_ID) — "
                "the server will start but will reject every request. "
                "Set MCP_AUTH_REQUIRED=false for unauthenticated local dev."
            )
        middleware.append(Middleware(_auth_middleware_factory(store)))
    else:
        LOG.warning("MCP_AUTH_REQUIRED=false — running open. Do not expose publicly.")

    app = mcp.http_app(path=path, transport="http", middleware=middleware)

    if store is not None and store.configured:
        # Run the refresh loop alongside the FastMCP app's lifespan.
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(scope):
            task = asyncio.create_task(store.refresh_loop())
            try:
                async with original_lifespan(scope):
                    yield
            finally:
                task.cancel()

        app.router.lifespan_context = combined_lifespan

    uvicorn.run(app, host=host, port=port, log_level=os.getenv("UVICORN_LOG_LEVEL", "info"))


def main() -> None:
    """CLI entry point. Transport via env or argv."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in ("http", "streamable-http"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        path = os.getenv("MCP_PATH", "/mcp")
        _serve_http(host, port, path)
    elif transport == "sse":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise SystemExit(f"Unknown MCP_TRANSPORT={transport!r}")


if __name__ == "__main__":
    main()
