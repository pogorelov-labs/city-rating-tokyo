import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const levels = ['info', 'low', 'moderate', 'high', 'critical'];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = message => { throw new Error(message); };
const validNode = node => typeof node === 'string' && /^(?:node_modules\/(?:@[^/]+\/)?[^/]+\/)*node_modules\/(?:@[^/]+\/)?[^/]+$/.test(node) &&
  !node.split('/').some(part => part === '.' || part === '..' || part.includes('\\'));

function resolveDependency(packages, node, dependency) {
  let base = node;
  while (true) {
    const candidate = `${base ? `${base}/` : ''}node_modules/${dependency}`;
    if (Object.hasOwn(packages, candidate)) return candidate;
    if (!base) return null;
    const index = base.lastIndexOf('/node_modules/');
    base = index < 0 ? '' : base.slice(0, index);
  }
}

function refersTo(name, key, spec) {
  if (typeof spec !== 'string' || !spec.startsWith('npm:')) return key === name;
  const alias = spec.slice(4);
  return alias === name || alias.startsWith(`${name}@`);
}

/** Validate npm's full report against the lockfile; no advisories are waived. */
export function evaluateAudit(report, lock) {
  if (!object(report) || Object.hasOwn(report, 'error') || report.auditReportVersion !== 2 || !object(report.vulnerabilities) ||
      !object(report.metadata?.vulnerabilities) || !object(lock?.packages)) fail('Malformed audit report or lockfile');
  const vulnerabilities = report.vulnerabilities;
  const counts = Object.fromEntries(levels.map(level => [level, 0]));
  const roots = new Set();
  for (const [name, entry] of Object.entries(vulnerabilities)) {
    if (!object(entry) || entry.name !== name || !levels.includes(entry.severity) ||
        !Array.isArray(entry.via) || entry.via.length === 0 || !Array.isArray(entry.nodes) || entry.nodes.length === 0) fail(`Malformed vulnerability: ${name}`);
    counts[entry.severity]++;
    for (const node of entry.nodes) {
      if (!validNode(node) || !Object.hasOwn(lock.packages, node)) fail(`Unknown lock path: ${node}`);
      const pkg = lock.packages[node];
      // An alias and its target can have different names. Prefer the lockfile's
      // explicit package identity; the directory name is only the default.
      if (!object(pkg) || (pkg.name ?? node.split('node_modules/').at(-1)) !== name) fail(`Unknown lock path: ${node}`);
    }
    for (const cause of entry.via) {
      if (typeof cause === 'string') {
        if (!Object.hasOwn(vulnerabilities, cause)) fail(`Unknown cause ${cause} for ${name}`);
        for (const node of entry.nodes) {
          const pkg = lock.packages[node];
          const edges = [pkg.dependencies, pkg.optionalDependencies, pkg.peerDependencies]
            .filter(object).flatMap(deps => Object.entries(deps)).filter(([key, spec]) => refersTo(cause, key, spec));
          const linked = edges.some(([key]) => {
            const resolved = resolveDependency(lock.packages, node, key);
            return resolved && vulnerabilities[cause].nodes?.includes(resolved);
          });
          if (!linked) fail(`Unresolved dependency path ${node} -> ${cause}`);
        }
      } else if (!object(cause) || !levels.includes(cause.severity) || typeof cause.url !== 'string' || cause.name !== name) {
        fail(`Malformed advisory for ${name}`);
      } else if (levels.indexOf(cause.severity) > levels.indexOf(entry.severity)) {
        fail(`Inconsistent advisory severity: ${name}`);
      } else roots.add(name);
    }
  }
  const metadata = report.metadata.vulnerabilities;
  for (const level of levels) if (!Number.isInteger(metadata[level]) || metadata[level] !== counts[level]) fail(`Inconsistent ${level} audit count`);
  if (!Number.isInteger(metadata.total) || metadata.total !== Object.keys(vulnerabilities).length) fail('Inconsistent audit total');

  // Every inherited finding must resolve to a real advisory, even in cycles.
  let changed = true;
  while (changed) {
    changed = false;
    for (const [name, entry] of Object.entries(vulnerabilities)) {
      if (!roots.has(name) && entry.via.some(cause => typeof cause === 'string' && roots.has(cause))) {
        roots.add(name); changed = true;
      }
    }
  }
  for (const [name, entry] of Object.entries(vulnerabilities)) {
    if (!roots.has(name)) fail(`Unresolved advisory causality: ${name}`);
    if (levels.indexOf(entry.severity) >= 2) fail(`Blocked ${entry.severity} vulnerability: ${name}`);
  }
  return { blocked: 0 };
}

export function runAudit() {
  const result = spawnSync('npm', ['audit', '--json', '--audit-level=moderate', '--include=dev'], { cwd: appDir, encoding: 'utf8', timeout: 60_000, maxBuffer: 20 * 1024 * 1024 });
  if (result.error || result.signal || ![0, 1].includes(result.status)) fail(`npm audit failed: ${result.error?.message ?? result.stderr ?? result.status}`);
  let report, lock;
  try { report = JSON.parse(result.stdout); lock = JSON.parse(readFileSync(resolve(appDir, 'package-lock.json'), 'utf8')); }
  catch { fail('Could not parse audit report or lockfile'); }
  const assessment = evaluateAudit(report, lock);
  if (result.status !== 0 || assessment.blocked !== 0) fail('npm audit exit status disagrees with report');
  console.log('No moderate or higher npm audit findings.');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { runAudit(); } catch (error) { console.error(`Dependency audit failed: ${error.message}`); process.exitCode = 1; }
}
