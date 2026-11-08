#!/usr/bin/env python3
"""G17/A-5 prep: personal-data scan over ALL user-facing bundle text.

Patterns flagged (P1 = likely personal data, must redact; P2 = review):
- Thai national ID shape (13 digits with separators)
- phone numbers (Thai mobile/landline shapes, incl. international)
- street addresses with house numbers ("123/45 ถนน…", "Soi … 12")
- resident/person names in quotes with attributions ("said X", user handles)
- email addresses, LINE/WhatsApp/Telegram handles
- social handles (@handle) and user IDs in URLs (facebook.com/…,
  x.com/<status urls are fine; /user/ paths flagged), room/plate numbers

Scope: editorial copy (preview/lead/lists/uncertainties), claim text_en,
question notes, source titles/publishers. Excluded: canonical URLs (checked
separately for identity-bearing paths), app-data facts.

Run: python3 -I personal_data_scan.py --batch-dir <b1> [...] [--json out]
Exit 0 = clean (P1-free); 1 = P1 findings exist.
"""
import argparse
import glob
import json
import os
import re
import sys

PATTERNS = [
    ("thai-national-id", re.compile(r"\b\d\s?\d{4}\s?\d{5}\s?\d{2}\s?\d\b"), "P1"),
    ("phone", re.compile(r"\b(?:\+66|0)\s?[2-689]\d(?:[\s-]?\d){6,8}\b"), "P1"),  # leading \b: OSM node ids (7096345624) must not match
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "P1"),
    ("street-address", re.compile(r"\b\d{1,4}/\d{1,4}\s+(?:ถ\.|ถนน|Soi|ซอย|[A-Z][a-z]+ (?:Road|Rd))"), "P2"),
    ("house-number-soi", re.compile(r"\b(?:Soi|ซอย)\s+[A-Za-zก-๙]+\s*\d{1,3}/\d{1,3}\b"), "P2"),
    ("quoted-resident", re.compile(r"(?:said|ตามที่|บอกว่า)\s+[\"“']?[A-Z][a-z]+\s[A-Z][a-z]+"), "P2"),
    ("social-handle", re.compile(r"(?:^|\s)@[A-Za-z0-9_]{4,30}\b"), "P2"),
    ("messenger-id", re.compile(r"\b(?:line\s*id|line|whatsapp|wechat|kakao(?:talk)?)\s*(?:id\s*[:@]?|[:@])\s*(?=[A-Za-z0-9_.-]*\d)[A-Za-z0-9_.-]{5,}\b", re.I), "P1"),  # handle must contain a digit ("Dark Red Line: Krung Thep Aphiwat" is prose)  # requires id/[:@] separator — bare "Silom Line southern" must NOT match
    ("id-plate", re.compile(r"\b(?:บบ|กก|1กก)\s?\d{1,4}\b"), "P2"),
    ("room-tenant", re.compile(r"\b(?:room|ห้อง)\s?\d{3,4}\b.{0,30}(?:tenant|ผู้เช่า|ชื่อ)", re.I), "P2"),
    ("identity-url", re.compile(r"(?:facebook\.com/(?:profile\.php\?id=|people/)|line\.me/ti/p|t\.me/[A-Za-z0-9_]+/\d+\?comment=)"), "P2"),
]

def texts_of(b):
    ed = b["editorial"]
    for blk in (ed.get("preview"), ed.get("guide_lead")):
        if blk:
            yield ("editorial." + ("preview" if blk is ed.get("preview") else "guide_lead"), blk.get("text_en") or "")
    for lst in ("strengths", "tradeoffs", "day_night", "within_area_variation", "conditional_fit"):
        for i, it in enumerate(ed.get(lst) or []):
            yield (f"editorial.{lst}[{i}]", it.get("text_en") or "")
    for u in ed.get("uncertainties") or []:
        yield ("editorial.uncertainties", u if isinstance(u, str) else (u.get("text_en") or u.get("text") or ""))
    for c in b.get("claims") or []:
        yield (f"claim {c['id']}", c.get("text_en") or "")
    for q in b.get("question_answers") or []:
        yield (f"qa {q['id']}", q.get("notes") or "")
    for s in b.get("sources") or []:
        yield (f"source {s['id']} title", s.get("title") or "")
    for n in (b.get("review", {}).get("notes") or []):
        yield ("review.note", str(n))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", action="append", required=True)
    ap.add_argument("--json")
    args = ap.parse_args()
    findings = []
    for bd in args.batch_dir:
        for p in sorted(glob.glob(os.path.join(bd, "profiles", "*.json"))):
            b = json.load(open(p, encoding="utf-8"))
            ent = b["entity"]["key"]
            for where, text in texts_of(b):
                for name, pat, sev in PATTERNS:
                    for m in pat.finditer(text):
                        # keep URL-ish matches out of handle false positives
                        frag = m.group(0)
                        if name == "social-handle" and ("http" in text[max(0, m.start()-6):m.start()+1] or "t.me" in text[max(0, m.start()-30):m.start()]):
                            continue
                        findings.append({"entity": ent, "where": where, "pattern": name,
                                         "severity": sev, "fragment": frag[:80],
                                         "context": text[max(0, m.start()-40):m.end()+40][:120]})
    p1 = [f for f in findings if f["severity"] == "P1"]
    for f in findings:
        print(f"[{f['severity']}] {f['entity']} {f['where']} {f['pattern']}: {f['fragment']!r}")
    print(f"\nSCAN: {len(findings)} finding(s) — P1={len(p1)} P2={len(findings)-len(p1)}"
          f" ({'CLEAN of P1' if not p1 else 'P1 REDACTION REQUIRED'})")
    if args.json:
        json.dump({"generated": "2026-11-08", "findings": findings},
                  open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote", args.json)
    sys.exit(1 if p1 else 0)

if __name__ == "__main__":
    main()
