"""In-memory embeddings store + cosine search.

Loads `data/embeddings.npz` (built by scripts/build-embeddings.py) once
at startup, slices the flat vector matrix into per-(locale, field)
views for fast filtered cosine. Query-time embedding goes through the
same fastembed model name baked into the npz so build-time and runtime
vectors live in the same space.

The fastembed model is loaded lazily on the first query — Phase 1 tools
(search/get/compare/etc.) shouldn't pay the ~3 s model-load cost.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import numpy as np

LOG = logging.getLogger("city_rating_mcp.embeddings")

EMBEDDINGS_ENV = "CITY_RATING_EMBEDDINGS"
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "embeddings.npz"


class EmbeddingStore:
    """Loaded once at startup; thread-safe lazy model init for queries."""

    def __init__(
        self,
        vectors: np.ndarray,
        slugs: np.ndarray,
        locales: np.ndarray,
        fields: np.ndarray,
        model_name: str,
    ):
        self.vectors = vectors  # (N, D), L2-normalized → dot = cosine
        self.slugs = slugs
        self.locales = locales
        self.fields = fields
        self.model_name = model_name
        self._model_lock = threading.Lock()
        self._model = None  # type: ignore[assignment]

        # Pre-compute (locale, field) → row indices for O(1) lookups.
        self._by_lf: dict[tuple[str, str], np.ndarray] = {}
        for loc in np.unique(locales):
            for fld in np.unique(fields):
                mask = (locales == loc) & (fields == fld)
                idx = np.where(mask)[0]
                if idx.size:
                    self._by_lf[(str(loc), str(fld))] = idx

        # (slug, locale) → 'all' aggregate row index, for find_similar.
        self._agg_idx: dict[tuple[str, str], int] = {}
        agg_mask = fields == "all"
        for i in np.where(agg_mask)[0]:
            self._agg_idx[(str(slugs[i]), str(locales[i]))] = int(i)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "EmbeddingStore":
        path = Path(path or os.getenv(EMBEDDINGS_ENV) or DEFAULT_PATH)
        if not path.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {path}. Run scripts/build-embeddings.py."
            )
        with np.load(path, allow_pickle=False) as z:
            vectors = z["vectors"]
            slugs = z["slugs"]
            locales = z["locales"]
            fields = z["fields"]
            model = str(z["model"])
        LOG.info(
            "embeddings loaded: %d vectors, dim=%d, model=%s",
            vectors.shape[0], vectors.shape[1], model,
        )
        return cls(vectors=vectors, slugs=slugs, locales=locales, fields=fields, model_name=model)

    def _embedder(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    from fastembed import TextEmbedding
                    cache_dir = os.getenv("FASTEMBED_CACHE_DIR") or None
                    LOG.info(
                        "loading fastembed model %s (cache=%s) ...",
                        self.model_name, cache_dir or "default",
                    )
                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=cache_dir,
                    )
                    LOG.info("fastembed model ready")
        return self._model

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query with the e5 'query: ' prefix; L2-normalize."""
        emb = self._embedder()
        v = next(iter(emb.embed([f"query: {text}"])))
        v = np.asarray(v, dtype=np.float32)
        n = np.linalg.norm(v)
        if n > 0:
            v = v / n
        return v

    def search(
        self,
        query_vec: np.ndarray,
        *,
        locale: str = "en",
        field: str | None = None,
        limit: int = 10,
        slug_filter: set[str] | None = None,
    ) -> list[tuple[str, str, float]]:
        """Top-k (slug, field, score) by cosine.

        If `field` is None we search over the (slug, locale) aggregate
        ('all') so each station contributes one vector — better for
        general queries. If `field` is given, search across that field
        only.
        """
        target_field = field or "all"
        idx = self._by_lf.get((locale, target_field))
        if idx is None or idx.size == 0:
            return []

        sub = self.vectors[idx]  # (k, D)
        scores = sub @ query_vec  # (k,)

        if slug_filter is not None:
            mask = np.array([self.slugs[i] in slug_filter for i in idx])
            scores = np.where(mask, scores, -np.inf)

        k = max(1, min(limit, scores.size))
        # argpartition for top-k, then sort just those k
        top_idx = np.argpartition(-scores, kth=k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        return [
            (
                str(self.slugs[idx[i]]),
                str(self.fields[idx[i]]),
                float(scores[i]),
            )
            for i in top_idx
            if scores[i] > -np.inf
        ]

    def aggregate_vector(self, slug: str, locale: str) -> np.ndarray | None:
        """The (slug, locale) 'all' vector — used by find_similar."""
        i = self._agg_idx.get((slug, locale))
        if i is None:
            return None
        return self.vectors[i]
