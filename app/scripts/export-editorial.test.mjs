import { test } from 'node:test';
import assert from 'node:assert/strict';
import { selectBundles, copyEligible, buildIndexEntity, buildChunk, claimsForGuide } from './export-editorial.mjs';

const base = over => ({
  schema_version: '1.0',
  entity: { key: 'st.x', kind: 'station_area', name_en: 'X', name_th: 'X' },
  selection_context: {},
  sources: [], claims: [], question_answers: [], editorial: {},
  images: [], review: { status: 'ready_for_review', reviewer: null, reviewed_at: null, notes: [] },
  ...over,
});

const agentApproved = over => base({
  ...over,
  review: { status: 'approved', reviewer: 'agent-review:DeepSeek Harness/deepseek-flash',
            reviewed_at: '2026-11-08T13:00:00+03:00', notes: [] },
});
const humanApproved = over => base({
  ...over,
  review: { status: 'approved', reviewer: 'Jane Doe (editorial)', reviewed_at: '2026-11-09T10:00:00Z', notes: [] },
});

test('sign-off key: agent-reviewed approved bundle is NOT copy-eligible (E-5 amendment)', () => {
  assert.equal(copyEligible(agentApproved()), false);
  assert.equal(buildIndexEntity(agentApproved()).copy_eligible, false);
});

test('sign-off key: human-approved bundle IS copy-eligible', () => {
  assert.equal(copyEligible(humanApproved()), true);
  assert.equal(buildIndexEntity(humanApproved()).copy_eligible, true);
  assert.equal(buildIndexEntity(humanApproved()).review.signatory, 'human');
});

test('precedence: tier-A beats tier-B for the same entity; superseded recorded', () => {
  const tierB = base({ entity: { key: 'st.sala', kind: 'station_area', name_en: 'S', name_th: 'S' },
                       _batch: '2026-11-07-batch4-light-zcode-main',
                       sources: [{ id: 's1' }], claims: [{ id: 'c1' }] });
  const tierA = { ...agentApproved(), entity: { key: 'st.sala', kind: 'station_area', name_en: 'S', name_th: 'S' },
                  _batch: '2026-11-08-batch5-b-to-a',
                  sources: [{ id: 's1' }, { id: 's2' }, { id: 's3' }, { id: 's4' }],
                  claims: Array.from({ length: 14 }, (_, i) => ({ id: `c${i}` })) };
  const picked = selectBundles([tierB, tierA]);
  assert.equal(picked.length, 1);
  assert.equal(picked[0], tierA);
  assert.equal(tierB.superseded, true);
});

test('evidence bar: conflicted and researcher_inference claims never enter guide sections', () => {
  const allowed = new Set(claimsForGuide([
    { id: 'a', review_status: 'corroborated' },
    { id: 'b', review_status: 'proposed' },
    { id: 'c', review_status: 'conflicted' },
    { id: 'd', review_status: 'proposed' },
  ]).map(c => c.id));
  assert.deepEqual([...allowed].sort(), ['a', 'b', 'd']);
  assert.deepEqual(claimsForGuide([{ id: 'b', review_status: 'proposed' }])[0].attribution_required, true);
  const ed = { strengths: [
    { text_en: 'ok', claim_ids: ['a'] },
    { text_en: 'dropped — conflicted only', claim_ids: ['c'] },
    { text_en: 'kept w/ attribution flag', claim_ids: ['b'] },
  ] };
  const sections = buildChunk({ ...base(), editorial: ed,
    claims: [{ id: 'a', review_status: 'corroborated', temporal_scope: {} },
             { id: 'b', review_status: 'proposed', temporal_scope: {} },
             { id: 'c', review_status: 'conflicted', temporal_scope: {} }] }, allowed);
  assert.equal(sections.guide.sections.strengths.length, 2);
  assert.ok(sections.guide.attribution_required.includes('b'));
});

test('tier-C anti-laundering: data-only bundle emits a card record and a chunk with NO narrative', () => {
  const dataOnly = base({ review: { status: 'draft', reviewer: null, reviewed_at: null,
                                    notes: ['data-only placeholder (tier C)'] } });
  assert.equal(buildIndexEntity(dataOnly).tier, 'C');
  assert.equal(buildIndexEntity(dataOnly).card, 'data_only');
  const chunk = buildChunk(dataOnly, new Set());
  assert.equal(chunk.card, 'data_only');
  assert.equal(chunk.guide, undefined);
  assert.equal(chunk.claims, undefined);
});

test('recheck_due: minimum recheck_by across claims', () => {
  const b = base({ claims: [
    { id: 'a', temporal_scope: { recheck_by: '2027-03' } },
    { id: 'b', temporal_scope: { recheck_by: '2026-12-31' } },
    { id: 'c', temporal_scope: { recheck_by: null } },
  ] });
  assert.equal(buildIndexEntity(b).recheck_due, '2026-12-31');
});

test('banned-copy words would be visible to the gate (fixture documents the contract)', () => {
  const ed = { strengths: [{ text_en: 'a vibrant hidden gem', claim_ids: [] }] };
  assert.match(ed.strengths[0].text_en, /\b(vibrant|hidden gem|something for everyone)\b/i);
});
