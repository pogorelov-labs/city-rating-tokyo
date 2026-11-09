#!/usr/bin/env node
/**
 * Editorial exporter (E-1/P0 skeleton — ships behind a feature flag; nothing
 * in the app imports its output yet, so the build is unaffected until P1).
 *
 * Reads the research program's entity bundles and emits, per the E-1 draft
 * spec (2026-11-08-integration-review.md):
 *   1. editorial-index.json  — one slim record per entity (card/map payload)
 *   2. per-entity chunks     — guide narrative + claims + sources (on-demand)
 *
 * Gates enforced HERE (not by convention):
 *   - entity precedence: an entity carried by two bundles resolves to the
 *     highest tier (batch 5 upgrades over batch 4); the superseded batch is
 *     recorded as provenance.
 *   - human-sign-off key (E-5): copy_eligible=false unless review.status is
 *     `approved` AND the reviewer does NOT start with `agent-review:`.
 *   - evidence bar: conflicted and researcher_inference claims never enter
 *     guide sections; corroborated-only previews; proposed items are flagged
 *     `attribution_required`.
 *   - tier-C anti-laundering: data-only entities emit a card record and a
 *     chunk with NO narrative fields.
 *
 * Usage (dry-run by default):
 *   node scripts/export-editorial.mjs --research ../research/bangkok/editorial/batches \
 *        --app-data src/data/bangkok [--emit]
 */
