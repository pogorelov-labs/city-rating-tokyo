# Third critical pass — parallel review, gate-verification, canonicalization, D-6 (2026-11-08)

A third review pass over the state that did not exist when the first two
critiques were written: the continuation-plan execution, the P0 gate fix, the
canonicalization, the Telegram corpus (D-6), the decision record/PR — **and
the parallel reviewer's own work**, which this pass verifies before accepting
and then attacks from angles none of the earlier passes used.

---

## Angle A — verify the verifier (review-process integrity)

The parallel reviewer is an **agent**; its claims were treated as claims, not
facts. Every spot-check reproduces:

- Its claimed file writes are real: 4 commits on this branch (review report,
  audit gates, doc link fixes, wording), per-batch
  `review/REVIEW-2026-11-08-independent.md` ×5, bundle dispositions
  (`review.reviewer = "agent-review:DeepSeek Harness/deepseek-flash … not a
  human signatory"`), audit rules + 9 tests. Working tree and git history
  agree.
- **F1** (placeholder editorial values) reproduces: literal `"text_en"`/
  `"text"`/`"claim_ids"` values found in batch-4 profiles.
- **F2** reproduces: `st.hua-lamphong` has 8 exploded **source** limitation
  arrays + mixed claim array `hua-lamphong-c01` — classes my repair pass did
  not cover (my rule: all-entries-single-char; their rule: ≥10 single-char).
- **F3** reproduces: sam-yot has **3/43 body-read sources; 11 of 18 claims
  rest solely on unread sources**. See Angle B3 — this indicts my own record.
- **F5** reproduces with my own PIP probes: ICONSIAM is **inside** the
  khlong-san khet ring (`--khet` → True) and **outside** the station cell
  (shadowed key → False). My earlier khlong-san "correction" was wrong.
- **F8** reproduces: batch 3 has **no `review/findings.md`** and batch 4 has
  none either, despite program records claiming per-batch findings exist.

Their `audit.py` diff (1c237a8) was read before acceptance: the six new rules
match their §6 description and are sound.

**Process hazards this angle exposes:**

1. **Two writers, one working tree.** The reviewer's uncommitted `audit.py`
   briefly coexisted with my D-6 commit on the shared gate file; I declined to
   touch it. Recommendation: parallel contributors work on their own branches
   or at least commit promptly; the shared gate file is the collision point.
2. **The review sat unpushed for hours** (branch ahead 4) — the PR did not
   show the review. This pass pushes it.
3. **A completed review flips the shipped gate's semantics** (approved/
   blocked now legal `review.status` values). Downstream consumers must treat
   `reviewer: agent-review:*` as **not** human sign-off (see Angle D3).

## Angle B — my own passes audited against the review (what I got wrong)

1. **My limitations repair was partial.** The relabel ledger's "71 arrays
   repaired (byte-exact)" is true only for the all-single-char **claim**
   subset. Mixed arrays (character prefix + trailing sentence) and **source**
   arrays were never covered: 17 + 32 more remain (reviewer F2). The ledger
   now says so; the repair rule needs their ≥10-single-char generalization.
2. **My "zero P1 ×5" was rule-relative, not absolute.** Under the reviewer's
   rules the same corpus shows **97 P1 (batch 2) + 126 P1 (batch 4)** — the
   classes (placeholder editorial values, inline claim refs in copy,
   app-data locators on web sources, source-limitation explosions) were
   invisible to the shipped rules. Every "zero P1" claim in the program docs
   needs the qualifier "under the rules then in force" — now added where
   restated.
3. **The sam-yot verification-pass claim in my final review is not evidenced
   by the delivered bundle** (3/43 body-read; the commit message says five
   claims were upgraded to body-read; they were not). I propagated an
   unverifiable claim into the program record — the harshest finding of this
   pass, and now corrected in the final review by the reviewer (F16).
4. **My khlong-san correction was wrong** (F5): I conflated the station cell
   with the khet. Root cause pattern: the B-8 key-shadowing trap was
   *documented* (open_issues, batch-3) but the tool fix (`--khet`) landed
   only today — the batch-4 agent hit a known trap because the fix was
   deferred. Lesson recorded: **fix tools, not just document traps**.
5. **My B-13 conflict link needs re-examination.** I linked
   `wat-mangkon-c06 → c02/c04` as the corpus's only intra-bundle claim
   conflict. The review (F7) establishes c02/c04 as **correct** and the
   tension as c06's framing vs Wikipedia's simplification — the link's
   target attribution is questionable and should be revisited in rework, not
   silently kept.

## Angle C — what the reviewer ALSO missed (new findings this pass)

1. **Canonical-family latent bug (fixed).** `canon_family("Bangkok Post
   (Telegram channel)")` returned `bangkok-post` — a masquerading Telegram
   channel would have corroborated the real outlet's family once TG citations
   exist. Fix: rule 0 in `canonical.py` (anything containing "telegram" is
   its own family) + registry family strings now carry the "Telegram" marker
   + `tg_corpus cite` enforces it + tests.
