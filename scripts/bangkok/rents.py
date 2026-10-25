"""Provenance and validation for editorial district rents and station proxies."""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

CONFIDENCE = {"moderate", "estimate", "editorial"}


def validate_overrides(doc: dict, area_ids: set[str]) -> None:
    """Validate against the areas actually built, never a second hand-kept ID list."""
    meta, areas = doc["_meta"], doc["areas"]
    sources = meta["sources"]
    unknown = set(areas) - area_ids
    if unknown:
        raise ValueError(f"Unknown rent override areas: {sorted(unknown)}")
    date.fromisoformat(meta["audited_at"])
    for aid, entry in areas.items():
        def require(ok: bool, message: str) -> None:
            if not ok:
                raise ValueError(f"{aid}: {message}")

        r1, r2 = entry["rent_1br"], entry["rent_2br"]
        require(type(r1) is int and type(r2) is int and 5_000 <= r1 < r2 <= 120_000, "invalid rent bounds")
        require(entry["confidence"] in CONFIDENCE, "invalid rent confidence")
        require(entry["metric"] == "median_asking_by_bedroom", "unsupported rent metric")
        as_of = date.fromisoformat(entry["as_of"])
        require(as_of <= date.fromisoformat(meta["audited_at"]), "rent date after audit")
        require(bool(entry["method"].strip()), "missing method")
        require(bool(entry["limitations"]) and all(s.strip() for s in entry["limitations"]), "missing limitations")
        require(set(entry["sample_size"]) == {"one_bed", "two_bed"}, "missing bedroom sample counts")
        for n in entry["sample_size"].values():
            require(type(n) is int and n >= 5, "median requires at least five listings per bedroom")
        require(set(entry["source_typical_size_sqm"]) == {"one_bed", "two_bed"}, "missing size descriptors")
        for size in entry["source_typical_size_sqm"].values():
            require(size is None or (type(size) in (int, float) and size > 0), "invalid size descriptor")
        require(type(entry.get("composition_skew", False)) is bool, "invalid composition flag")
        require(bool(entry["sources"]), "missing source")
        for sid in entry["sources"]:
            require(sid in sources, f"unknown source {sid}")
            source = sources[sid]
            url = urlparse(source["url"])
            require(url.scheme == "https" and bool(url.netloc), "source needs a public HTTPS URL")
            require(bool(source["publisher"].strip()), "missing publisher")
            require(source["as_of"] == entry["as_of"], "source date mismatch")
            require(as_of <= date.fromisoformat(source["accessed"]) <= date.fromisoformat(meta["audited_at"]), "invalid access date")


def editorial_rent(entry: dict, meta: dict, *, blend: bool = False) -> dict:
    """Keep the existing fixed-size estimate; an audit is not a new observation."""
    return {
        "one_bed": entry["rent_1br"], "two_bed": entry["rent_2br"],
        "source": "listing_research", "updated": meta["as_of"], "as_of": meta["as_of"],
        "confidence": entry.get("rent_confidence", meta["confidence"]),
        "metric": "typical_asking", "provenance": "district_blend" if blend else "district_editorial",
        "definition": meta["definition"], "method": (
            "Resident-weighted district rent blend, rounded to 500 THB. " if blend else ""
        ) + meta["method"],
        "sample_size": None, "sources": [], "limitations": meta["limitations"],
        "audited_at": meta["audited_at"], "source_audit": meta["source_audit"],
    }


