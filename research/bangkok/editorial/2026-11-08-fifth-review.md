# Fifth review — the newest artifacts audited (2026-11-08)

Each pass has audited a different layer (claims → gates → my own corrections →
superseded-state → now **the newest artifacts**: the P0 exporter, the
post-batch-5 aggregations, and the residual staleness). Three real findings,
one of them in my own just-written code; all fixed in this pass.

## F5-1 — the P0 exporter's tier inference was wrong (own bug, caught by emit-validation)

The dry-run said `copy_eligible: 0` (correct) but the emit path — never
executed on real data before this pass — produced **39 A / 7 B instead of
31/15**: eight batch-4 light bundles with ≥12 claims and ≥4 sources tripped
the `claims ≥ 12 → A` shape heuristic. The tier-B contract is 8–12 claims, so
12-claim light bundles sat exactly on the boundary. Fix: tier is a **recorded
fact** (batch identity via `TIER_BY_BATCH`), with the heuristic demoted to a
documented fallback for unregistered batches. Post-fix emit: **31/15/137,
exact**; `chunk` href added to index entities (was missing); dead lines
removed. 7 fixture tests updated and green.

Method note: the bug was invisible to the dry-run and to the fixture tests
(whose own fixtures relied on the same wrong heuristic) — it surfaced only
when the emit path ran on real data and the output was checked against an
independent count (the tier plan). Check generated output against expected
totals, always.

## F5-2 — claim-ID duplication across superseded pairs (contained, but the old "zero collisions" claim is stale)

**103 claim IDs exist in both batch-4 and batch-5** for the 9 upgraded
entities (each bundle numbered its own claims from c01). The deep review's
B-arc1 ("zero collisions corpus-wide") was true then and is **stale now** —
uniqueness holds *within the authoritative per-entity record* only, i.e. it
is guaranteed by the precedence rule, not by the corpus. Consequences audited:
the exporter, recheck registry, and B-11 all consume the precedence-filtered
view, so no consumer sees the duplication; the condition is documented here
rather than "fixed" (renumbering superseded history would be worse). If any
future tool ever merges across the superseded boundary, it must key on
`(batch, claim_id)`, never bare claim_id.

## F5-3 — B-2 audit was undercounted and then I truncated the CSV twice

The 20 "HTTPError" rows were transient rate-limiting: a delayed retry
recovered 8 → audit **100/133** (90 ≤100 m; drift unchanged). But the
recovery crashed twice on a field-name mismatch (`wiki_lng` vs `wiki_lon`)
**after write-open had truncated the audit CSV**, and the second run then
wrote an empty list over it. Restored from git (273ceb2 — committed artifacts
saved the data), fixed the key, and the recovery now builds both final lists
in memory before opening any file for write. New standing rule: **never open
write mode on an artifact until its replacement content is fully
constructed.**

Also confirmed sound: Silom-corridor rent facts across the three bundles
(sala-daeng "app blend = top of asking ranges", chong-nonsi 24k median + 28–55k
guides, bang-rak USD 862 ≈ 28–29k) are mutually coherent — the raw-fact sweep
extension for the upgraded units passes on the corridor with the most
overlapping claims.

## Residual staleness fixed in passing

- Reviewer packet header still said "batches 1–2 (12 bundles)" (F15 residue,
  never fixed) → now states the real scope; the 45–60-min estimate now scopes
  to §2 only.
- WS-C intro still said "201 dated recheck flags" → now 603 items
  (253 + 399) under precedence.

## State after this pass

Exporter: tier-correct emit validated on real data (31/15/137; zero
conflicted leakage; zero tier-C narrative; zero empty leads). Corpus:
183/183 (31/15/137), all gates green, registry 603/666 under precedence,
B-2 at 100/133 with classification, receipts coherent. Open items unchanged:
DEC-2 named reviewer, A-5/A-6 human passes, build-machine replay, TG handles.
