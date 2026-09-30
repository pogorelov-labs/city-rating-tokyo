"""
Station slug canonicalisation for rows read from NocoDB.

CRTKY-113 renamed 334 station slugs (wapuro → Hepburn). stations.json and the
local JSON files were re-keyed, but NocoDB rows scraped before the rename still
carry the old slugs, so every join by slug silently missed those stations and
their ratings fell back to proxies in every category. Readers must index NocoDB
rows through `index_by_slug`, never with a bare `{r["slug"]: r ...}`.

Kept free of NocoDB/requests imports so tests and offline scripts can use it.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REDIRECTS_PATH = ROOT / "app" / "src" / "data" / "slug-redirects.json"


def load_slug_redirects(path=REDIRECTS_PATH):
    """Map of old slug → current slug (CRTKY-113)."""
    return json.loads(Path(path).read_text())


def index_by_slug(rows, redirects=None, key="slug"):
    """
    Index rows by current slug.

    Rows under an old slug are remapped through the redirects. If a table holds
    rows under both spellings (a station re-scraped after the rename), the row
    under the current slug wins, since it is the newer one.

    Remapped rows are shallow copies whose `key` field holds the current slug.
    Returns (index, remapped) where remapped counts rows that were re-keyed.
    """
    if redirects is None:
        redirects = load_slug_redirects()
    index = {}
    for row in rows:
        slug = row.get(key)
        if slug and slug not in redirects:
            index[slug] = row
    remapped = 0
    for row in rows:
        slug = row.get(key)
        if slug in redirects and redirects[slug] not in index:
            # Copy with the current slug so the old one cannot leak downstream.
            index[redirects[slug]] = {**row, key: redirects[slug]}
            remapped += 1
    return index, remapped
