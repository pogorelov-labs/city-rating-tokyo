"""Tokyo source vintage and integrity checks; no network or scoring policy."""
import json
from datetime import date, datetime, timezone


# Preserve the documented existing coverage, allowing its small OSM gaps.
MIN_COVERAGE = {"hotpepper": 1.0, "osm_pois": .93,
                "osm_extended": .97, "osm_livability": 1.0}
HP_FIELDS = ("total_count", "izakaya_count", "bar_count", "cafe_count", "midnight_count")


def scraped_date(value):
    """Unknown is never today's date. Accept source dates and ISO timestamps."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo:
            stamp = stamp.astimezone(timezone.utc)
        return stamp.date().isoformat()
    except ValueError:
        return None


def station_dates(slug, tables):
    return {name: scraped_date(rows.get(slug, {}).get("scraped_at"))
            for name, rows in tables.items()}


def encode_dates(dates):
    return json.dumps(dates, separators=(",", ":"), sort_keys=True)


def decode_dates(value):
    """Read additive source_dates metadata. Legacy rows have no map."""
    if value is None or value == "":
        return {}
    dates = json.loads(value) if isinstance(value, str) else value
    if not isinstance(dates, dict) or set(dates) != set(MIN_COVERAGE):
        raise ValueError("Incomplete source-date metadata")
    for stamp in dates.values():
        if stamp is not None and scraped_date(stamp) != stamp:
            raise ValueError("Malformed source date")
    return dates


def conservative_month(dates, legacy=None):
    """Oldest observed source month; unknown input cannot claim freshness."""
    if dates:
        return min(dates.values())[:7] if all(dates.values()) else "unknown"
    if isinstance(legacy, str) and len(legacy) == 7:
        date.fromisoformat(legacy + "-01")
        return legacy
    return "unknown"


def check_sources(slugs, tables, max_age_days, today=None):
    """Fail closed on incomplete/stale input. An explicit age policy is required."""
    if not isinstance(max_age_days, int) or max_age_days < 1:
        raise ValueError("Set a positive --max-source-age-days (owner freshness policy)")
    today = today or date.today()
    expected = set(slugs)
    if not expected:
        raise ValueError("Empty station population")
    errors, summary = [], {}
    for name, minimum in MIN_COVERAGE.items():
        rows = tables.get(name, {})
        covered = expected & rows.keys()
        invalid, stale, future = [], [], []
        for slug in sorted(covered):
            stamp = scraped_date(rows[slug].get("scraped_at"))
            if stamp is None:
                invalid.append(slug)
            else:
                age = (today - date.fromisoformat(stamp)).days
                if age > max_age_days:
                    stale.append(slug)
                if age < 0:
                    future.append(slug)
        summary[name] = {"rows": len(covered), "expected": len(expected),
                         "stale": len(stale), "unknown_date": len(invalid), "future": len(future)}
        if len(covered) / len(expected) < minimum:
            errors.append(f"{name}: incomplete coverage {len(covered)}/{len(expected)} < {minimum:.0%}")
        for reason, values in (("stale", stale), ("unknown date", invalid), ("future date", future)):
            if values:
                errors.append(f"{name}: {len(values)} {reason} rows (e.g. {', '.join(values[:3])})")
    hp = tables.get("hotpepper", {})
    incomplete = [s for s in expected & hp.keys() if any(
        not isinstance(hp[s].get(f), (int, float)) or isinstance(hp[s].get(f), bool)
        or hp[s][f] < 0 or not float(hp[s][f]).is_integer() for f in HP_FIELDS)]
    if incomplete:
        errors.append(f"hotpepper: {len(incomplete)} incomplete count rows (including midnight)")
    for name, field in (("hotpepper", "total_count"), ("osm_pois", "food_count")):
        positive = sum(isinstance(r.get(field), (int, float)) and r[field] > 0
                       for s, r in tables.get(name, {}).items() if s in expected)
        summary[name]["food_positive"] = positive
        if not positive:
            errors.append(f"{name}: empty food source mix (all zero or absent)")
    if errors:
        raise ValueError("Source canary failed:\n  " + "\n  ".join(errors))
    return summary


def check_source_mix(candidate, previous, max_loss=.05):
    """Guard a >5% loss of source-bearing rows, without changing confidence rules."""
    def counts(rows):
        result = {}
        for row in rows:
            sources = row.get("sources") or {}
            sources = json.loads(sources) if isinstance(sources, str) else sources
            for category, names in sources.items():
                for name in set(names):
                    if name.startswith(("hotpepper", "osm")):
                        key = (category, name)
                        result[key] = result.get(key, 0) + 1
        return result
    before, after = counts(previous), counts(candidate)
    losses = [f"{cat}/{source}: {n} -> {after.get((cat, source), 0)}"
              for (cat, source), n in sorted(before.items())
              if after.get((cat, source), 0) < n * (1 - max_loss)]
    if losses:
        raise ValueError("Source-mix canary failed (>5% loss): " + "; ".join(losses))
