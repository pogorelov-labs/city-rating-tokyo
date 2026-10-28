# ADR: Next phase — Consolidate & Harden — 2026-10-28

**Status:** Accepted by the owner on 2026-10-28.
Decision: `crtky-next-phase-2026-10-28`.

The research → adoption → implementation program and the health epic are
complete, with no next epic defined. The question is whether to expand city
coverage, deepen the existing cities, complete Bangkok's remaining gaps, or
first consolidate the shipped baseline.

## Adopted

Choose **Consolidate & Harden** before committing to the next product epic:

- Cut v0.1.2 through the [release runbook](../../docs/RELEASING.md).
- Have the owner execute CRTKY-199: retire the 251-station daily-essentials
  fallback cohort and activate the approved confidence, freshness and
  recoverable-update path. The [Tokyo refresh runbook](../notes/2026-10-15-hotpepper-resilience-runbook.md)
  remains the operational reference.
- Apply the approved Loki and Bangkok-embedding mounts through private
  maintainer procedures, enabling observability and Bangkok semantic search.
- Stabilize the Tokyo touch/canvas browser check, then promote e2e CI to blocking.
- Fix the phone-width selected-card/zoom-control obstruction tracked in CRTKY-114.

Then re-gate breadth versus depth using roughly two weeks of live traffic
evidence. This phase improves the feedback loop; it does not preselect the
next city or a new category program. Operational actions remain owner work;
the ADR records the decision rather than claiming those actions have run.

## Alternatives and costs

| Alternative | Cost / trade-off | Decision |
|---|---|---|
| Third city | Months of research per city; accepts estimation and coverage gaps like Bangkok's while expanding the maintenance surface. | Defer until the existing baseline and feedback loop are working. |
| Depth push in the existing cities | Visible value without another city, but category additions can outrun source quality and the honesty doctrine. | Defer as the natural follow-on after consolidation. |
| Bangkok completion | Closes the two-city evidence asymmetry, but sequencing depends on owner actions for source access and licensing. | Proceed in parallel at the owner's discretion; do not make it the phase's critical path. |

## Rationale

Every item in the chosen phase is cheaper than the first step of any
alternative and increases the value of whichever scope follows. A release
delivers the merged improvements; the operator pass closes a known data
fallback; live observability replaces speculation with evidence. The other
options remain available with better information after this phase.

## Reopen conditions

Re-gate roughly two weeks after v0.1.2 with Loki collection active. Review
Loki/Umami traffic, feedback signals and search patterns before choosing
breadth versus depth.

Reopen earlier if a fact invalidates an assumption: source access becomes
available, a concrete third-city dataset changes the cost, or user feedback
demands a category. Bangkok owner actions may proceed in parallel without
waiting for the re-gate.

Acceptance source: owner decision-gate interview, 2026-10-28; condensed from
the private `decision-next-phase.md` record (full provenance path retained
privately). This ADR is the canonical decision after merge.
