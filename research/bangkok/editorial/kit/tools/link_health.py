#!/usr/bin/env python3
"""C-6/G14: link-health wave over all canonical URLs in the researched bundles.

Checks URL *resolution* (HTTP status), not content drift — content re-reads
are the dated recheck waves (WS-C C-1..C-4) and the end-of-batch volatile
recheck (C-7). Dead URLs are reported for flagging on the source record;
claims citing them get "archived citation" status — never silent deletion.

Politeness: 8 workers, 15 s timeout, one GET per URL, no retry loops.
Wikipedia/OSM et al. are fine with a plain GET; nothing is bypassed
(403/401 are recorded as access-limited, not worked around).

Run: python3 -I link_health.py --batch-dir <b1> [...] --out <wave.json>
"""
import argparse
import collections
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

UA = "Mozilla/5.0 (compatible; city-rating-research-linkcheck/1.0; +research-robot)"


def check(url):
    # Thai-script IRIs must be percent-encoded for urllib (checker bug fixed 2026-11-08)
    fetch = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")
    req = urllib.request.Request(fetch, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return url, r.status, None
    except urllib.error.HTTPError as e:
        return url, e.code, f"http {e.code}"
    except Exception as e:  # noqa: BLE001 — report class, not details
        return url, None, type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    urls, where = [], collections.defaultdict(set)
    for bd in args.batch_dir:
        for fn in sorted(os.listdir(os.path.join(bd, "profiles"))):
            if not fn.endswith(".json"):
                continue
            b = json.load(open(os.path.join(bd, "profiles", fn), encoding="utf-8"))
            for s in b.get("sources") or []:
                urls.append(s["canonical_url"])
                where[s["canonical_url"]].add(b["entity"]["key"])
    urls = list(dict.fromkeys(urls))
    print(f"checking {len(urls)} URLs with 8 workers …")

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for url, status, err in ex.map(check, urls):
            results.append({"url": url, "status": status, "error": err,
                            "cited_by": sorted(where[url])})
            if status != 200:
                print(f"  [{status or err}] {url[:100]}")

    by = collections.Counter("ok" if r["status"] == 200 else
                             ("http-error" if r["status"] else "network-error")
                             for r in results)
    out = {
        "wave": "C-6/G14 link-health wave 1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url_count": len(results),
        "summary": dict(by),
        "policy": ("dead URLs are flagged on the source record; affected claims "
                   "downgrade to archived-citation status — never deleted silently"),
        "results": sorted(results, key=lambda r: (r["status"] is None,
                                                  r["status"] or 0, r["url"])),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wave complete: {dict(by)} -> {args.out}")


if __name__ == "__main__":
    main()