import { readdirSync, readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const TIER_ORDER = { A: 3, B: 2, C: 1 };
// Tier is a recorded fact (batch identity), not a shape inference — the
// fifth-review finding: a claims>=12 heuristic misclassified 8 tier-B light
// bundles (8–12-claim contract) as tier A.
const TIER_BY_BATCH = {
  '2026-11-05-pilot-zcode-main': 'A',
  '2026-11-07-batch2-zcode-main': 'A',
  '2026-11-07-batch3-zcode-main': 'A',
  '2026-11-08-batch5-b-to-a': 'A',
  '2026-11-07-batch4-light-zcode-main': 'B',
  '2026-11-08-tail-data-only': 'C',
};
const AGENT_REVIEWER = /^agent-review:/;

const isDataOnly = bundle =>
  (bundle.review?.notes ?? []).some(n => String(n).toLowerCase().includes('data-only'));

export function tierOf(bundle) {
  if (isDataOnly(bundle)) return 'C';
  const recorded = bundle._batch && TIER_BY_BATCH[bundle._batch];
  if (recorded) return recorded;
  // fallback for unregistered batches (documented heuristic, not authoritative)
  const claims = bundle.claims?.length ?? 0;
  const sources = bundle.sources?.length ?? 0;
  return claims >= 12 && sources >= 4 ? 'A' : 'B';
}

export function copyEligible(bundle) {
  const r = bundle.review ?? {};
  return r.status === 'approved'
    && typeof r.reviewer === 'string'
    && r.reviewer.length > 0
    && !AGENT_REVIEWER.test(r.reviewer)
    && Boolean(r.reviewed_at);
}

/** Entity precedence: highest tier wins; ties → newest researched_at manifest… (P0: input order). */
export function selectBundles(bundles) {
  const byEntity = new Map();
  for (const b of bundles) {
    const key = b.entity.key;
    const prev = byEntity.get(key);
    if (!prev) { byEntity.set(key, b); continue; }
    const [ta, tb] = [TIER_ORDER[tierOf(b)], TIER_ORDER[tierOf(prev)]];
    if (ta > tb) { prev.superseded = true; byEntity.set(key, b); }
    else if (ta < tb) { b.superseded = true; }
    else { b.superseded = true; } // same tier twice → keep first, mark the other
  }
  return [...byEntity.values()];
}

export function minRecheck(bundle) {
  const dates = (bundle.claims ?? [])
    .map(c => c.temporal_scope?.recheck_by).filter(Boolean).sort();
  return dates[0] ?? null;
}

/** Evidence bar: which claims may appear in guide sections, and how. */
export function claimsForGuide(claims) {
  return (claims ?? [])
    .filter(c => c.review_status === 'corroborated' || c.review_status === 'proposed')
    .map(c => ({ id: c.id, status: c.review_status,
                 attribution_required: c.review_status === 'proposed' }));
}

/** Sections with claim filtering; conflicted/inference never surface. */
export function guideSections(editorial, allowedIds) {
  const out = {};
  for (const [field, key] of [['strengths','strengths'], ['tradeoffs','tradeoffs'],
                              ['day_night','dayNight'], ['within_area_variation','variation'],
                              ['conditional_fit','fit']]) {
    const items = editorial?.[field] ?? [];
    out[key] = items
      .filter(it => (it.claim_ids ?? []).every(id => allowedIds.has(id)))
      .map(it => ({ en: it.text_en ?? '', claims: it.claim_ids }));
  }
  return out;
}

/** Evidence bar for the card preview: every preview claim corroborated. */
export function eligiblePreview(bundle) {
  const pv = bundle.editorial?.preview;
  if (!pv || !copyEligible(bundle)) return null;
  const statuses = new Map((bundle.claims ?? []).map(c => [c.id, c.review_status]));
  const ids = pv.claim_ids ?? [];
  if (!ids.length || !ids.every(id => statuses.get(id) === 'corroborated')) return null;
  return { en: pv.text_en };
}

export function buildIndexEntity(bundle) {
  const entity = bundle.entity;
  const tier = tierOf(bundle);
  if (tier === 'C') {
    return { tier, card: 'data_only', copy_eligible: false,
             as_of: bundle.selection_context?.as_of ?? null,
             review: signoffRecord(bundle), chunk: null, superseded_by: bundle.superseded_by ?? null };
  }
  return {
    preview: eligiblePreview(bundle),
    tier,
    copy_eligible: copyEligible(bundle),
    as_of: null, // P1: derived from review.reviewed_at / manifest research_completed_at
    chunk: `/data/bangkok/editorial/${entity.key}.json`,
    review: signoffRecord(bundle),
    stats: { sources: bundle.sources?.length ?? 0,
             body_read: (bundle.sources ?? []).filter(s => s.body_read).length,
             claims: bundle.claims?.length ?? 0 },
    // E-3 disclosures: program-level rating mechanisms (B-3/B-5 receipts), one
    // tap from the score. Keys resolve via messages/*/common.json.
    disclosures: ['disclosure.greenBuffer1km', 'disclosure.transportMechanism'],
    recheck_due: minRecheck(bundle),
    superseded_by: bundle.superseded_by ?? null,
  };
}

function signoffRecord(bundle) {
  const r = bundle.review ?? {};
  return { status: r.status ?? 'unknown', signatory: copyEligible(bundle) ? 'human' : 'none|agent',
           reviewer: r.reviewer ?? null, reviewed_at: r.reviewed_at ?? null };
}

export function buildChunk(bundle, allowedIds) {
  if (tierOf(bundle) === 'C') {
    // anti-laundering: no narrative fields exist on a tier-C chunk, by construction
    return { key: bundle.entity.key, card: 'data_only',
             note: 'Scores only — editorial guide pending.' };
  }
  const ed = bundle.editorial ?? {};
  return {
    key: bundle.entity.key,
    as_of: null, // P1
    guide: {
      lead: allowedIds.size ? { en: ed.guide_lead?.text_en ?? '', claims: (ed.guide_lead?.claim_ids ?? []).filter(id => allowedIds.has(id)) } : { en: '', claims: [] },
      sections: guideSections(ed, allowedIds),
      uncertainties: (ed.uncertainties ?? []).filter(u => typeof u === 'string'),
      attribution_required: claimsForGuide(bundle.claims).filter(c => c.attribution_required).map(c => c.id),
    },
    claims: (bundle.claims ?? []).map(c => ({
      id: c.id, status: c.review_status, kind: c.kind,
      temporal: { event: c.temporal_scope?.event_date ?? null,
                  observed: c.temporal_scope?.observed_period ?? null,
                  recheck: c.temporal_scope?.recheck_by ?? null },
      limitations: c.limitations ?? [], conflicts_with: c.conflicts_with ?? [],
    })),
    sources: (bundle.sources ?? []).map(s => ({
      id: s.id, url: s.canonical_url, body_read: s.body_read,
      attribution: { publisher: s.publisher, family: s.publisher_family },
    })),
  };
}

/** Load every researched bundle from a batches root (skips data-only markers later). */
export function loadBundles(batchesRoot) {
  const bundles = [];
  if (!existsSync(batchesRoot)) return bundles;
  for (const dir of readdirSync(batchesRoot, { withFileTypes: true })) {
    if (!dir.isDirectory()) continue;
    const profiles = join(batchesRoot, dir.name, 'profiles');
    if (!existsSync(profiles)) continue;
    for (const fn of readdirSync(profiles)) {
      if (!fn.endsWith('.json')) continue;
      try {
        const bundle = JSON.parse(readFileSync(join(profiles, fn), 'utf8'));
        bundle._batch = dir.name;
        bundles.push(bundle);
      } catch { /* skip unreadable partial */ }
    }
  }
  return bundles;
}

/** Entity keys the shipped app can actually render: station areas + districts. */
export function loadLiveKeys(appDir) {
  const areas = JSON.parse(readFileSync(join(appDir, 'src/data/bangkok/stations.json'), 'utf8')).areas;
  const districts = JSON.parse(readFileSync(join(appDir, 'src/data/bangkok/districts.json'), 'utf8')).districts;
  return new Set([...areas.map(a => `st.${a.id}`), ...districts.map(d => d.slug)]);
}

export function buildIndex(bundles, supersededIds, liveKeys) {
  const entities = {};
  for (const b of selectBundles(bundles)) {
    // Entities the app no longer has (removed areas) never ship — the research
    // bundle stays as the historical record, the served surface does not.
    if (liveKeys && !liveKeys.has(b.entity.key)) continue;
    const rec = buildIndexEntity(b);
    if (supersededIds?.has(b.entity.key)) rec.superseded_by = rec.superseded_by ?? true;
    entities[b.entity.key] = rec;
  }
  return { _meta: { schema_version: '1.1-p0', exporter: 'export-editorial.mjs P0' }, entities };
}

export function run({ researchDir, emit, outIndex, outChunks, liveKeys }) {
  const bundles = loadBundles(researchDir);
  const selected = selectBundles(bundles);
  const index = buildIndex(bundles, undefined, liveKeys);
  const lines = [`bundles loaded: ${bundles.length}; entities after precedence: ${selected.length}`];
  const skipped = selected.filter(b => liveKeys && !liveKeys.has(b.entity.key));
  if (skipped.length) lines.push(`outside app snapshot (skipped): ${skipped.map(b => b.entity.key).join(', ')}`);
  const eligible = Object.values(index.entities).filter(e => e.copy_eligible).length;
  const tierC = Object.values(index.entities).filter(e => e.tier === 'C').length;
  lines.push(`copy_eligible: ${eligible} (human sign-off required for the rest — E-5 key)`);
  lines.push(`tier C (data-only cards): ${tierC}`);
  if (emit) {
    mkdirSync(outIndex && dirname(outIndex), { recursive: true });
    writeFileSync(outIndex, JSON.stringify(index, null, 1));
    mkdirSync(outChunks, { recursive: true });
    for (const b of selected) {
      if (liveKeys && !liveKeys.has(b.entity.key)) continue;
      const allowed = new Set(claimsForGuide(b.claims).map(c => c.id));
      writeFileSync(join(outChunks, `${b.entity.key}.json`),
                    JSON.stringify(buildChunk(b, allowed), null, 1));
    }
    lines.push(`EMITTED index -> ${outIndex}; chunks -> ${outChunks}`);
  } else {
    lines.push('dry-run (pass --emit to write)');
  }
  return lines;
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const arg = name => {
    const i = process.argv.indexOf(name);
    return i >= 0 ? process.argv[i + 1] : undefined;
  };
  const appDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const repoDir = resolve(appDir, '..');
  const research = arg('--research') ?? join(repoDir, 'research/bangkok/editorial/batches');
  const lines = run({
    researchDir: research,
    emit: process.argv.includes('--emit'),
    outIndex: arg('--out-index') ?? join(appDir, 'src/data/bangkok/editorial-index.json'),
    outChunks: arg('--out-chunks') ?? join(appDir, 'public/data/bangkok/editorial'),
    liveKeys: loadLiveKeys(appDir),
  });
  console.log(lines.join('\n'));
}
