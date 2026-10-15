# Tokyo source resilience and computed-ratings recovery

CRTKY-194 / CRTKY-160. Implementation and offline verification, 2026-10-15.
No live source refresh, schema mutation, or computed-ratings write was performed.

## Coverage and rollout

CRTKY-160 already shipped the strict ±3 spot-check gate, explicit transit-default
override, and >93% MLIT coverage gate. This change preserves those gates and
replaces delete-all/insert with **recoverable in-place updates, not atomic
replacement**. The scratch refresh test forces Otemachi safety to 1 (expected
about 9) and proves exit 1 before export or commit.

CRTKY-194's source canary, provenance, key runbook and midnight ingest are covered
here. Second-source adoption and the hp=0/rich-OSM confidence branch remain owner
decisions; this change does not alter food/nightlife formulas, confidence, caps,
or Bangkok. A correlation experiment is a separate deliverable, not implied by
these tests. No ticket closure is claimed.

Rollout order (operator actions; not executed):

1. Review and merge the code through normal CI. Stop every ratings writer and
   standalone exporter on **all hosts** for the maintenance window. Use one
   designated host and persistent recovery directory for compute and export.
2. In NocoDB base `ph4flgay4kmcgk4`, table `computed_ratings`
   (`mkp046vo42kj55w`), inspect fields. If `source_dates` is absent, add exactly
   one field with title **`source_dates`**, UI type **Long text** (`uidt=LongText`),
   nullable, no default. If present with this type, do nothing. If the existing
   type differs, stop and review migration; do not recreate or silently convert
   it. Keep `data_date` as **Single line text** (`SingleLineText`). This procedure
   is idempotent and needs a base schema editor; data-only tokens do not grant
   provisioning authority. No API provisioning helper is run automatically.
3. Give the refresh principal scoped read access to the four source tables and
   computed table, update access to computed rows, and read access to this table's
   metadata (`GET /api/v2/meta/tables/mkp046vo42kj55w`). It needs no computed
   insert/delete permissions. Run `python3 scripts/check-rating-schema.py`.
   Missing field, wrong type, or unavailable metadata access fails before any
   write. This read check does not prove update permission; that permission must
   be granted explicitly, without using a production write as a capability probe.
4. Owner selects a freshness policy in days. Supply it explicitly as
   `--max-source-age-days=N` to `refresh-ratings.sh`; there is deliberately no
   implicit 60/90/120-day SLA choice. Refresh upstream sources first if stale.
   The observed April snapshot must not be re-stamped to October. Coordinate
   source acquisition separately; do not widen the limit just to make CI green.
5. Run the read-only source check, then an authorized dry-run, review its source
   mix and spot-checks, then the authorized refresh on the same host. The refresh
   checks schema and inputs before compute, and compute rechecks its own exact
   inputs. A >5% drop in any existing HP/OSM category/source row count fails before
   writing. This is a conservative regression alarm, not a confidence/adoption
   threshold; investigate a legitimate change before changing the guard.
6. Export only after all writes pass full readback. Retain finalized journals
   under the operator's backup/retention policy. Do not copy them into git.

Read-only observations on 2026-10-15: metadata access works with the existing
scoped app token; `source_dates` is absent. HP: 1,493 rows dated April 3, with no
missing midnight count. OSM POIs: 1,398 dated April 3; extended: 1,467 dated
April 4; livability: 1,493 dated April 12–13. These observations are not fresh
source acquisitions. All candidate 60/90/120-day limits reject this snapshot.

## Provenance contract

- Existing `data_date` remains a scalar month (`YYYY-MM`), conservatively the
  oldest known row vintage across the four scraped POI tables. An absent or
  undated input gives `unknown`, never the compute/export date. It is **POI input
  vintage**, not a claim that annual crime/passenger data or editorial prose was
  observed that month. `computed_at` remains the computation date.
- Additive `source_dates` is a JSON object in LongText, with exactly four keys:
  `hotpepper`, `osm_pois`, `osm_extended`, `osm_livability`. Values are ISO
  `YYYY-MM-DD` derived from that station row's `scraped_at`, or JSON null when
  absent/unknown. Dates describe whole source rows; historic separate field
  updates cannot be reconstructed from one row timestamp.
- Exported `DemoData.source_dates?: Record<string, string | null>` matches the
  generator and authoritative exported data interface. Old rows without the
  column retain their actual legacy month and omit the map. Malformed nonempty
  JSON fails export. Curated rows keep their ratings and confidence rules while
  their upstream provenance is refreshed. No new UI confidence semantics.
- Completeness checks preserve documented coverage floors: HP/livability 100%,
  OSM POIs 93%, extended 97%. Available rows must have valid nonfuture source dates
  within the selected age. HP's five count fields, including midnight, must be
  nonnegative integers; missing is not zero. Both HP and OSM need a nonempty food
  signal. These are input/source-mix checks, not a fallback to another vendor.

Offline canary verification (no token needed; terminal mode cannot continue to
compute, export or commit):

```sh
bash scripts/refresh-ratings.sh --check-sources-fixture=/absolute/scratch.json --max-source-age-days=90
python -m pytest scripts/test_source_health.py scripts/test_refresh_integrity.py -q
```

The fixture has `slugs`, `tables` (table → canonical slug → source row), and an
optional fixed `today`. Tests generate stale and incomplete fixtures in temporary
directories and exercise the real shell. The fixture mode always exits after
the check, including when it succeeds.

## HotPepper key and acquisition runbook

Use the existing project secret store (Coolify per-service environment, documented
through the private infrastructure index). Never paste keys into a command URL,
git, chat, logs, or screenshots. The checker reads `HOTPEPPER_API_KEY` from the
process environment and suppresses request exception details, which can contain
the key query parameter. It does not require NocoDB access:

