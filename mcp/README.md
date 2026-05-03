# city-rating MCP server

MCP (Model Context Protocol) server exposing the Tokyo city-rating dataset:
1493 stations, 10 ratings each, plus signals (food, nightlife, green, gym,
livability, crime, transit, last train, livecams, environment, ward, lines)
in EN/JA/RU.

Live site: https://city-rating.pogorelov.dev

## Status

| Phase | What ships | State |
|-------|------------|-------|
| 1 — light tools | search / get / compare / list_pois / methodology / list_categories | ✅ |
| 2 — embeddings | semantic_search / find_similar / recommend (multilingual-e5-large, in-memory cosine) | ✅ |
| 3 — auth & deploy | NocoDB-backed API keys + per-key rate limit, site request form, Coolify HTTP service at `city-rating.pogorelov.dev/mcp` (path-based, shares the frontend's domain) | ✅ code, ⏳ deploy |

## Tools

### Light (no model load)

| Tool | What it does |
|------|--------------|
| `search_stations(weights?, min/max rent, min/max commute, category_mins, has_live_camera, hide_flood_risk, hide_high_seismic, locale, limit)` | Top-N by weighted composite under hard filters (mirrors the homepage). |
| `get_station(slug, locale)` | Full profile: ratings, confidence, sources, rent, transit, last train, environment, signals, ward, lines, livecams, multilingual description. |
| `compare_stations(slugs[], locale)` | 2–5 full profiles side by side. |
| `list_pois(slug, category?)` | Per-station signal counts (food / nightlife / green / vibe / gym / essentials). |
| `get_methodology()` | Formulas, confidence levels, source caveats. Quote this when explaining a rating. |
| `list_categories()` | Reference list of rating keys, POI categories, locales, description fields. |

### Heavy (embeddings)

The first heavy call triggers a one-time fastembed model load (~3 s). After
that, queries are ~50 ms (40 ms ONNX inference + 5 ms cosine + overhead).

| Tool | What it does |
|------|--------------|
| `semantic_search(query, locale, field?, limit)` | Free-form text → most-matching stations. `field=None` searches a per-station aggregate; `field='nightlife'` (or atmosphere/landmarks/food) constrains to that one. |
| `find_similar(slug, locale, limit)` | "I like Kichijoji, what else feels like that?" — cosine over the (slug, locale) aggregate vector. |
| `recommend(query, weights?, filters..., hybrid_alpha=0.5, locale, limit)` | Hybrid: semantic top-60 → drop dealbreaker fails → re-rank by `α·cosine + (1-α)·composite/10`. The right tool when a user describes intent AND has hard requirements. |

Default weights and filter ranges match `app/src/lib/types.ts:DEFAULT_WEIGHTS` / `DEFAULT_FILTERS`.

## Embeddings: host volume

The embeddings file (`data/embeddings.npz`, ~80 MB, 22,395 e5-large
vectors) is **not built inside Docker** and **not committed to git**.
It lives on the host as a Coolify persistent volume, bind-mounted into
the container at `/app/data/external/embeddings.npz`.

Why: the encoding step (17,916 texts through e5-large ONNX) took ~110
min on the 2-core VPS — wasteful on every redeploy because the inputs
(`generated-descriptions.json`) only change when the description corpus
is regenerated. Decoupling the artifact from the build cuts a redeploy
from ~2 hours to ~7 min.

### Generating the file

```bash
# One-time on the maintainer's M2 (~19 min wall, faster than VPS).
python3 scripts/build-embeddings.py
ls -lh data/embeddings.npz   # ~80 MB
sha256sum data/embeddings.npz
```

### Coolify configuration (one-time)

In the MCP service (UUID `f4p97un8b5pj9wdbam40bq4u`) → **Persistent Storage** → Add → **Directory mount**:

- **Source directory (host):** `/data/coolify/applications/f4p97un8b5pj9wdbam40bq4u/embeddings`
- **Destination directory (container):** `/app/data/external`

Coolify defaults the host source to `/data/coolify/applications/<uuid>` —
the `/embeddings` suffix keeps the npz in its own subdir so we can drop
sibling artifacts in the future without polluting the root.

### Uploading to the VPS

```bash
APP=f4p97un8b5pj9wdbam40bq4u
ssh root@vps "mkdir -p /data/coolify/applications/$APP/embeddings"
scp data/embeddings.npz root@vps:/data/coolify/applications/$APP/embeddings/
ssh root@vps "sha256sum /data/coolify/applications/$APP/embeddings/embeddings.npz"
```

The `CITY_RATING_EMBEDDINGS=/app/data/external/embeddings.npz` env var
is set in the Dockerfile already — no app config change needed.

If the bind mount is missing or the npz is absent, the container starts
fine (light tools work) but logs a WARN at startup and `semantic_search
/ find_similar / recommend` raise on first call. The startup probe
prints exact paths so misconfig is loud.

### Refreshing embeddings

When `generated-descriptions.json` changes:
1. Regenerate `data/embeddings.npz` locally (`python3 scripts/build-embeddings.py`)
2. scp to the host (overwrites the bind-mount target)
3. Restart the MCP container in Coolify (or `docker restart …`)

No image rebuild needed.

### Model choice

`intfloat/multilingual-e5-large` (1024d, ONNX). Strongest multilingual
encoder fastembed supports — EN/JA/RU all native. e5 family requires
`passage:` prefix on documents and `query:` on queries; both code paths
handle this automatically.

The npz is a flat numpy archive with parallel arrays (`vectors`,
`slugs`, `locales`, `fields`, `model`). The MCP loader splits it into
per-(locale, field) views in O(1) at startup so cosine queries don't
pay a mask cost.

## Run locally (stdio for Claude Desktop / Claude Code)

```bash
# 1. Build the datamart (needs NocoDB token in env or hardcoded fallback)
cd ..  # repo root
python3 scripts/build-datamart.py

# 2. Install MCP deps
cd mcp
pip install -e .

# 3. Smoke-test
python3 -c "from city_rating_mcp.data import Datamart; print(len(Datamart.load()))"
# → 1493

# 4. Run over stdio
city-rating-mcp
```

Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "city-rating": {
      "command": "city-rating-mcp",
      "env": {
        "CITY_RATING_DATAMART": "/abs/path/to/data/station-datamart.json"
      }
    }
  }
}
```

Claude Code (`.claude/settings.json` — workspace level):

```json
{
  "mcpServers": {
    "city-rating": {
      "command": "python3",
      "args": ["-m", "city_rating_mcp.server"],
      "env": {
        "CITY_RATING_DATAMART": "${workspaceFolder}/data/station-datamart.json"
      }
    }
  }
}
```

## Run as HTTP service

```bash
MCP_TRANSPORT=http MCP_PORT=8000 MCP_PATH=/mcp city-rating-mcp
```

Connect with any MCP HTTP client at `http://localhost:8000/mcp`.

