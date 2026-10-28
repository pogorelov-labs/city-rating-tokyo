# Traefik access logs → Loki: request-level traffic visibility

CRTKY-127. Runbook, reference configuration, and offline verification, 2026-10-28.
No host access was available for this change: nothing below was applied to the
production host, and every step that needs the host is marked **owner**.

## Scope and what this does not decide

- Ticket acceptance: (1) a LogQL query returns request counts for the
  city-rating host; (2) station-page vs homepage split is visible;
  (3) retention is stated, not assumed.
- Product analytics is **not** the goal and is already covered: Umami has
  counted page views since launch, and the 2026-09-30 checkpoint used it to
  answer the original D4 question (traffic ≈ zero, zeros are real). Access
  logs add the request-level view Umami structurally cannot see: every router
  and host on the shared proxy, status classes, latency, crawlers and no-JS
  clients, redirect hops. Both views are complements, not alternatives.
- Measured 2026-09-30 (checkpoint `research/decisions/2026-09-30-epic80-checkpoint.md`):
  docker container logs are already in Loki (label `container`, not
  `job`/`service_name` — the 2026-08-25 "only varlogs" reading was a query
  artifact); Traefik access logs are **not enabled at all** (no `--accesslog`
  in the `coolify-proxy` args), so the promtail drop rule waiting for them
  (`vps_infra`) is dead code until they exist.
- Enabling access logs restarts the **shared proxy for every site on the
  host** — an interruption of a few seconds. That is the single disruptive
  step; the owner picks the moment.

## What ships in this repo

`infra/observability/` — reference configuration, verified offline (below):

| File | Role |
|------|------|
| `coolify-proxy-accesslog-args.yml` | Proxy command args that turn on JSON access logging |
| `promtail-traefik.yml` | Promtail `traefik-access` scrape job (the additive host change) |
| `loki-config.yml` | Reference Loki config with the current 5d retention made explicit |
| `docker-compose.yml` | Reference stack for a fresh host (not applied anywhere now) |
| `logql-queries.md` | Verified queries: counts/rate, p95, 4xx/5xx by host, station/home split |

## Rollout order (owner actions; not executed)

1. **Owner — discovery on the host** (read-only, no restarts):

   ```sh
   docker inspect coolify-proxy --format '{{json .Config.Args}} {{json .Config.Cmd}}'
   docker inspect coolify-proxy --format '{{json .Mounts}}'
   ls -la /data/coolify/proxy/
   docker ps --format '{{.Names}}' | grep -i -e loki -e promtail
   docker inspect <promtail-container> --format '{{json .Mounts}} {{json .Config.Cmd}}'
   ```

   Confirm: the proxy volume maps `/data/coolify/proxy` ↔ `/traefik` (Coolify's
   documented layout; adjust if an older Coolify differs); where promtail's
   config file lives and which path it can read; the Loki push URL promtail
   already uses (reuse it — do not invent one).

2. **Owner — enable JSON access logs.** In Coolify: Servers → the server →
   Proxy → Configuration, add the args from
   `infra/observability/coolify-proxy-accesslog-args.yml` to the proxy service,
   save. Editing `/data/coolify/proxy/docker-compose.yml` on disk instead is
   overwritten by Coolify's next write of its saved configuration — use the UI.
   Then restart the proxy in the chosen window and verify the file exists and
   grows:

   ```sh
   tail -f /data/coolify/proxy/access.log   # lines are single-line JSON
   ```

3. **Owner — extend promtail.** Copy the `traefik-access` scrape job from
   `infra/observability/promtail-traefik.yml` into the live promtail config
   (the `vps_infra` one), adjusting `__path__` to the path as seen by the
   promtail container and keeping its existing `clients` URL. The old drop
   rule for stdout access logs can stay (harmless: with `filePath` set,
   Traefik writes only the file) or be cleaned up. Restart promtail and check
   its logs for push errors — Loki refuses pushes when its volume is >90% full
   (`ingester.wal.disk_full_threshold`, default 0.9; observed in verification).

4. **Owner — verify with the acceptance queries** from
   `infra/observability/logql-queries.md`, e.g. after a handful of requests:

   ```sh
   export LOKI_ADDR=http://<loki-address>:3100
   logcli query --since=1h 'sum(count_over_time({job="traefik-access"} | json | RequestHost="city-rating.pogorelov.dev" [1h])) or vector(0)'
   ```

   Acceptance is met when (1) the count is non-zero and matches manual
   requests, (2) the station/home split query returns both numbers, and
   (3) everyone reading the numbers knows the window is **5 days** — weekly or
   monthly trends need an explicit retention change (below), not a bigger
   range.