def station_rent(aid: str, blended: dict, editorial_meta: dict, overrides: dict) -> dict:
    baseline = {k: blended[k] for k in ("rent_1br", "rent_2br")}
    entry = overrides["areas"].get(aid)
    if entry is None:
        return {**editorial_rent(blended, editorial_meta, blend=True), "editorial_baseline": baseline}
    meta = overrides["_meta"]
    return {
        "one_bed": entry["rent_1br"], "two_bed": entry["rent_2br"],
        "source": "dooasset", "updated": entry["as_of"], "as_of": entry["as_of"],
        "confidence": entry["confidence"], "metric": entry["metric"], "provenance": "station_override",
        "definition": meta["definition"], "method": entry["method"],
        "sample_size": entry["sample_size"], "source_typical_size_sqm": entry["source_typical_size_sqm"],
        "composition_skew": entry.get("composition_skew", False), "editorial_baseline": baseline,
        "sources": [{"id": sid, **meta["sources"][sid]} for sid in entry["sources"]],
        "limitations": entry["limitations"], "audited_at": meta["audited_at"], "source_audit": meta["audit"],
    }


def rent_audit(overrides: dict) -> dict:
    return {
        "audited_at": overrides["_meta"]["audited_at"], "source_audit": overrides["_meta"]["audit"],
        "station_override_count": len(overrides["areas"]), "grid_rent": "district_editorial",
    }


GRID_POLICY = "district_editorial; station-area rent overrides do not apply to grid cells"


def refresh_committed_rents(editorial: dict, overrides: dict, districts_doc: dict,
                            areas_doc: dict, meta: dict, grid: dict, signals: dict,
                            ratings, default_weights: dict) -> None:
    """Refresh rent without reacquiring OSM/POIs or recomputing geometry.

    District changes need the full spatial build to recompute resident shares.
    Save the original area pair so removing an override restores its blend.
    """
    districts, areas = districts_doc["districts"], areas_doc["areas"]
    district_inputs, rent_meta = editorial["districts"], editorial["_meta"]["rent"]
    if len(districts) != 50 or {d["slug"] for d in districts} != set(district_inputs):
        raise ValueError("Rent refresh requires all 50 committed districts")
    if len(areas) != meta["station_area_count"] or {a["id"] for a in areas} != set(grid["areas"]):
        raise ValueError("Rent refresh requires a complete committed area/grid join")
    validate_overrides(overrides, {a["id"] for a in areas})
    planned = {}
    for d in districts:
        entry = district_inputs[d["slug"]]
        if (d["rent"]["one_bed"], d["rent"]["two_bed"]) != (entry["rent_1br"], entry["rent_2br"]):
            raise ValueError("District rents changed: run the full spatial build")
    for a in areas:
        old = a["rent"]
        baseline = old.get("editorial_baseline")
        if baseline is None:
            if old.get("provenance") == "station_override" or old["source"] != "listing_research":
                raise ValueError(f"{a['id']}: missing editorial baseline; run the full build")
            baseline = {"rent_1br": old["one_bed"], "rent_2br": old["two_bed"]}
        planned[a["id"]] = station_rent(a["id"], baseline, rent_meta, overrides)

    for d in districts:
        d["rent"] = editorial_rent(district_inputs[d["slug"]], rent_meta)
        d["confidence"]["rent"] = d["rent"]["confidence"]
        d["sources"]["rent"] = [d["rent"]["source"]]
    for a in areas:
        rent = planned[a["id"]]
        a["rent"] = rent
        a["ratings"]["rent"] = ratings.rent_to_affordability(rent["one_bed"])
        a["confidence"]["rent"] = rent["confidence"]
        a["sources"]["rent"] = [rent["source"]]
        signal = signals["station_areas"][a["id"]]
        signal["rent_1br"], signal["rent_2br"] = rent["one_bed"], rent["two_bed"]
        signal["raw"]["rent"] = rent["one_bed"]
        signal["ratings"]["rent"] = a["ratings"]["rent"]
    meta["station_medians"]["rent"] = ratings.median_int([a["ratings"]["rent"] for a in areas])
    meta["station_default_anchors"] = ratings.anchors([ratings.composite(a["ratings"], default_weights) for a in areas])
    meta["rent_audit"] = rent_audit(overrides)
    grid["rent_policy"] = GRID_POLICY
    for doc in (districts_doc, areas_doc):
        doc["_meta"]["rent_audit"] = rent_audit(overrides)
