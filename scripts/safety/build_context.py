#!/usr/bin/env python3
"""Offline, citation-only aggregates. Never exports source rows or joins stations."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/safety/sources.json"
OUTPUT = ROOT / "app/src/data/safety/context.json"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def checked_input(root, entry):
    content = (root / entry["path"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise ValueError(f"Source changed; review citation before regeneration: {entry['path']}")
    return content


def traffic_total(workbook):
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        strings = ["".join(si.itertext()) for si in ET.fromstring(
            archive.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    totals = []
    for row in sheet.findall("s:sheetData/s:row", NS):
        cells = {}
        for cell in row.findall("s:c", NS):
            value = cell.findtext("s:v", default="", namespaces=NS)
            cells[cell.attrib["r"].rstrip("0123456789")] = (
                strings[int(value)] if cell.attrib.get("t") == "s" and value else value)
        if cells.get("A") == "総数ソウスウ":
            totals.append({"accidents": int(cells["D"]), "fatalities": int(cells["E"])})
    if len(totals) != 1:
        raise ValueError("Expected one explicit metropolitan total; never sum hierarchical rows")
    return totals[0]


def build(root=ROOT, manifest=None):
    manifest = manifest if manifest is not None else json.loads(MANIFEST.read_text())
    if manifest["version"] != 1 or manifest["publication"] != "aggregate_citation_only":
        raise ValueError("Only reviewed aggregate citations can be published")
    files = {key: checked_input(root, value) for key, value in manifest["inputs"].items()}
    traffic = traffic_total(files["traffic_workbook"])
    digest = list(csv.DictReader(io.StringIO(files["traffic_digest"].decode())))
    totals = [r for r in digest if r["police_station(署)"] == "総数ソウスウ"]
    if len(totals) != 1 or traffic != {
        "accidents": int(totals[0]["accidents_発生件数"]),
        "fatalities": int(totals[0]["deaths_死者"]),
    } or traffic != manifest["traffic"]["expected"]:
        raise ValueError("Workbook/digest/reviewed traffic citation disagree")
    survey = json.loads(files["survey_summary"])["files"]["gaisu-r8-01.pdf"]
    # The PDF is image-only: the pinned, visually verified summary is the input.
    counts = [survey[k] for k in ("ward23_23区", "tama_多摩", "national_rivers_国河川")]
    total = survey["total_総計"]
    if any(type(n) is not int or n < 0 for n in [*counts, total]) or sum(counts) != total:
        raise ValueError("Survey count must include wards, Tama AND national rivers")
    welfare = {"people": total}
    if welfare != manifest["welfare"]["expected"]:
        raise ValueError("Survey differs from reviewed factual citation")
    facts = {}
    for name, values in (("traffic", traffic), ("welfare", welfare)):
        source = manifest[name]
        # Explicit allowlist: raw records, blocked inputs and editorial scores
        # cannot leak through a blanket manifest spread.
        facts[name] = {k: source[k] for k in (
            "publisher", "period", "scope", "unit", "denominator", "source_url", "document_url", "table")}
        facts[name]["values"] = values
    return {"version": 1, "publication": "aggregate_citation_only",
            "verified_at": manifest["verified_at"], "facts": facts,
            "source_sha256": {key: entry["sha256"] for key, entry in manifest["inputs"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on generated-output drift; write nothing")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != content:
            raise SystemExit("Safety context drift; run python3 scripts/safety/build_context.py")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content)
    print("Verified two aggregate citations; no station/registry rows or ratings generated")


if __name__ == "__main__":
    main()
