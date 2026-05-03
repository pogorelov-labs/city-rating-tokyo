"""Heavy tools backed by embeddings: semantic_search, find_similar, recommend."""

from __future__ import annotations

from typing import Any

from ..data import Datamart
from ..embeddings import EmbeddingStore
from ..scoring import DEFAULT_WEIGHTS, composite_score, passes_dealbreakers
from ..views import search_row


def semantic_search(
    dm: Datamart,
    es: EmbeddingStore,
    *,
    query: str,
    locale: str = "en",
    field: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Find stations whose descriptions best match a free-form query.

    `field=None` searches over the per-(slug, locale) aggregate so each
    station contributes one vector. `field='nightlife'` (or atmosphere /
    landmarks / food) constrains the search to that single field — useful
    for queries like "loud, late, izakaya alley".
    """
    if not query or not query.strip():
        raise ValueError("query is empty")
    qvec = es.embed_query(query)
    hits = es.search(qvec, locale=locale, field=field, limit=limit)
    out = []
    for slug, fld, score in hits:
        entry = dm.get(slug)
        if entry is None:
            continue
        row = search_row(entry, composite_score(entry.get("ratings")), locale=locale)
        row["semantic_score"] = round(score, 4)
        row["matched_field"] = fld
        out.append(row)
    return {"query": query, "locale": locale, "field": field, "results": out}


def find_similar(
    dm: Datamart,
    es: EmbeddingStore,
    *,
    slug: str,
    locale: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
    """Stations most semantically similar to `slug` based on description vectors."""
    if dm.get(slug) is None:
        raise ValueError(f"Station '{slug}' not found")
    qvec = es.aggregate_vector(slug, locale)
    if qvec is None:
        raise ValueError(
            f"No embedding for ({slug}, {locale}). Was the embeddings build "
            f"run after descriptions were generated?"
        )
    # +1 because the seed station will be its own top hit.
    hits = es.search(qvec, locale=locale, field=None, limit=limit + 1)
    out = []
    for s, _fld, score in hits:
        if s == slug:
            continue
        entry = dm.get(s)
        if entry is None:
            continue
        row = search_row(entry, composite_score(entry.get("ratings")), locale=locale)
        row["similarity"] = round(score, 4)
        out.append(row)
        if len(out) >= limit:
            break
    return {"seed": slug, "locale": locale, "results": out}


def recommend(
    dm: Datamart,
    es: EmbeddingStore,
    *,
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
    candidate_pool: int = 60,
    limit: int = 10,
) -> dict[str, Any]:
    """Hybrid: semantic intent + structured weights + hard filters.

    Pipeline: take top `candidate_pool` by semantic similarity over the
    aggregate vector, drop anything that fails the dealbreakers, then
    re-rank by `alpha * cosine + (1 - alpha) * composite/10`. alpha=0
    is pure data-driven (same as search_stations), alpha=1 is pure
    semantic. Default 0.5 = "tell me good places that match the vibe."

    The two-stage shape (cosine pool → filter → blend) avoids letting a
    single very-cosine hit with bad ratings win, while not paying for
    composite scoring on all 1493 stations.
    """
    if not query or not query.strip():
        raise ValueError("query is empty")
    if not 0 <= hybrid_alpha <= 1:
        raise ValueError("hybrid_alpha must be in [0, 1]")

    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    qvec = es.embed_query(query)

    # Stage 1: fetch a pool from semantic search, then filter
    pool = es.search(qvec, locale=locale, field=None, limit=max(limit * 3, candidate_pool))
    survivors: list[tuple[float, dict[str, Any], dict[str, Any]]] = []

    for slug, _fld, sem in pool:
        entry = dm.get(slug)
        if entry is None:
            continue
        ok, flags = passes_dealbreakers(
            entry,
            min_rent=min_rent,
            max_rent=max_rent,
            min_commute=min_commute,
            max_commute=max_commute,
            category_mins=category_mins,
            has_live_camera=has_live_camera,
            hide_flood_risk=hide_flood_risk,
            hide_high_seismic=hide_high_seismic,
        )
        if not ok:
            continue
        comp = composite_score(entry.get("ratings"), w)
        if comp is None:
            continue
        # cosine in [-1, 1]; clamp to [0, 1] for the blend
        sem_clamped = max(0.0, min(1.0, sem))
        blended = hybrid_alpha * sem_clamped + (1 - hybrid_alpha) * (comp / 10.0)
        survivors.append((blended, comp, sem_clamped, entry, flags))  # type: ignore[arg-type]

    survivors.sort(key=lambda r: r[0], reverse=True)  # type: ignore[index]
    top = survivors[:limit]

    return {
        "query": query,
        "locale": locale,
        "weights": w,
        "hybrid_alpha": hybrid_alpha,
        "candidate_pool": candidate_pool,
        "total_after_filters": len(survivors),
        "results": [
            {
                **search_row(entry, comp, locale=locale, rent_unknown=flags.get("rent_unknown", False)),
                "blended_score": round(blended, 4),
                "semantic_score": round(sem, 4),
            }
            for blended, comp, sem, entry, flags in top  # type: ignore[misc]
        ],
    }
