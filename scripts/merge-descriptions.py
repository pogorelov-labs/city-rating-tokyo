#!/usr/bin/env python3
"""
Merge all data/descriptions/<slug>.json into a single generated-descriptions.json.

Run after batch generation is complete (or as a checkpoint).

Usage:
    python3 scripts/merge-descriptions.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESC_DIR = ROOT / "data" / "descriptions"
# Output lives under app/src/data/ so the Next.js frontend can import it —
# `data/` (repo root) is outside the Docker build context per CRTKY-86 fix.
OUT_PATH = ROOT / "app" / "src" / "data" / "generated-descriptions.json"


def validate(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    for lang in ["en", "ja", "ru"]:
        if lang not in d or not isinstance(d[lang], dict):
            return False
        for field in ["atmosphere", "landmarks", "food", "nightlife"]:
            if field not in d[lang] or not isinstance(d[lang][field], str) or not d[lang][field].strip():
                return False
    return True


def main():
    files = sorted(DESC_DIR.glob("*.json"))
    merged = {
        "_metadata": {
            "description": "Merged from data/descriptions/*.json. Per-station multilingual descriptions generated via LLM agents (Claude Code, Codex, Cursor, etc).",
            "model": "haiku/sonnet/mixed",
            "count": 0,
            "invalid": 0,
        }
    }

    invalid = []
    for f in files:
        try:
            with open(f) as fh:
                d = json.load(fh)
            if validate(d):
                merged[f.stem] = d
            else:
                invalid.append(f.stem)
        except Exception as e:
            invalid.append(f"{f.stem}: {e}")

    merged["_metadata"]["count"] = len([k for k in merged if not k.startswith("_")])
    merged["_metadata"]["invalid"] = len(invalid)

    with open(OUT_PATH, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"✓ Merged {merged['_metadata']['count']} descriptions → {OUT_PATH}")
    if invalid:
        print(f"⚠ {len(invalid)} invalid files skipped:")
        for entry in invalid[:10]:
            print(f"    {entry}")


if __name__ == "__main__":
    main()
