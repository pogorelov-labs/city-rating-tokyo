"""In-memory datamart store.

Loads `data/station-datamart.json` (produced by `scripts/build-datamart.py`)
once at startup and merges in `generated-descriptions.json` (produced by
the CRTKY-109 LLM pipeline) so each entry carries a multilingual
`description: {en, ja, ru}` block. Descriptions are kept in a separate
file because the datamart is rebuilt against NocoDB but descriptions
ship as a committed JSON artifact.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterable

import orjson

LOG = logging.getLogger("city_rating_mcp.data")

DATAMART_ENV = "CITY_RATING_DATAMART"
DESCRIPTIONS_ENV = "CITY_RATING_DESCRIPTIONS"
LIVECAMS_ENV = "CITY_RATING_LIVECAMS"
DEFAULT_DATAMART = Path(__file__).resolve().parents[3] / "data" / "station-datamart.json"
DEFAULT_DESCRIPTIONS = (
    Path(__file__).resolve().parents[3] / "app" / "src" / "data" / "generated-descriptions.json"
)
DEFAULT_LIVECAMS = (
    Path(__file__).resolve().parents[3] / "app" / "src" / "data" / "livecams.json"
)


class Datamart:
    """In-memory view of the per-station datamart."""

    def __init__(self, stations: dict[str, dict[str, Any]], generation_order: list[str], metadata: dict[str, Any]):
        self._stations = stations
        self._order = generation_order
        self._metadata = metadata

    @classmethod
    def load(
        cls,
        path: Path | str | None = None,
        descriptions_path: Path | str | None = None,
        livecams_path: Path | str | None = None,
    ) -> "Datamart":
        path = Path(path or os.getenv(DATAMART_ENV) or DEFAULT_DATAMART)
        if not path.exists():
            raise FileNotFoundError(
                f"Datamart not found at {path}. Run scripts/build-datamart.py first "
                f"or set {DATAMART_ENV}."
            )
        with path.open("rb") as f:
            payload = orjson.loads(f.read())
        stations = payload.get("stations", {})

        # Optional: merge multilingual descriptions. Missing file is OK
        # (Phase 1 deployments may pre-date CRTKY-109 Phase 6).
        desc_path = Path(
            descriptions_path or os.getenv(DESCRIPTIONS_ENV) or DEFAULT_DESCRIPTIONS
        )
        if desc_path.exists():
            with desc_path.open("rb") as f:
                desc_data = orjson.loads(f.read())
            merged = 0
            for slug, entry in stations.items():
                d = desc_data.get(slug)
                # Skip the _metadata key and any non-dict entries
                if isinstance(d, dict) and "en" in d:
                    entry["description"] = d
                    merged += 1
            LOG.info("merged descriptions for %d / %d stations", merged, len(stations))
        else:
            LOG.warning("descriptions file not found at %s — skipping merge", desc_path)

        # Optional: merge livecams.json (live YouTube cameras within 300m,
        # ~29 stations today). Same pattern as descriptions — kept out of
        # the datamart because the cadence differs.
        cam_path = Path(
            livecams_path or os.getenv(LIVECAMS_ENV) or DEFAULT_LIVECAMS
        )
        if cam_path.exists():
            with cam_path.open("rb") as f:
                cam_data = orjson.loads(f.read())
            merged_cams = 0
            for slug, cams in cam_data.items():
                if slug.startswith("_"):
                    continue
                entry = stations.get(slug)
                if entry is not None and isinstance(cams, list) and cams:
                    entry["livecams"] = cams
                    merged_cams += 1
            LOG.info("merged livecams for %d stations", merged_cams)
        else:
            LOG.warning("livecams file not found at %s — skipping merge", cam_path)

        return cls(
            stations=stations,
            generation_order=payload.get("generation_order", []),
            metadata=payload.get("metadata", {}),
        )

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def __len__(self) -> int:
        return len(self._stations)

    def __contains__(self, slug: str) -> bool:
        return slug in self._stations

    def get(self, slug: str) -> dict[str, Any] | None:
        return self._stations.get(slug)

    def all(self) -> Iterable[dict[str, Any]]:
        return self._stations.values()

    def slugs(self) -> list[str]:
        return list(self._stations.keys())

    def by_score_desc(self) -> list[str]:
        return list(self._order)
