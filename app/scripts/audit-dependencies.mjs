import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const expiry = Date.parse('2026-11-08T00:00:00Z');
const advisory = 'https://github.com/advisories/GHSA-g3hv-75wg-m249';
const levels = ['info', 'low', 'moderate', 'high', 'critical'];
const allowedPath = 'node_modules/minimatch';
const integrity = 'sha512-VgjWUsnnT6n+NUk6eZq77zeFdpW2LWDzP6zFGrCbHXiYNul5Dzqk2HHQ5uFH2DNW5Xbp8+jVzaeNt94ssEEl4w==';
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = message => { throw new Error(message); };
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

/** Validate npm's graph and allow only the documented, development-only exception. */
export function evaluateAudit(report, lock, now = Date.now()) {
  if (!object(report) || Object.hasOwn(report, 'error') || report.auditReportVersion !== 2 || !object(report.vulnerabilities) ||
      !object(report.metadata?.vulnerabilities) || !object(lock?.packages) || !Number.isFinite(now)) fail('Malformed audit report or lockfile');
  const vulnerabilities = report.vulnerabilities;
  const counts = Object.fromEntries(levels.map(level => [level, 0]));
  for (const [name, entry] of Object.entries(vulnerabilities)) {
    if (!object(entry) || entry.name !== name || !levels.includes(entry.severity) ||
        !Array.isArray(entry.via) || entry.via.length === 0 || !Array.isArray(entry.nodes) || entry.nodes.length === 0) fail(`Malformed vulnerability: ${name}`);
    counts[entry.severity]++;
    for (const node of entry.nodes) if (typeof node !== 'string' || !(node === `node_modules/${name}` || node.endsWith(`/node_modules/${name}`)) || !object(lock.packages[node])) fail(`Unknown lock path: ${node}`);
    for (const cause of entry.via) {
      if (typeof cause === 'string') {
        if (!Object.hasOwn(vulnerabilities, cause)) fail(`Unknown cause ${cause} for ${name}`);
        // npm's inherited edges must be backed by a declared dependency, not a fabricated graph.
        for (const node of entry.nodes) {
          const pkg = lock.packages[node];
          if (![pkg.dependencies, pkg.optionalDependencies, pkg.peerDependencies].some(deps => object(deps) && Object.hasOwn(deps, cause))) fail(`Unresolved edge ${name} -> ${cause}`);
          const resolved = resolveDependency(lock.packages, node, cause);
          if (!resolved || !vulnerabilities[cause].nodes?.includes(resolved)) fail(`Unresolved dependency path ${node} -> ${cause}`);
        }
      } else if (!object(cause) || !levels.includes(cause.severity) || typeof cause.url !== 'string' || cause.name !== name) {
        fail(`Malformed advisory for ${name}`);
      } else if (levels.indexOf(cause.severity) > levels.indexOf(entry.severity)) {
        fail(`Inconsistent advisory severity: ${name}`);
      }
    }
  }
  const metadata = report.metadata.vulnerabilities;
  for (const level of levels) if (!Number.isInteger(metadata[level]) || metadata[level] !== counts[level]) fail(`Inconsistent ${level} audit count`);
  if (!Number.isInteger(metadata.total) || metadata.total !== Object.keys(vulnerabilities).length) fail('Inconsistent audit total');

  let applied = false;
  const reachesRoot = new Set();
  for (const [name, entry] of Object.entries(vulnerabilities)) {
    if (levels.indexOf(entry.severity) < 2) continue;
    if (entry.severity !== 'moderate') fail(`Blocked ${entry.severity} vulnerability: ${name}`);
    for (const node of entry.nodes) {
      const pkg = lock.packages[node];
      if (pkg.dev !== true || pkg.devOptional === true || pkg.optional === true) fail(`Non-development or optional path: ${node}`);
    }
    for (const cause of entry.via) {
      if (typeof cause === 'string') continue;
      if (levels.indexOf(cause.severity) < 2) continue;
      if (name !== 'minimatch' || cause.name !== 'minimatch' || cause.dependency !== 'minimatch' || cause.url !== advisory || cause.severity !== 'moderate' ||
          entry.nodes.length !== 1 || entry.nodes[0] !== allowedPath) fail(`Blocked advisory: ${cause.url}`);
      const pkg = lock.packages[allowedPath];
      if (pkg.version !== '3.1.5' || pkg.integrity !== integrity || pkg.resolved !== 'https://registry.npmjs.org/minimatch/-/minimatch-3.1.5.tgz') fail('Unexpected minimatch lock identity');
      if (now >= expiry) fail('Minimatch exception expired');
      applied = true;
      reachesRoot.add(name);
    }
  }
  // Fixed point handles cycles while requiring every affected node to reach an actual advisory.
  let changed = true;
  while (changed) {
    changed = false;
    for (const [name, entry] of Object.entries(vulnerabilities)) {
      if (!reachesRoot.has(name) && entry.via.some(cause => typeof cause === 'string' && reachesRoot.has(cause))) {
        reachesRoot.add(name); changed = true;
      }
    }
  }
  for (const [name, entry] of Object.entries(vulnerabilities)) {
    if (levels.indexOf(entry.severity) >= 2 && !reachesRoot.has(name)) fail(`Unresolved advisory causality: ${name}`);
  }
  return { exceptionApplied: applied };
}

export function runAudit() {
  const result = spawnSync('npm', ['audit', '--json'], { cwd: appDir, encoding: 'utf8', timeout: 60_000, maxBuffer: 20 * 1024 * 1024 });
  if (result.error || result.signal || ![0, 1].includes(result.status)) fail(`npm audit failed: ${result.error?.message ?? result.stderr ?? result.status}`);
  let report, lock;
  try { report = JSON.parse(result.stdout); lock = JSON.parse(readFileSync(resolve(appDir, 'package-lock.json'), 'utf8')); }
  catch { fail('Could not parse audit report or lockfile'); }
  const assessment = evaluateAudit(report, lock);
  if ((result.status === 0) !== (report.metadata.vulnerabilities.total === 0)) fail('npm audit exit status disagrees with report');
  if (assessment.exceptionApplied) console.log('Raw npm audit is not clean: temporary GHSA-g3hv-75wg-m249 exception for dev-only minimatch 3.1.5, expires 2026-11-08T00:00:00Z.');
  else console.log('No moderate or higher npm audit findings.');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { runAudit(); } catch (error) { console.error(`Dependency audit failed: ${error.message}`); process.exitCode = 1; }
}