## Build the Docker image

The Dockerfile uses **repo root** as build context so it can pull
`scripts/build-datamart.py` + NocoDB data into stage 1.

```bash
cd ..  # repo root
docker build \
    -f mcp/Dockerfile \
    --build-arg NOCODB_API_TOKEN=$NOCODB_API_TOKEN \
    -t city-rating-mcp:latest \
    .

docker run --rm -p 8000:8000 city-rating-mcp:latest
```

## Authentication

Public deploys gate every request on a NocoDB-backed bearer key.

### Request flow

```
user → city-rating.pogorelov.dev/<locale>/api-access  (form)
   → POST /api/api-access (Next.js route)
       → generate `crk_<32 hex>`, hash SHA-256
       → INSERT into NocoDB.api_keys with status='pending'
       → return plaintext key once
user saves key, waits for admin approval
admin flips status → 'active' in NocoDB UI
city-rating.pogorelov.dev/mcp refreshes its key cache every 5 min
client → MCP with `Authorization: Bearer crk_…`  → tool call
```

The MCP only ever sees SHA-256 hashes. Plaintext lives in the user's
notes. Same hash function (Node `crypto.createHash('sha256')` / Python
`hashlib.sha256`) on both sides.

### NocoDB `api_keys` schema

Must be created **manually** in the NocoDB UI — the API token is
data-only so we can't add tables programmatically. Once created, set
`NOCODB_API_KEYS_TABLE_ID` on both the site and the MCP runtime.

| Column | Type | Notes |
|--------|------|-------|
| `Id` | ID (auto, primary) | NocoDB default |
| `key_hash` | SingleLineText (64 chars, unique recommended) | SHA-256 hex of the plaintext key |
| `email` | Email | Required by the form |
| `use_case` | LongText | What the user wrote in the form |
| `status` | SingleSelect (`pending` default, `active`, `revoked`) | Admin flips this |
| `rate_limit_per_min` | Number (default 60) | Per-key limit; tweak per consumer |
| `last_used_at` | DateTime (optional) | Future: written by MCP on each call |
| `notes` | LongText (optional) | Admin scratchpad |
| `created_at` | DateTime | Set by the API route |

**Display field:** `email` (so the admin grid is human-readable).
**Approve workflow:** open the row in NocoDB → set `status` → `active` →
optional: bump `rate_limit_per_min` if you trust the requester.

### Rate limiting

Token bucket per key. Capacity = `rate_limit_per_min`, refill =
`capacity / 60` tokens per second. Over budget → 429 with
`Retry-After: 5`.

In-memory, per-process. Single-instance deploy is fine. If we ever scale
horizontally, move to Redis or accept N×limit (each instance enforces
locally).

## Coolify deploy — shared domain `city-rating.pogorelov.dev/mcp`

The MCP runs as a **second Coolify service on the same domain** as the
Next.js frontend. Traefik routes path prefix `/mcp` to the MCP container,
everything else to Next.js. Two services, one domain, one TLS cert.

```
                    Traefik (Coolify)
                     /            \
PathPrefix(/mcp)/   /              \   default
                   ↓                ↓
            MCP container     Next.js container
        FastMCP @ /mcp        site + /api/api-access
        Healthz @ /mcp/healthz
```

