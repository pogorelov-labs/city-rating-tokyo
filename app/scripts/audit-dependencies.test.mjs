import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, chmodSync, rmSync, mkdirSync, copyFileSync, realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { evaluateAudit } from './audit-dependencies.mjs';

const counts = () => ({ info: 0, low: 0, moderate: 0, high: 0, critical: 0, total: 0 });
function fixture(severity = 'moderate', alias = false) {
  const node = `node_modules/${alias ? 'minimatch-core' : 'minimatch'}`;
  const root = { source: 1244012, name: 'minimatch', dependency: 'minimatch', severity, url: 'https://github.com/advisories/GHSA-g3hv-75wg-m249' };
  const totals = counts(); totals[severity] = 2; totals.total = 2;
  return {
    lock: { packages: { [node]: { name: 'minimatch', version: '3.1.5', dev: true }, 'node_modules/parent': { version: '1.0.0', dev: true,
      dependencies: alias ? { 'minimatch-core': 'npm:minimatch@3.1.5' } : { minimatch: '^3.1.0' } } } },
    report: { auditReportVersion: 2, metadata: { vulnerabilities: totals }, vulnerabilities: {
      minimatch: { name: 'minimatch', severity, nodes: [node], via: [root] },
      parent: { name: 'parent', severity, nodes: ['node_modules/parent'], via: ['minimatch'] },
    } },
  };
}
const blocked = (report, lock) => assert.throws(() => evaluateAudit(report, lock));
function harness(dir, lock) {
  const scripts = join(dir, 'app', 'scripts'); mkdirSync(scripts, { recursive: true });
  const script = join(scripts, 'audit-dependencies.mjs');
  copyFileSync(fileURLToPath(new URL('./audit-dependencies.mjs', import.meta.url)), script);
  writeFileSync(join(dir, 'app', 'package-lock.json'), JSON.stringify(lock));
  return script;
}

test('blocks the former exact 3.1.5 advisory and all moderate or higher findings', () => {
  for (const severity of ['moderate', 'high', 'critical']) {
    const { report, lock } = fixture(severity);
    assert.throws(() => evaluateAudit(report, lock), new RegExp(`Blocked ${severity}`));
  }
});

test('permits valid info/low reports, including verified npm aliases', () => {
  for (const severity of ['info', 'low']) for (const alias of [false, true]) {
    const { report, lock } = fixture(severity, alias);
    assert.deepEqual(evaluateAudit(report, lock), { blocked: 0 });
  }
});

test('rejects malformed reports, missing causes, alias mismatches and inconsistent counts', () => {
  let { report, lock } = fixture('low'); delete report.metadata; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.vulnerabilities.parent.via = ['missing']; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.metadata.vulnerabilities.low = 0; blocked(report, lock);
  ({ report, lock } = fixture('low')); delete lock.packages['node_modules/parent'].dependencies.minimatch; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.error = { code: 'EAUDITNOLOCK' }; blocked(report, lock);
  ({ report, lock } = fixture('low', true)); lock.packages['node_modules/minimatch-core'].name = 'other'; blocked(report, lock);
  ({ report, lock } = fixture('low')); lock.packages['node_modules/minimatch'].name = '@city-rating/minimatch-compat'; blocked(report, lock);
  ({ report, lock } = fixture('low')); lock.packages['node_modules/parent'].dependencies.minimatch = 'npm:other@3.1.5'; blocked(report, lock);
  ({ report, lock } = fixture('low', true)); lock.packages['node_modules/parent'].dependencies['minimatch-core'] = 'npm:other@3.1.5'; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.vulnerabilities.minimatch.nodes = ['node_modules/../minimatch']; blocked(report, lock);
});

test('rejects unresolved dependency paths and cycles with no advisory', () => {
  let { report, lock } = fixture('low');
  lock.packages['node_modules/parent/node_modules/minimatch'] = { name: 'minimatch', version: '11.0.3' }; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.vulnerabilities.parent.via = ['parent'];
  lock.packages['node_modules/parent'].dependencies.parent = '*'; blocked(report, lock);
  ({ report, lock } = fixture('low')); report.vulnerabilities.parent.via.push('parent');
  lock.packages['node_modules/parent'].dependencies.parent = '*';
  assert.deepEqual(evaluateAudit(report, lock), { blocked: 0 });
});

test('clean report passes', () => {
  const { report, lock } = fixture(); report.vulnerabilities = {}; report.metadata.vulnerabilities = counts();
  assert.deepEqual(evaluateAudit(report, lock), { blocked: 0 });
});

test('CLI fails closed on npm errors, malformed output and inconsistent exit status', () => {
  const dir = realpathSync(mkdtempSync(join(tmpdir(), 'city-audit-test-')));
  try {
    const fake = join(dir, 'npm');
    const scriptPath = harness(dir, fixture('low').lock);
    const clean = { auditReportVersion: 2, vulnerabilities: {}, metadata: { vulnerabilities: counts() } };
    for (const script of ['#!/bin/sh\nexit 2\n', '#!/bin/sh\necho broken\nexit 1\n', '#!/bin/sh\necho "{}"\nexit 0\n', `#!/bin/sh\nprintf '%s' '${JSON.stringify(clean)}'\nexit 1\n`]) {
      writeFileSync(fake, script); chmodSync(fake, 0o755);
      const result = spawnSync(process.execPath, [scriptPath], { env: { ...process.env, PATH: `${dir}:${process.env.PATH}` }, encoding: 'utf8' });
      assert.equal(result.status, 1); assert.match(result.stderr, /Dependency audit failed/);
    }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('CLI accepts a valid low report with npm moderate-threshold exit 0', () => {
  const dir = realpathSync(mkdtempSync(join(tmpdir(), 'city-audit-test-')));
  try {
    // Use a synthetic alias lock so the test does not depend on the checkout.
    const scriptPath = harness(dir, fixture('low', true).lock);
    const report = { auditReportVersion: 2, metadata: { vulnerabilities: { ...counts(), low: 1, total: 1 } }, vulnerabilities: {
      minimatch: { name: 'minimatch', severity: 'low', nodes: ['node_modules/minimatch-core'], via: [{ name: 'minimatch', severity: 'low', url: 'https://example.test/advisory' }] },
    } };
    const fake = join(dir, 'npm'); writeFileSync(fake, `#!/bin/sh\n[ "$*" = "audit --json --audit-level=moderate --include=dev" ] || exit 3\nprintf '%s' '${JSON.stringify(report)}'\nexit 0\n`); chmodSync(fake, 0o755);
    const result = spawnSync(process.execPath, [scriptPath], { env: { ...process.env, PATH: `${dir}:${process.env.PATH}` }, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr); assert.match(result.stdout, /No moderate or higher/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