```sh
python3 scripts/scrapers/scrape-hotpepper.py --check-key
```

Run this bounded liveness check monthly and before a planned acquisition, through
the existing operator scheduler if one is configured; this PR does not install
a cron job or claim one already exists. A valid zero count is success. Recruit
returns API errors inside HTTP 200: code 2000 is authentication/IP rejection,
3000 invalid parameters; neither is a zero observation. The scraper retries
transient errors and exits nonzero on skipped/failed stations.

On authentication rejection: confirm the configured key/principal and allowed
usage with the owner, use Recruit's official account/key registration or recovery
flow, and store the replacement in the same scoped secret location. The exact
2026 reissue UI and permission to hold overlapping keys have not been verified;
do not promise instant self-serve rotation. Probe the replacement, update the
authorized consumer, confirm it can read, then retire the old key through the
provider's supported procedure. A failed probe keeps the last-good dataset frozen.
On timeouts/429/5xx, back off and retry acquisition later; do not compute zeros.
On provider retirement, stop refresh and bring the separate-source evidence and
confidence/cap decision to the owner. No automatic OSM-only degraded mode ships.

The tracked `scrape-hotpepper.py` now fetches **total, izakaya, bar, cafe and
midnight** together and only then stamps `scraped_at`. It updates existing IDs
when filling missing midnight counts or using `--refresh`; slug aliases are
canonicalized for matching. It never overwrites a successful old row after a
failed category query. `--dry-run` lists work without HP or NocoDB writes.
Production counts retain the existing `range=3` (**1,000 m**) semantics. An
800 m experiment needs complete paginated venue coordinates, deduplicated IDs,
and a distance filter; it cannot rescale these aggregate counts.

Provider references: [Recruit API reference](https://webservice.recruit.co.jp/doc/hotpepper/reference.html),
[key registration entry](https://webservice.recruit.co.jp/register/).

## Recovery protocol and transaction evidence

The live version endpoint reported `currentVersion=0.301.2` and
`releaseVersion=2026.09.1` (read-only). The matching upstream
[v2 controller](https://github.com/nocodb/nocodb/blob/0.301.2/packages/nocodb/src/controllers/data-table.controller.ts)
exposes separate record operations; the
[service](https://github.com/nocodb/nocodb/blob/0.301.2/packages/nocodb/src/services/data-table.service.ts)
calls `bulkUpdate`, and
[BaseModelSqlv2](https://github.com/nocodb/nocodb/blob/0.301.2/packages/nocodb/src/db/BaseModelSqlv2.ts)
opens/commits a transaction inside that operation. **Per-request transactions do
not make several PATCHes, or a DELETE followed by INSERT, atomic.** No exposed
v2 transaction handle spans these requests. We did not access the underlying
database or assume its engine. A generation-pointer/staging design would require
schema and every reader to migrate together; that larger change is not smuggled
into this fix.

`rating_store.py` requires identical nonempty unique slug sets and stable row IDs.
It refuses bootstrap, duplicates, or membership drift. Under the local file lock,
it reads all preimages and fsyncs a mode-0600 journal (then fsyncs its directory)
before the first PATCH. A journal contains backend/table identity, before/after
rows, field list, hashes and phase. Each batch is at most 100 rows. Readback checks
the full population and all owned fields, including the new metadata. No DELETE
or INSERT is used, even for restoration.

Known failed responses/readback errors trigger a best-effort restoration of all
preimages followed by full verification. The refresh still fails: it never exports
as though the candidate succeeded. A process kill, failed rollback, or transport
timeout leaves an unresolved journal. Timeout/disconnect outcomes are ambiguous:
automatic compensation could race the original request, so they require explicit
operator recovery after requests settle. A journal-finalization failure also blocks
the next run. Compute and export refuse unresolved local journals.

Default directory: `~/.local/state/city-rating/computed-ratings`. Direct compute and
export accept `--recovery-dir` for a designated persistent path; use the same path
for both. The refresh wrapper uses the default. The lock protects only this host
and directory. It does **not** block a legacy exporter, another host, a user editing
NocoDB, or readers directly consuming the table. Such readers can observe mixed
generations during the maintenance window. The deployed website uses committed
static data and stays on its last-good export.

If interrupted:

1. Stop every ratings writer/exporter on every host. Preserve the journal and
   directory. Confirm outstanding API requests have completed/terminated before
   recovery; a client timeout alone does not prove this. If this cannot be
   established, keep the last-good static export and escalate to the operator.
2. Use the same backend and scoped credentials. Run:

   ```sh
   python3 scripts/recover-ratings.py /absolute/path/to/unresolved.json --writers-stopped
   ```

3. The tool checks identity, checksums, unchanged membership/IDs, and schema;
   patches every before-image by ID; and verifies every owned field before marking
   `restored`. Repeat after a known partial recovery failure once service health
   returns. A finalized journal is refused to avoid overwriting later generations.
4. Resume only after successful readback and no unresolved journals. Do not delete
   a pending journal to bypass the guard. If journal data is lost/corrupt, IDs or
   membership changed, or writes came from another host, stop automated recovery:
   reconcile against the retained backup/last-good export with the owner. This
   protocol cannot reconstruct lost source metadata or undo independent edits.

Simulated tests cover failures after partial batches 1/2/3, process interruption,
unknown transport outcomes, failed rollback, dropped fields, disk/fsync failure,
missing schema, duplicate/missing slugs, local lock contention, wrong backend,
tampered journal, readback, and successful explicit recovery. They verify
recoverability under the stated single-writer assumptions; they do not claim a
live destructive test or globally atomic replacement.