5. **Owner — retention decision (explicit).** Loki keeps 5 days today. A
   longer window means raising `limits_config.retention_period` (and keeping
   the compactor's `retention_enabled`) plus disk headroom for the index and
   chunks; at ~1k requests/day plus ~3k probes/week this is small, but it is
   the owner's call. Nothing in this change assumes a longer window.

## Variants considered

- **A. Promtail tails the access-log file (recommended, verified).** Minimal
  moving parts on a host that already runs promtail; the proxy change is four
  CLI args; queries parse fields at query time with bounded cardinality.
- **B. Traefik native OTLP export → Loki's OTLP endpoint (works, not
  recommended).** Verified end-to-end locally (`experimental.otlpLogs: true` +
  `accessLog.otlp.http.endpoint` → Loki `/otlp/v1/logs`), but with default
  Loki settings every access-log attribute — `RequestPath`, `ClientHost`,
  even `Duration` — becomes a **stream label**: unbounded cardinality that
  exhausts Loki's stream limits under real traffic. Making it safe needs
  `limits_config.otlp_config` attribute filtering, and the exporter is
  experimental upstream. Traefik v3.x has no native "Loki output" for access
  logs as of v3.7 — file/stdout/OTLP are the only outputs.

## Ops notes

- **Rotation:** Traefik never rotates `access.log`. At current traffic
  (checkpoint: ~2.9k blackbox-probe requests/week + ~1k other requests/day)
  JSON lines are on the order of 1–2 MB/day; check with `du` after a week. If
  it needs bounding, use logrotate with `copytruncate` or a USR1 signal
  (`docker kill --signal=USR1 coolify-proxy` makes Traefik reopen the file)
  and keep promtail reading the active path.
- **Privacy:** stored fields include the client IP (`ClientHost`) and full
  path with query string (`RequestPath` — external links can carry tokens in
  query parameters). Headers are dropped (no User-Agent / Referer /
  Authorization). Dropping the IP too is one flag
  (`--accesslog.fields.names.ClientHost=drop`) at the cost of abuse diagnosis
  and any future log-based blocking; keeping it is the default here. With 5d
  retention the exposure window is short, and query examples never select the
  IP field.
- **The known HTTP→HTTPS 404 bug** (checkpoint «Попутно»: router
  `http-0-vhtx5…` references a missing `redirect-to-https@docker`
  middleware) will now be visible as a steady 404 stream in these logs. It is
  a separate fix in `vps_infra`, not part of CRTKY-127 — but these queries
  make its volume measurable, which was part of the point.

## Offline verification (2026-10-28, local rig; no production access)

Real components, native binaries on darwin/arm64: **Traefik v3.7.16** with a
file-provider router for `Host(city-rating.pogorelov.dev)`, JSON access log to
file; **promtail v3.5.4** running the shipped scrape job (only `__path__` and
`clients.url` localized); **Loki v3.7.9** with the reference config (5d
retention); a stub backend answering the site's real URL shapes
(`/`, `/ja`, `/ru`, `/station/<slug>`, `/bangkok`, `/methodology`, 404s).
16 deterministic requests plus wrong-Host probes; every query executed through
Loki's HTTP API with expected values asserted.

| Check | Result |
|---|---|
| Request count for host (acceptance 1) | 16/16 exact |
| Station pages all locales (incl. 404 on station path) | 6/6 exact |
| Station pages, 2xx only | 5/5 exact |
| Homepage all locales (incl. `[?]` query-string tolerance) | 6/6 exact |
| 4xx share for host | 12.5% = 2/16 exact |
| 5xx count (`or vector(0)` form) | explicit 0.0 |
| Request rate, p95 ms (`Duration`/1e6) | positive, plausible |
| Group-by `RequestHost` (incl. wrong-host probes) | exact / ≥1 |
| `RequestPath` keeps query string | confirmed |

Cross-check: 6 home + 6 station + 2 bangkok + 1 methodology + 1 other-404 =
16 = host total. All 11 checks passed.

Verified gotchas are recorded in `infra/observability/logql-queries.md` (the
`\?` escape rejection, empty≠zero, nanosecond durations, hop counting).

Limits of the rig: loopback traffic (latency distribution not representative
of real users), single-tenant unauthenticated Loki, no Coolify present — the
Coolify-specific steps above cite Coolify's current documentation instead and
are the reason discovery is step 1.

Component receipts (SHA-256, darwin/arm64 release artifacts):
`traefik_v3.7.16` `cddf264830889c27afe774dbc1c39559c749a99bc69322ba0073ec0af01ca59d`;
`loki 3.7.9` `48acd15626d60ce357ac094c79d30eb9cc8be150b3b97e1360762506c3cd05a8`;
`logcli 3.7.9` `6e7b60e0d3a7883c59bf82909bc4d934739144211702050a1bf33d1f2b2e9bec`;
`promtail 3.5.4` `19b7c5a7a889fdc2b031fa8e799759c0ed962f375c2f11d0dbedcb83db5966fa`.

## Rollback

- Remove the added args in Coolify Proxy → Configuration and restart the
  proxy: access logging stops, routing is unaffected.
- Remove the `traefik-access` scrape job from promtail (or leave it idle — no
  file, no lines) and restart promtail.
- Already-stored entries age out after 5 days; no schema or data migration is
  involved anywhere.

## Consistency with repo docs

- No CHANGELOG entry: infrastructure-only change, invisible to users of the
  published site (public release copy rules — `docs/RELEASING.md`).
- `CLAUDE.md` Key Files gained one row for `infra/observability/`.
- Nothing here publishes host secrets: tool names, Coolify's documented paths,
  and the already-public domain only.
