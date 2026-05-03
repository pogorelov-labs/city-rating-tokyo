#!/usr/bin/env python3
"""Build per-station semantic embeddings for the MCP server.

Reads `app/src/data/generated-descriptions.json` (1493 stations × 3 locales
× 4 fields), encodes each text with multilingual-e5-base via fastembed
(ONNX), and writes `data/embeddings.npz` consumed by the MCP at runtime.

Output schema (parallel arrays of length N):
    vectors  — float32, shape (N, 768), L2-normalized so dot = cosine
    slugs    — str, shape (N,)
    locales  — str, shape (N,)  — 'en' | 'ja' | 'ru'
    fields   — str, shape (N,)  — 'atmosphere'|'landmarks'|'food'|'nightlife'|'all'
    model    — bytes scalar, the model name used for the build

`field='all'` is a per-(slug, locale) aggregate: mean-pool of the 4 field
vectors then L2-renormalized. Used by find_similar so we don't pick a
representative field arbitrarily.

Usage:
    python3 scripts/build-embeddings.py
    python3 scripts/build-embeddings.py --model intfloat/multilingual-e5-base
    python3 scripts/build-embeddings.py --slug shibuya  # dry-run on one station

Notes:
- e5 family REQUIRES "passage: " prefix on documents and "query: " on
  queries. Skip the prefix and recall drops noticeably. Match this in
  the runtime query path (see mcp/src/city_rating_mcp/embeddings.py).
- ~17,916 texts at ~50/sec on an M2 CPU = ~6 min wall time. Output is
  ~70 MB on disk, ~70 MB resident at runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTIONS = ROOT / "app" / "src" / "data" / "generated-descriptions.json"
OUT = ROOT / "data" / "embeddings.npz"

LOCALES = ("en", "ja", "ru")
FIELDS = ("atmosphere", "landmarks", "food", "nightlife")
DEFAULT_MODEL = "intfloat/multilingual-e5-large"


def load_descriptions() -> dict[str, dict[str, dict[str, str]]]:
    with DESCRIPTIONS.open() as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def collect_texts(
    descriptions: dict[str, dict[str, dict[str, str]]],
    only_slug: str | None = None,
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Return (texts, index) for all (slug, locale, field) triples.

    `texts` carries the e5 "passage: " prefix already. `index` is parallel.
    """
    texts: list[str] = []
    index: list[tuple[str, str, str]] = []
    slugs = [only_slug] if only_slug else sorted(descriptions.keys())

    for slug in slugs:
        if slug not in descriptions:
            print(f"warn: slug {slug!r} not in descriptions", file=sys.stderr)
            continue
        per_locale = descriptions[slug]
        for locale in LOCALES:
            block = per_locale.get(locale) or {}
            for field in FIELDS:
                text = (block.get(field) or "").strip()
                if not text:
                    # e5 hates empty strings — skip; we'll back-fill 'all'
                    # only over present fields below.
                    continue
                texts.append(f"passage: {text}")
                index.append((slug, locale, field))
    return texts, index


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--slug", default=None, help="single-slug dry run")
    p.add_argument("--out", default=str(OUT))
    args = p.parse_args()

    import numpy as np
    from fastembed import TextEmbedding

    print(f"Loading descriptions from {DESCRIPTIONS}...")
    descriptions = load_descriptions()
    print(f"  stations: {len(descriptions)}")

    import os
    cache_dir = os.getenv("FASTEMBED_CACHE_DIR") or None
    print(f"\nLoading model {args.model} (ONNX, cache={cache_dir or 'default'})...")
    t0 = time.time()
    embedder = TextEmbedding(model_name=args.model, cache_dir=cache_dir)
    print(f"  ready in {time.time() - t0:.1f}s")

    print("\nCollecting texts...")
    texts, index = collect_texts(descriptions, only_slug=args.slug)
    print(f"  texts: {len(texts)} ({len(LOCALES)} locales × {len(FIELDS)} fields)")

    print("\nEncoding...")
    t0 = time.time()
    # fastembed yields generators; materialize to ndarray.
    vectors = np.asarray(list(embedder.embed(texts)), dtype=np.float32)
    elapsed = time.time() - t0
    print(f"  {vectors.shape[0]} × {vectors.shape[1]} in {elapsed:.1f}s "
          f"({vectors.shape[0] / elapsed:.0f}/s)")

    # L2-normalize so cosine = dot product later
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors /= norms

    # Aggregate per (slug, locale): mean of present fields, renormalize.
    print("\nBuilding 'all' aggregates...")
    by_pair: dict[tuple[str, str], list[int]] = {}
    for i, (slug, locale, _field) in enumerate(index):
        by_pair.setdefault((slug, locale), []).append(i)

    agg_vectors = []
    agg_slugs: list[str] = []
    agg_locales: list[str] = []
    for (slug, locale), idxs in by_pair.items():
        v = vectors[idxs].mean(axis=0)
        n = np.linalg.norm(v)
        if n > 0:
            v = v / n
        agg_vectors.append(v)
        agg_slugs.append(slug)
        agg_locales.append(locale)
    agg_arr = np.asarray(agg_vectors, dtype=np.float32)

    # Concatenate field-level + aggregate vectors into one flat matrix.
    all_vectors = np.concatenate([vectors, agg_arr], axis=0)
    all_slugs = np.array([s for s, _, _ in index] + agg_slugs)
    all_locales = np.array([loc for _, loc, _ in index] + agg_locales)
    all_fields = np.array([f for _, _, f in index] + ["all"] * len(agg_slugs))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        vectors=all_vectors,
        slugs=all_slugs,
        locales=all_locales,
        fields=all_fields,
        model=np.array(args.model),
    )

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n✓ Wrote {out_path}")
    print(f"  total vectors: {all_vectors.shape[0]} (field={len(index)} + all={len(agg_slugs)})")
    print(f"  dim:           {all_vectors.shape[1]}")
    print(f"  on disk:       {size_mb:.1f} MB compressed")


if __name__ == "__main__":
    main()
