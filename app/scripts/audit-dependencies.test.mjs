import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync, chmodSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { evaluateAudit } from './audit-dependencies.mjs';

const realLock = JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));
const minimatch = realLock.packages['node_modules/minimatch'];
const time = Date.parse('2026-11-07T23:59:59Z');
function fixture() {
  const root = { source: 1244012, name: 'minimatch', dependency: 'minimatch', severity: 'moderate', url: 'https://github.com/advisories/GHSA-g3hv-75wg-m249' };
  return {
    lock: { packages: { 'node_modules/minimatch': structuredClone(minimatch), 'node_modules/parent': { version: '1.0.0', dev: true, dependencies: { minimatch: '^3.1.0' } } } },
    report: { auditReportVersion: 2, metadata: { vulnerabilities: { info: 0, low: 0, moderate: 2, high: 0, critical: 0, total: 2 } }, vulnerabilities: {
      minimatch: { name: 'minimatch', severity: 'moderate', nodes: ['node_modules/minimatch'], via: [root] },
      parent: { name: 'parent', severity: 'moderate', nodes: ['node_modules/parent'], via: ['minimatch'] },
    } },
  };
}
const blocked = (report, lock, at = time) => assert.throws(() => evaluateAudit(report, lock, at));

test('accepts only the allowed advisory and its verified inherited chain before expiry', () => {
  const { report, lock } = fixture();
  assert.deepEqual(evaluateAudit(report, lock, time), { exceptionApplied: true });
  blocked(report, lock, Date.parse('2026-11-08T00:00:00Z'));
});

test('rejects malformed reports, missing causes and inconsistent counts', () => {
  let { report, lock } = fixture(); delete report.metadata; blocked(report, lock);
  ({ report, lock } = fixture()); report.vulnerabilities.parent.via = ['missing']; blocked(report, lock);
  ({ report, lock } = fixture()); report.metadata.vulnerabilities.moderate = 0; blocked(report, lock);
  ({ report, lock } = fixture()); delete lock.packages['node_modules/parent'].dependencies.minimatch; blocked(report, lock);
  ({ report, lock } = fixture()); report.error = { code: 'EAUDITNOLOCK' }; blocked(report, lock);
});

test('rejects any additional moderate advisory, high severity, or altered identity', () => {
  let { report, lock } = fixture(); report.vulnerabilities.minimatch.via.push({ ...report.vulnerabilities.minimatch.via[0], url: 'https://github.com/advisories/GHSA-other' }); blocked(report, lock);
  ({ report, lock } = fixture()); report.vulnerabilities.minimatch.via[0].severity = 'high'; blocked(report, lock);
  ({ report, lock } = fixture()); lock.packages['node_modules/minimatch'].integrity = 'sha512-other'; blocked(report, lock);
  ({ report, lock } = fixture()); lock.packages['node_modules/minimatch'].version = '3.1.6'; blocked(report, lock);
  for (const severity of ['high', 'critical']) {
    ({ report, lock } = fixture());
    report.vulnerabilities.minimatch.severity = severity;
    report.vulnerabilities.minimatch.via[0].severity = severity;
    report.metadata.vulnerabilities.moderate = 1;
    report.metadata.vulnerabilities[severity] = 1;
    assert.throws(() => evaluateAudit(report, lock, time), new RegExp(`Blocked ${severity}`));
  }
});

test('rejects production, optional, nested vulnerable copies and unresolved resolution', () => {
  for (const patch of [{ dev: false }, { dev: undefined }, { optional: true }, { devOptional: true }]) {
    const { report, lock } = fixture(); Object.assign(lock.packages['node_modules/minimatch'], patch); blocked(report, lock);
  }
  let { report, lock } = fixture(); lock.packages['node_modules/parent'].dev = false; blocked(report, lock);
  ({ report, lock } = fixture()); lock.packages['node_modules/parent/node_modules/minimatch'] = structuredClone(minimatch); report.vulnerabilities.minimatch.nodes.push('node_modules/parent/node_modules/minimatch'); blocked(report, lock);
  ({ report, lock } = fixture()); lock.packages['node_modules/parent/node_modules/minimatch'] = { version: '11.0.3', dev: true }; blocked(report, lock);
});

test('rejects cycles with no advisory and permits a cycle that actually reaches the allowed root', () => {
  let { report, lock } = fixture();
  report.vulnerabilities.parent.via = ['parent']; lock.packages['node_modules/parent'].dependencies.parent = '*'; blocked(report, lock);
  ({ report, lock } = fixture());
  report.vulnerabilities.parent.via.push('parent'); lock.packages['node_modules/parent'].dependencies.parent = '*';
  assert.equal(evaluateAudit(report, lock, time).exceptionApplied, true);
});

test('clean report passes without claiming an exception', () => {
  const { report, lock } = fixture(); report.vulnerabilities = {}; report.metadata.vulnerabilities.moderate = 0; report.metadata.vulnerabilities.total = 0;
  assert.deepEqual(evaluateAudit(report, lock, time), { exceptionApplied: false });
  assert.deepEqual(evaluateAudit(report, lock, Date.parse('2026-11-08T00:00:00Z')), { exceptionApplied: false });
});

test('CLI fails closed on npm process errors and malformed output', () => {
  const dir = mkdtempSync(join(tmpdir(), 'city-audit-test-'));
  try {
    const fake = join(dir, 'npm');
    for (const script of ['#!/bin/sh\nexit 2\n', '#!/bin/sh\necho broken\nexit 1\n', '#!/bin/sh\necho "{}"\nexit 0\n']) {
      writeFileSync(fake, script); chmodSync(fake, 0o755);
      const result = spawnSync(process.execPath, [fileURLToPath(new URL('./audit-dependencies.mjs', import.meta.url))], { env: { ...process.env, PATH: `${dir}:${process.env.PATH}` }, encoding: 'utf8' });
      assert.equal(result.status, 1); assert.match(result.stderr, /Dependency audit failed/);
    }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