2. **`tg_corpus cite` emitted source records for rejected channels** (no
   verdict guard) — demonstrated live by citing the rejected "bangkokpost"
   channel. Fix: cite now refuses unregistered and `usable_for_evidence:
   false` channels.
3. **`tg_corpus cite --body-read` argparse bug** (store_true + default=True —
   always true, `False` inexpressible). Fix: `BooleanOptionalAction`.
4. **`tg_corpus pull` stall loop** — a page returning only known messages
   re-fetched the same URL until max-pages. Fix: stall break.
5. **The packet's "no claim rests solely on snippet-only source
   (machine-verified)" was false** (F3 makes it demonstrably false) and sat
   uncorrected in the tree even after the review — retracted with a pointer
   now.
6. **URL-count staleness**: docs said 547 distinct URLs; post-repair registry
   is 543 (sam-yan's four Overpass records merged into one). Corrected in
   final-review §1, plan §0 and C-6.
7. **Positive result worth recording**: no editorial preview/lead block cites
   *only* relabeled (now-proposed) claims — the B-10 relabel creates no
   evidence-bar (E-5) exposure in card copy; 14 blocks cite them alongside
   other claims, which E-5's guide-narrative tier permits with attribution.

## Angle D — decisions, publication, and the agent-review semantics

1. **The decision record is honest but thin.** DEC-5/6/7/8/10 were adopted at
   documented defaults from a one-word approval; the defaults were already
   the plan's stated "if un-decided" behavior, so nothing changed silently —
   but DEC-2 (name a human reviewer), DEC-3 (calendar owner), DEC-4 (D-1
   budget), DEC-9 (maintenance owner) remain genuinely open, and the agent
   review does **not** substitute for DEC-2 (its own header says so).
2. **The PR is live while 24 bundles are blocked.** The PR body's "Open
   gates" section stays accurate; the review's statuses now ride the same
   branch. No contradiction, but the tier-plan status column (agent-set) must
   never be quoted as human approval.
3. **Concrete E-5 amendment (recorded here, applies to the adapter spec):**
   the copy evidence bar must key on *human* sign-off — a bundle whose
   `review.reviewer` starts with `agent-review:` is not copy-eligible until a
   human signatory records approval. Otherwise "approved" statuses leak into
   product copy with no human in the loop.

## Angle E — still missed at program level (unchanged or newly opened)

- **The rework itself** (24 blocked bundles; reviewer §9 order): F1/F2 are
  lossless rebuilds from `raw/` (mechanical, mine); **F4's recommended
  "re-assemble batch 2" must NOT re-assemble** — raw/ predates coordinator
  corrections; the fix is a profile-level strip of inline refs (like the
  contract-repair pattern). F3 needs real re-research or claim/copy removal
  (token budget — DEC-4-adjacent). F5/F6/F7/F10/F12 are copy/provenance edits.
- Batch-3/4 `review/findings.md` still missing (F8) — a batch-DoD gap that my
  "per-batch verification lives in each batch's review/" claim glossed over.
- A-5 (legal/privacy), A-6 (Thai verification), E-7 (corridor coherence),
  C-7 (retroactive volatile rechecks), safety-5 routing, B-12 adoption, DEC-3
  owner — all open; none advanced by today's passes.
- The "audit zero-P1" DoD line needs a standing convention: report the rule
  version with the count (G2 findings are rule-relative, as this pass proved
  twice).

## Angle F — kit quality pattern

Three same-class path bugs from one author in one day (ROOT counting ×3), the
assembler shipping behaviors the reviewer had to gate (inline refs not
stripped, placeholder values unexamined), and audit rules growing only when a
defect class was *discovered* rather than from the contract text. The kit is
now tested (33 green) but its growth model is reactive. Proposal (recorded,
not built): derive audit rules from the handoff contract clauses as a
checklist — every "must" in HANDOFF.md gets a named rule or an explicit
"not machine-checkable" note. That converts the review's F9 lesson into a
standing design rule.

---

## Fixes applied by this pass (all gates re-run green)

`canonical.py` rule 0 (TG families never merge) + tests · `tg_corpus.py`
verdict guard + argparse fix + stall break + family-marker defense · registry
family fix · packet retraction of the false residual · URL-count corrections ·
third-review doc + plan progress log. 33 kit tests green; validate ALL OK ×5;
audit findings unchanged from the review's baseline (rules-in-force noted).

## What survived the pass

The reviewer's dispositions and their audit rules (verified, accepted); the
honest-corrections chain across all four program documents; the corpus's
structural integrity architecture — provenance, evidence tiers, tier-C
honesty, and the standing boundaries. The weakest point exposed today is not
any single defect but the **reactive growth model of the gates** — every
defect class was found by a human-shaped attention pass, never by the
contract. That is now the top process item (Angle F).
