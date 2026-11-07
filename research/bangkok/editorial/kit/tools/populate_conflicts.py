#!/usr/bin/env python3
"""B-13: populate structured claim-to-claim conflict links (handoff rule:
every claim carries its conflicts).

The corpus review (2026-11-08) found that almost all conflicts in these
batches are *source-level* and live inside single claims (limitations +
`conflicted` status) — the structured link field applies where two claims in
one bundle contradict each other, which reviewer passes detected exactly once:
wat-mangkon-c06's Yaowarat/Chinatown≈Samphanthawong framing conflicts with the
venue-level khet facts in c02 (station straddles two khets) and c04 (temple
attributed to Pom Prap Sattru Phai) — the bundle's own limitation names them.

Links are explicit here (reviewer-derived, not heuristic), union-merged, and
idempotent. kit/validate.py and kit/audit.py check link integrity.

Run: python3 -I populate_conflicts.py --batch-dir <dir> [...]
"""
import argparse
import json
import os

# entity key -> {claim_id: [conflicting claim ids in the same bundle]}
LINKS = {
    "st.wat-mangkon": {"wat-mangkon-c06": ["wat-mangkon-c02", "wat-mangkon-c04"]},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    args = ap.parse_args()
    applied = 0
    for bd in args.batch_dir:
        for fn in sorted(os.listdir(os.path.join(bd, "profiles"))):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(bd, "profiles", fn)
            bundle = json.load(open(path, encoding="utf-8"))
            ent = bundle["entity"]["key"]
            if ent not in LINKS:
                continue
            claims = {c["id"]: c for c in bundle["claims"]}
            for cid, targets in LINKS[ent].items():
                if cid not in claims:
                    raise SystemExit(f"{ent}: link source {cid} not found")
                c = claims[cid]
                merged = sorted(set(c.get("conflicts_with") or []) | set(targets))
                for t in merged:
                    if t not in claims:
                        raise SystemExit(f"{ent}: dangling link {t} on {cid}")
                if merged != c.get("conflicts_with"):
                    c["conflicts_with"] = merged
                    applied += 1
                    print(f"{ent}: {cid} -> conflicts_with {merged}")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bundle, f, ensure_ascii=False, indent=1)
    print(f"applied {applied} link update(s); idempotent on re-run")


if __name__ == "__main__":
    main()
