"""Canonical publisher-family mapping for corroboration independence (B-10/G21).

`publisher_family` strings drifted across batches: language editions of
Wikipedia ("English Wikipedia", "Wikipedia (TH)", "Wikimedia (Wikipedia EN)"),
OpenStreetMap/Overpass variants, portal casing variants, and agent-generic
buckets. Corroboration counts *independent publishers* — two language editions
of the same encyclopedia (Thai Wikipedia routinely translates English
Wikipedia), or two query APIs over the same OSM database, are not independent
evidence. `canon_family()` maps a raw family string onto a canonical publisher
identity; assemble.py and audit.py both compute corroboration through it so
labels and re-audits agree.

Rules (first match wins; case-insensitive; "^" prefix = startswith):
1. Wikimedia Foundation projects (wikipedia / wikimedia / wikivoyage /
   wikidata) -> "wikimedia" — same publisher.
2. OpenStreetMap + Overpass -> "openstreetmap" — Overpass is a query API
   over the same database.
3. Google products -> "google".
4. Named-publisher variant merges (Time Out, Thai PBS, BK Magazine, Nation
   Group, One Bangkok, Condoreviews Thailand, FazWaz, HipFlat, DDproperty/
   PropertyGuru, PropertyScout, Tripadvisor, Bangkok Post, Michelin,
   Central Group, The Standard, Thairath).
5. Everything else is returned unchanged. Agent-generic buckets
   ("news-media", "real_estate_portal", "transit-operator", "user-generated",
   "lifestyle_blog", "personal_blog", "specialist-media") are NEVER merged
   with named publishers — the mapping would be speculative.

Measured effect on this corpus (2026-11-08, deterministic rerun): 23 of 422
corroborated claims relabel to proposed (422 -> 399). The deep review's
in-session estimate of 27 used an unrecorded broader mapping; the rule set
here is authoritative and reproducible (see
2026-11-08-canonical-relabel-log.jsonl).
"""

# (canonical, needles); "^" = startswith instead of substring
ORG_RULES = [
    ("wikimedia", ("wikipedia", "wikimedia", "wikivoyage", "wikidata")),
    ("openstreetmap", ("openstreetmap", "overpass", "osm-overpass")),
    ("google", ("google",)),
    ("time-out", ("timeout", "time out")),
    ("thai-pbs", ("thaipbs", "thai pbs", "thai_public_broadcast")),
    ("bk-magazine", ("bkmag", "bk magazine")),
    ("nation-group", ("^nation",)),
    ("onebangkok", ("onebangkok",)),
    ("condo-reviews", ("condoreview",)),
    ("fazwaz", ("fazwaz",)),
    ("hipflat", ("hipflat",)),
    ("propertyguru-group", ("ddproperty", "propertyguru")),
    ("property-scout", ("propertyscout",)),
    ("tripadvisor", ("tripadvisor",)),
    ("bangkok-post", ("bangkok post", "bangkokpost")),
    ("michelin", ("michelin",)),
    ("central-group", ("central_group", "central group")),
    ("the-standard", ("the_standard", "the standard")),
    ("thairath", ("thairath",)),
]


def canon_family(raw):
    """Map a raw publisher_family string to its canonical publisher identity."""
    s = (raw or "").strip().lower()
    if not s:
        return raw
    for out, needles in ORG_RULES:
        for n in needles:
            if n.startswith("^"):
                if s.startswith(n[1:]):
                    return out
            elif n in s:
                return out
    return raw.strip() if isinstance(raw, str) else raw


def canon_families(families):
    """Canonical family set for an iterable of raw family strings."""
    return {canon_family(f) for f in families}
