#!/usr/bin/env python3
"""Generate HTML contact sheet from face detection results for human review.

Reads flagged-faces.json (output of detect-faces.py) and generates a self-contained
HTML page with image cards. User checks/unchecks images, then exports confirmed
removals as JSON.

Usage:
  python3 scripts/generate-face-review.py [flagged-faces.json] [output.html]

Defaults:
  Input:  /tmp/face-detect-results/flagged-faces.json
  Output: /tmp/face-review.html
"""

import json
import sys
from pathlib import Path
from html import escape

DEFAULT_INPUT = "/tmp/face-detect-results/flagged-faces.json"
DEFAULT_OUTPUT = "/tmp/face-review.html"


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_INPUT)
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_OUTPUT)

    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    with open(input_path) as f:
        flagged = json.load(f)

    # Flatten into sorted list
    all_entries = []
    for slug, entries in sorted(flagged.items()):
        for entry in entries:
            all_entries.append(entry)

    # Sort: first-images first, then by area ratio descending
    all_entries.sort(key=lambda e: (-e["is_first_image"], -e["max_area_ratio"]))

    total = len(all_entries)
    first_count = sum(1 for e in all_entries if e["is_first_image"])

    print(f"Loaded {total} flagged images from {len(flagged)} stations")
    print(f"  First-image (preview) flags: {first_count}")

    # Generate HTML
    cards_html = []
    for i, entry in enumerate(all_entries):
        slug = escape(entry["slug"])
        url = escape(entry["url"])
        local_path = escape(entry["local_path"])
        face_count = entry["face_count"]
        max_area = entry["max_area_ratio"]
        max_conf = entry["max_confidence"]
        is_first = entry["is_first_image"]
        idx = entry["index"]

        badge = '<span class="badge preview">MAP PREVIEW</span>' if is_first else ""
        area_class = "high" if max_area > 0.05 else "medium" if max_area > 0.02 else "low"

        cards_html.append(f"""
    <div class="card" data-slug="{slug}" data-local-path="{local_path}" data-index="{idx}">
      <div class="img-wrap">
        <img src="{url}" alt="{slug}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22200%22><rect fill=%22%23eee%22 width=%22300%22 height=%22200%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22>Load error</text></svg>'">
      </div>
      <div class="info">
        <div class="slug">{slug} <span class="idx">[{idx}]</span> {badge}</div>
        <div class="meta">
          <span class="faces">{face_count} face{"s" if face_count != 1 else ""}</span>
          <span class="area {area_class}">area: {max_area:.1%}</span>
          <span class="conf">conf: {max_conf:.0%}</span>
        </div>
        <label class="check">
          <input type="checkbox" checked>
          <span>Remove</span>
        </label>
      </div>
    </div>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Face Detection Review — {total} flagged images</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, system-ui, sans-serif; background: #f5f5f5; color: #333; }}
.header {{
  position: sticky; top: 0; z-index: 100; background: #fff; border-bottom: 1px solid #ddd;
  padding: 12px 20px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}}
.header h1 {{ font-size: 18px; font-weight: 600; }}
.header .stats {{ font-size: 13px; color: #666; }}
.header .actions {{ display: flex; gap: 8px; margin-left: auto; }}
.btn {{
  padding: 6px 14px; border: 1px solid #ccc; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 13px;
}}
.btn:hover {{ background: #f0f0f0; }}
.btn.primary {{ background: #d32f2f; color: #fff; border-color: #d32f2f; }}
.btn.primary:hover {{ background: #b71c1c; }}
.filters {{
  padding: 8px 20px; background: #fff; border-bottom: 1px solid #eee;
  display: flex; gap: 12px; font-size: 13px;
}}
.filters label {{ cursor: pointer; }}
.grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px; padding: 16px 20px;
}}
.card {{
  background: #fff; border-radius: 8px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.1); transition: opacity .2s;
}}
.card.hidden {{ display: none; }}
.card .img-wrap {{ position: relative; width: 100%; aspect-ratio: 16/10; overflow: hidden; background: #eee; }}
.card img {{ width: 100%; height: 100%; object-fit: cover; }}
.card .info {{ padding: 8px 12px; }}
.card .slug {{ font-weight: 600; font-size: 14px; }}
.card .idx {{ color: #999; font-weight: 400; }}
.badge {{ display: inline-block; font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px; vertical-align: middle; }}
.badge.preview {{ background: #fff3e0; color: #e65100; }}
.card .meta {{ display: flex; gap: 8px; font-size: 12px; color: #666; margin-top: 4px; }}
.area.high {{ color: #d32f2f; font-weight: 600; }}
.area.medium {{ color: #f57c00; }}
.area.low {{ color: #666; }}
.card .check {{ display: flex; align-items: center; gap: 6px; margin-top: 6px; cursor: pointer; font-size: 13px; }}
.card .check input {{ width: 16px; height: 16px; }}
.card:has(input:not(:checked)) {{ opacity: 0.4; }}
.selected-count {{ font-weight: 600; color: #d32f2f; }}
</style>
</head>
<body>

<div class="header">
  <h1>Face Detection Review</h1>
  <div class="stats">
    <span>{total} flagged</span> &middot;
    <span>{first_count} map previews</span> &middot;
    <span class="selected-count" id="count">0 selected for removal</span>
  </div>
  <div class="actions">
    <button class="btn" onclick="selectAll()">Select All</button>
    <button class="btn" onclick="selectNone()">Select None</button>
    <button class="btn" onclick="selectPreviews()">Previews Only</button>
    <button class="btn primary" onclick="exportRemovals()">Export Removals JSON</button>
  </div>
</div>

<div class="filters">
  <label><input type="checkbox" id="filter-preview" onchange="applyFilters()"> Show only map previews</label>
  <label><input type="checkbox" id="filter-large" onchange="applyFilters()"> Show only large faces (&gt;5%)</label>
</div>

<div class="grid" id="grid">
{"".join(cards_html)}
</div>

<script>
function updateCount() {{
  const checked = document.querySelectorAll('.card:not(.hidden) input:checked').length;
  const total = document.querySelectorAll('.card:not(.hidden)').length;
  document.getElementById('count').textContent = checked + ' of ' + total + ' selected for removal';
}}

function selectAll() {{
  document.querySelectorAll('.card:not(.hidden) input').forEach(c => c.checked = true);
  updateCount();
}}

function selectNone() {{
  document.querySelectorAll('.card:not(.hidden) input').forEach(c => c.checked = false);
  updateCount();
}}

function selectPreviews() {{
  document.querySelectorAll('.card input').forEach(c => c.checked = false);
  document.querySelectorAll('.card .badge.preview').forEach(b => {{
    b.closest('.card').querySelector('input').checked = true;
  }});
  updateCount();
}}

function applyFilters() {{
  const previewOnly = document.getElementById('filter-preview').checked;
  const largeOnly = document.getElementById('filter-large').checked;
  document.querySelectorAll('.card').forEach(card => {{
    let show = true;
    if (previewOnly && !card.querySelector('.badge.preview')) show = false;
    if (largeOnly) {{
      const areaText = card.querySelector('.area').textContent;
      const areaVal = parseFloat(areaText.replace('area: ', '').replace('%', ''));
      if (areaVal < 5) show = false;
    }}
    card.classList.toggle('hidden', !show);
  }});
  updateCount();
}}

function exportRemovals() {{
  const removals = [];
  document.querySelectorAll('.card').forEach(card => {{
    const cb = card.querySelector('input');
    if (cb.checked) {{
      removals.push({{
        slug: card.dataset.slug,
        local_path: card.dataset.localPath,
        index: parseInt(card.dataset.index),
      }});
    }}
  }});

  if (removals.length === 0) {{
    alert('No images selected for removal.');
    return;
  }}

  const blob = new Blob([JSON.stringify(removals, null, 2)], {{ type: 'application/json' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'confirmed-removals.json';
  a.click();
  URL.revokeObjectURL(a.href);
}}

// Init
document.querySelectorAll('.card input').forEach(cb => {{
  cb.addEventListener('change', updateCount);
}});
updateCount();
</script>

</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    size_kb = output_path.stat().st_size / 1024
    print(f"Wrote {output_path} ({size_kb:.0f} KB)")
    print(f"Open in browser to review and export confirmed-removals.json")


if __name__ == "__main__":
    main()
