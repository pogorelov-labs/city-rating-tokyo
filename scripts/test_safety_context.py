"""Citation provenance, publication boundary and aggregate-integrity checks."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("safety_context", Path(__file__).parent / "safety/build_context.py")
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


def manifest():
    return json.loads(context.MANIFEST.read_text())


def test_pinned_sources_reproduce_public_citations_without_rows():
    result = context.build()
    assert result == json.loads(context.OUTPUT.read_text())
    assert set(result["facts"]) == {"traffic", "welfare"}
    assert result["facts"]["traffic"]["values"] == {"accidents": 30176, "fatalities": 134}
    assert result["facts"]["welfare"]["values"] == {"people": 507}
    assert all(fact["denominator"] is None for fact in result["facts"].values())
    text = json.dumps(result)
    for forbidden in ("station_slug", "latitude", "longitude", "safety_score", "bkk_accident", "ced0066", "women_in_total"):
        assert forbidden not in text


def test_changed_source_cannot_silently_update_a_citation():
    data = manifest()
    data["inputs"]["survey_pdf"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Source changed"):
        context.build(manifest=data)


def test_workbook_total_must_agree_with_reviewed_citation():
    data = manifest()
    data["traffic"]["expected"]["accidents"] = 30175
    with pytest.raises(ValueError, match="disagree"):
        context.build(manifest=data)


@pytest.mark.parametrize("publication", ["internal_only", "open_data", None])
def test_no_implicit_graduation_from_snapshot_to_public_dataset(publication):
    data = manifest()
    data["publication"] = publication
    with pytest.raises(ValueError, match="aggregate citations"):
        context.build(manifest=data)


def test_survey_cannot_drop_national_rivers(monkeypatch):
    original = context.checked_input
    def changed(root, entry):
        raw = original(root, entry)
        if entry["path"].endswith("homeless-surveys-summary.json"):
            data = json.loads(raw)
            data["files"]["gaisu-r8-01.pdf"]["national_rivers_国河川"] = 0
            return json.dumps(data).encode()
        return raw
    monkeypatch.setattr(context, "checked_input", changed)
    with pytest.raises(ValueError, match="national rivers"):
        context.build()


def test_blocked_rows_and_extra_metadata_are_not_spread_into_public_output():
    data = copy.deepcopy(manifest())
    data["blocked"].append({"id": "unapproved", "rows": [{"name": "PRIVATE_ROW"}]})
    data["traffic"]["unapproved_rows"] = [{"name": "PRIVATE_ROW"}]
    assert "PRIVATE_ROW" not in json.dumps(context.build(manifest=data))
