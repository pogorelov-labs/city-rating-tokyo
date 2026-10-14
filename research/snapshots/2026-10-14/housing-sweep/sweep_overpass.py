#!/usr/bin/env python3
"""Bangkok housing sweep — per-khet Overpass area() counts, remaining 46 khets.

Method per research/bangkok/notes/2026-10-13-housing-crtky148.md section 2:
one request per khet, seven `out count` blocks in order
(apartments, residential, dormitory, commercial, mixed_use, towers>=20, stations).
area id = 3600000000 + relation_id, computed as an integer (note's trap 1.1).
Counts parsed as ints (note's trap 1.1: Overpass count tags arrive as strings).
POST requires a User-Agent (note: 406 without one).
Retries: mirror round-robin per khet, rounds with backoff on 504/timeout.
Quadrant order NW, NE, SW, SE around bbox midpoint (13.72315, 100.6331).
Resumable: results.json holds per-khet rows; finished khets are skipped.
"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)

MIRRORS = [
    "overpass-api.de",               # main instance, freshest snapshot
    "maps.mail.ru/osm/tools/overpass",  # second live mirror 2026-10-14
    "overpass.kumi.systems",
    "overpass.private.coffee",
    "overpass.monicz.dev",
]
# per-attempt client timeout: live mirrors get room, known-hanging ones fail fast
TMO = {"overpass-api.de": 80, "maps.mail.ru/osm/tools/overpass": 80}
UA = "city-rating-research/1.0 (Bangkok housing sweep; contact: dev@pogorelov.labs)"
BBOX = "13.4907,100.3279,13.9556,100.9383"
MID_LAT, MID_LON = 13.72315, 100.6331

# repo canonical khets (data/bangkok/signals.json districts keys) -> OSM name:en
SLUGS = [
    "bang-bon", "bang-kapi", "bang-khae", "bang-khen", "bang-kho-laem",
    "bang-khun-thian", "bang-na", "bang-phlat", "bang-rak", "bang-sue",
    "bangkok-noi", "bangkok-yai", "bueng-kum", "chatuchak", "chom-thong",
    "din-daeng", "don-mueang", "dusit", "huai-khwang", "khan-na-yao",
    "khlong-sam-wa", "khlong-san", "khlong-toei", "lak-si", "lat-krabang",
    "lat-phrao", "min-buri", "nong-chok", "nong-khaem", "pathum-wan",
    "phasi-charoen", "phaya-thai", "phra-khanong", "phra-nakhon",
    "pom-prap-sattru-phai", "prawet", "rat-burana", "ratchathewi", "sai-mai",
    "samphanthawong", "saphan-sung", "sathon", "suan-luang", "taling-chan",
    "thawi-watthana", "thon-buri", "thung-khru", "wang-thonglang", "watthana",
    "yan-nawa",
]
# special case: repo slug "watthana" = OSM "Vadhana" (Khet Vadhana, rel 2938036)
ALIAS = {"watthana": "Vadhana"}
DONE = {"watthana", "bang-na", "khlong-toei", "huai-khwang"}  # counted 2026-10-13, note §2

TOWERS_RE = "^([2-9][0-9]|[1-9][0-9]{2,})$"  # building:levels >= 20, no 10-19 band
STATIONS_RE = "^(subway|light_rail|monorail)$"

LOG = open(HERE / "run.log", "a", encoding="utf-8")


def log(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def post(mirror, query, tmo=80):
    """POST one query. Returns parsed json body. Raises on failure."""
    url = f"https://{mirror}/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode()
    for _ in range(2):  # one manual 307-follow hop (monicz adds trailing slash)
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=tmo) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 307:
                loc = e.headers.get("Location")
                if loc:
                    url = loc if loc.startswith("http") else f"https://{mirror}{loc}"
                    continue
            raise
    raise RuntimeError("redirect loop")


def load_khets():
    reg = json.loads((RAW / "registry.json").read_text())
    khets = {}
    for e in reg["elements"]:
        t = e["tags"]
        en = (t.get("name:en") or "").replace(" District", "").strip()
        slug = None
        for s in SLUGS:
            if en.casefold() == ALIAS.get(s, s.replace("-", " ")).casefold():
                slug = s
                break
        if slug:
            c = e["center"]
            q = ("N" if c["lat"] >= MID_LAT else "S") + ("E" if c["lon"] >= MID_LON else "W")
            khets[slug] = {"rel_id": e["id"], "osm_name_en": en, "quadrant": q,
                           "center": (round(c["lat"], 5), round(c["lon"], 5))}
    missing = [s for s in SLUGS if s not in khets]
    if missing:
        raise SystemExit(f"registry mapping incomplete, unmatched slugs: {missing}")
    assert len(khets) == 50, f"expected 50 khets, got {len(khets)}"
    return khets


def khet_query(rel_id):
    rid = 3600000000 + int(rel_id)  # integer arithmetic, note trap 1.1
    b = lambda tag: (f'(way["building"="{tag}"](area.a);'
                     f'relation["building"="{tag}"](area.a););out count;')
    return (
        "[out:json][timeout:60];\n"
        f"area({rid})->.a;\n"
        + b("apartments") + "\n"
        + b("residential") + "\n"
        + b("dormitory") + "\n"
        + b("commercial") + "\n"
        + b("mixed_use") + "\n"
        + f'(way["building"]["building:levels"~"{TOWERS_RE}"](area.a);'
          f'relation["building"]["building:levels"~"{TOWERS_RE}"](area.a););out count;\n'
        + f'(node["railway"="station"]["station"~"{STATIONS_RE}"](area.a);'
          f'way["railway"="station"]["station"~"{STATIONS_RE}"](area.a););out count;'
    )


def parse_counts(body):
    els = [e for e in body.get("elements", []) if e.get("type") == "count"]
    if len(els) != 7:
        raise ValueError(f"expected 7 count blocks, got {len(els)}")
    vals = []
    for e in els:
        t = e["tags"]
        vals.append(int(t.get("ways", 0)) + int(t.get("relations", 0))
                    + int(t.get("nodes", 0)))
    apartments, residential, dormitory, commercial, mixed_use, towers, stations = vals
    # sanity guards vs city-wide June inventory (note section 1.3) plus growth slack
    caps = (12000, 50000, 2000, 20000, 100, 3000, 300)
    for name, v, c in zip(["apartments", "residential", "dormitory", "commercial",
                           "mixed_use", "towers", "stations"], vals, caps):
        if v > c:
            raise ValueError(f"sanity: {name}={v} exceeds cap {c}")
    return dict(apartments=apartments, residential=residential, dormitory=dormitory,
                commercial=commercial, mixed_use=mixed_use, towers_20plus=towers,
                stations_in_khet=stations)


def main():
    khets = load_khets()
    log(f"registry ok: 50 khets mapped, snapshot={json.loads((RAW/'registry.json').read_text())['osm3s']['timestamp_osm_base']}")
    todo = [s for s in SLUGS if s not in DONE]
    results_path = HERE / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}

    order = sorted(todo, key=lambda s: ("NW", "NE", "SW", "SE").index(khets[s]["quadrant"]))
    log(f"todo {len(todo)} khets, order: " + " ".join(order))

    mirror_idx = 0  # overpass-api.de first: freshest snapshot
    max_rounds = 40
    for slug in order:
        if slug in results:
            continue
        info = khets[slug]
        q = khet_query(info["rel_id"])
        got = False
        for rnd in range(max_rounds):
            for k in range(len(MIRRORS)):
                m = MIRRORS[k]
                try:
                    t0 = time.time()
                    body = post(m, q, TMO.get(m, 25))
                    dt = time.time() - t0
                    counts = parse_counts(body)
                    stamp = body.get("osm3s", {}).get("timestamp_osm_base", "?")
                    (RAW / f"{slug}.json").write_text(json.dumps(body, ensure_ascii=False))
                    results[slug] = {**counts, "rel_id": info["rel_id"],
                                     "osm_name_en": info["osm_name_en"],
                                     "quadrant": info["quadrant"],
                                     "snapshot": stamp, "mirror": m}
                    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=1))
                    log(f"OK {slug} ({info['quadrant']}) {m} {dt:.1f}s snapshot={stamp} {counts}")
                    got = True
                    break
                except urllib.error.HTTPError as e:
                    log(f"RETRY {slug} {m} http={e.code}")
                except Exception as e:
                    log(f"RETRY {slug} {m} {type(e).__name__}: {str(e)[:140]}")
                time.sleep(3)
            if got:
                break
            log(f"-- {slug}: full mirror round {rnd + 1}/{max_rounds} failed, sleep 45s")
            time.sleep(45)
        if not got:
            log(f"GIVEUP {slug} after {max_rounds} rounds")
        time.sleep(30)  # IP-friendly pacing after each success

    log(f"sweep finished: {len(results) + len(DONE)} khets counted in total (incl. 4 from note)")


if __name__ == "__main__":
    main()
