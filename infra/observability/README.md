# Observability: Traefik access logs → Loki (CRTKY-127)

Reusable pieces for shipping the shared Traefik proxy's access logs into Loki,
so request-level traffic for `city-rating.pogorelov.dev` (and every other host
on the same proxy) is queryable with LogQL. Motivation, owner runbook, and
verification evidence: [`research/notes/2026-10-28-traefik-loki-access-logs-runbook.md`](../../research/notes/2026-10-28-traefik-loki-access-logs-runbook.md).

The production host already runs Loki + promtail (5-day retention). These files
are **reference configuration**: the host applies the additive promtail job and
the proxy args, not this whole stack. Do not blind-apply over a live setup.

| File | Purpose |
|------|---------|
| `loki-config.yml` | Single-node Loki with explicit 5d retention (matches the host). For reproducing the stack on a fresh host. |
| `promtail-traefik.yml` | Promtail config with the `traefik-access` scrape job — the actual additive change for the host's existing promtail. |
| `docker-compose.yml` | Reference stack (Loki + promtail) wiring the two configs together. |
| `coolify-proxy-accesslog-args.yml` | `coolify-proxy` command args that enable JSON access logging via the Coolify proxy configuration. |
| `logql-queries.md` | Verified LogQL queries: request counts/rate per host, p95 latency, 4xx/5xx share by host, station-vs-homepage split. |

Verified offline 2026-10-28 against real components — Traefik v3.7.16,
Loki v3.7.9, promtail v3.5.4 (final promtail release line; upstream is EOL,
successor is Grafana Alloy) — details and SHA-256 receipts in the runbook.

This repository is public: files here contain no credentials and no
non-public host details beyond tool names and Coolify's documented paths.