The MCP container's healthz is mounted at `/mcp/healthz` — same prefix
as the transport — so a single Traefik PathPrefix rule covers both. No
healthz on the bare host (it'd be hidden behind Next.js anyway).

### Steps

1. **NocoDB:** create the `api_keys` table per the schema above. Note
   its table ID. (For city-rating-db this is `mzcavs8wz1bgwsb`.)
2. **Site env:** add `NOCODB_API_KEYS_TABLE_ID=<id>` to the existing
   city-rating Coolify service. The site reuses `NOCODB_API_URL` and
   `NOCODB_API_TOKEN` already wired for the feedback form. **Redeploy.**
3. **MCP service in Coolify:**
   - **New resource → Public Repository → `pogorelov-labs/city-rating`**
   - Build pack: **Dockerfile**
   - Dockerfile path: `mcp/Dockerfile`
   - Build context: `.` (repo root, NOT `mcp/`)
   - Build args:
     - `NOCODB_API_TOKEN=<token>` (used by stage 1 to fetch datamart)
   - Runtime env vars:
     - `NOCODB_API_URL=https://nocodb.pogorelov.dev`
     - `NOCODB_API_TOKEN=<token>`
     - `NOCODB_API_KEYS_TABLE_ID=<id>` (from step 1)
     - `MCP_AUTH_REQUIRED=true`
     - `MCP_KEY_REFRESH_SECONDS=300`
   - **Domain:** `city-rating.pogorelov.dev` (same as Next.js)
   - **Path:** `/mcp` — Coolify will generate a Traefik
     `PathPrefix(/mcp)` rule. (In Coolify v4: Settings → Domains →
     enter `https://city-rating.pogorelov.dev/mcp`.)
   - **Priority:** higher than the Next.js service so the path rule wins
     for `/mcp/*`. Coolify auto-orders longer prefixes first; if not,
     add the Traefik label `traefik.http.routers.mcp.priority=100` (or
     anything > the Next.js router's default 10).
   - **Healthcheck path:** `/mcp/healthz` (Traefik will route it to the
     MCP container per the path rule; or use container-level Docker
     healthcheck which is already wired in the Dockerfile).
4. **Auto-deploy** on push to `main` (Coolify GitHub App webhook).

The 15 MB datamart + 81 MB embeddings + ~2.2 GB e5-large model are baked
into the image. Cold start ≈ 4–6 s (model load). Memory footprint ≈
2.5 GB resident — fits the VPS. Refresh: push to `main` → image rebuilds
→ datamart re-fetched, embeddings re-generated from descriptions.

### Smoke-testing the deployed instance

```bash
KEY="crk_…"  # the plaintext key from the site form, after admin approval

# Health (no auth)
curl https://city-rating.pogorelov.dev/mcp/healthz
# → ok

# Without auth → 401
curl -i https://city-rating.pogorelov.dev/mcp

# With key → 200/406 (406 just means GET on a POST endpoint)
curl -i -H "Authorization: Bearer $KEY" https://city-rating.pogorelov.dev/mcp

# Real MCP call: pick your client (Claude Desktop, Claude Code) and
# point it at https://city-rating.pogorelov.dev/mcp with the bearer header.
```

### Why path-based instead of `mcp.pogorelov.dev` subdomain

- **One TLS cert, one DNS record.** Less to keep in sync.
- **`*.pogorelov.dev` cookies, CORS already set.** The `api-access`
  route's origin check covers both same-origin form submissions and any
  future site widget that calls the MCP without leaving the page.
- **Inspectable in DevTools alongside the site.** Same-origin requests
  show up in the Next.js Network panel, no CORS preflights.

If the MCP ever needs to scale independently or end up on a separate VPS,
the move back to a subdomain is a one-line Coolify config change — the
internal MCP path is already `/mcp` either way.

## Architecture (why this shape)

- **Datamart, not NocoDB.** The 10-table join already exists for the
  CRTKY-109 description pipeline. Reusing it gives the MCP a single
  in-memory dict with everything per slug. NocoDB stays the source of
  truth; image rebuild re-snapshots it.
- **Static + push-deployed.** Tokyo doesn't change minute-to-minute. A
  monthly rebuild is plenty fresh. No DB queries on hot path → all light
  tools reply in <10 ms at 1493 stations.
- **Frontend parity.** `scoring.py` mirrors `app/src/lib/scoring.ts`. If
  you change weights or filter defaults, change both.
- **Compact response shapes.** `views.py` trims each datamart entry to
  what the LLM actually needs in that context. Adding a new view? Keep
  field order deterministic so MCP clients can diff results across calls.

## Not yet shipped

- **POI place lists.** `list_pois` returns counts only. Per-place names
  + addresses live in NocoDB; will add a `nocodb_place_query` tool or a
  per-station JSON sidecar if the use case justifies the bytes.
- **Approval-time email.** Admin currently flips status manually; users
  poll their inbox. Adding a NocoDB → email webhook is a small follow-up.
- **last_used_at.** The schema has the column; the MCP doesn't write it
  yet (would require a NocoDB write per request, or a batched updater).
  Add when usage analytics matter.
