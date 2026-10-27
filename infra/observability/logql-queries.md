# LogQL queries for Traefik access logs (CRTKY-127)

Every query below was executed against a real Loki v3.7.9 ingesting real
Traefik v3.7.16 JSON access lines via the promtail job in
[`promtail-traefik.yml`](promtail-traefik.yml); expected numbers were asserted
against a deterministic request set (runbook §Offline verification). The
selector assumes the job label `traefik-access` and filters fields with
`| json` at query time — ingest keeps only low-cardinality labels by design.

Replace `city-rating.pogorelov.dev` with the host you care about. With the
current Loki retention (**5 days**), the largest usable range is `[5d]`;
prefer `[24h]`/`[1h]` and step down to shorter windows as traffic grows.

## 1. Request counts per host (acceptance #1)

```logql
# Total requests for the site, last 24h
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [24h])) or vector(0)

# All hosts through the shared proxy, ranked (scanner Host headers included)
topk(10, sum by (RequestHost) (count_over_time({job="traefik-access"} | json [24h])))
```

## 2. Request rate (req/s)

```logql
sum(rate({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [5m]))
```

## 3. p95 latency

```logql
# Duration is nanoseconds in Traefik JSON logs → divide to ms
quantile_over_time(0.95, {job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | unwrap Duration [5m]) / 1000000
```

`Duration` includes origin (backend) time; `Overhead` is the Traefik-only part
(also nanoseconds). For a static site behind the proxy, `Duration` is the
client-perceived total.

## 4. 4xx / 5xx share by host

```logql
# Share of 4xx, last 24h, in percent
100 * sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | DownstreamStatus=~"4.." [24h]))
    / sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [24h]))

# Same for 5xx (or vector(0) makes "no errors" an explicit zero)
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | DownstreamStatus=~"5.." [24h])) or vector(0)

# Per-host error volumes, one line per status class
sum by (RequestHost) (count_over_time({job="traefik-access"} | json | DownstreamStatus=~"4.." [24h]))
sum by (RequestHost) (count_over_time({job="traefik-access"} | json | DownstreamStatus=~"5.." [24h]))
```

`DownstreamStatus` is what the client received (after middleware/redirects);
`OriginStatus` is the backend's status.

## 5. Station-page vs homepage split (acceptance #2)

Site URL shapes: homepage `/`, `/ja`, `/ru` (EN default has no prefix);
station pages `/station/<slug>` and `/ja|/ru/station/<slug>`.

```logql
# Station pages, all locales — includes 404s on station paths
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | RequestPath=~"(/ja|/ru)?/station/.*" [24h]))

# Station pages, successful responses only
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | RequestPath=~"(/ja|/ru)?/station/.*" | DownstreamStatus=~"2.." [24h]))

# Homepage (all locales), tolerating query strings: [?] matches a literal '?'
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | RequestPath=~"(/ja|/ru)?/?([?].*)?" [24h]))

# Other sections by the same pattern, e.g. Bangkok and methodology
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | RequestPath=~"(/ja|/ru)?/bangkok" [24h]))
sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" | RequestPath=~"(/ja|/ru)?/methodology" [24h]))

# Top paths for the host
topk(10, sum by (RequestPath) (count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [24h])))
```

## 6. Traffic that never reaches the site (wrong hosts, scanners)

```logql
sum by (RequestHost) (count_over_time({job="traefik-access"} | json | RequestHost!="city-rating.pogorelov.dev" [24h]))
```

## Running them

With logcli on the host (or over SSH port-forward):

```sh
export LOKI_ADDR=http://127.0.0.1:3100   # or the internal Loki address
logcli query --since=24h 'sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [24h])) or vector(0)'
```

Or in Grafana Explore with the Loki datasource, if a Grafana is deployed.

## Verified gotchas

Each of these was hit and confirmed during offline verification, not copied
from blog posts:

- **`\?` inside double-quoted LogQL strings is rejected** (HTTP 400: invalid
  escape) — and a bare `?` is a regex quantifier. Match a literal `?` with a
  character class `[?]` (used above) or backtick raw strings.
- **Empty result ≠ zero.** Metric queries return no series when nothing
  matched; append `or vector(0)` when an explicit zero matters (dashboards).
- **`RequestPath` keeps the query string** (`/station/x?ref=1`), so homepage
  regexes must tolerate `([?].*)?` and path regexes end with `.*`.
- **Access logs count request hops, not page views.** Every redirect
  (HTTP→HTTPS, trailing-slash) is its own line. Page-view analytics stays
  Umami's job; these queries are the request-level/ops view, including
  crawlers and no-JS clients Umami never sees.
- **`Duration` and `Overhead` are nanoseconds** (float-safe to unwrap);
  divide by 1e6 for milliseconds.
- Ranges are capped by the **5-day** retention; longer trends need an owner
  decision on retention, not a bigger `[range]`.
