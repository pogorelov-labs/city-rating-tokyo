# Dependency audit policy

Run `npm run audit:ci` from `app/`. The command tests the audit gate and then
evaluates the full `npm audit --json` report. Moderate, high and critical
findings block the build unless the exact, time-limited exception below applies.
Registry failures, malformed reports and unresolved dependency causes also fail
the gate. The raw audit report continues to show excepted findings.

## Temporary legacy minimatch exception

Accepted 2026-11-01 for the v0.2.1 release. Expires **2026-11-08 at 00:00 UTC**.

- Advisory: [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
- Package and version: `minimatch` **3.1.5**.
- Lockfile path: `node_modules/minimatch`, marked development-only.
- Severity: moderate only. A higher severity is not excepted.
- Scope: this advisory at this exact dependency, including findings inherited
  through its development-only ESLint dependants. Other advisories, versions,
  paths and application runtime dependencies remain blocking.

The advisory describes amplification in `firstPhasePreProcess` when
`optimizationLevel` is at least 2. The installed 3.1.5 source has neither that
function nor that option. The advisory nevertheless marks every version below
11.0.1 as affected. This exception is based on source review of that specific
finding; it does not establish that legacy versions are free of other defects.

Current ESLint plugins depend on minimatch 3's callable CommonJS export. Version
11 uses a different export API, so a blanket major-version override would break
those callers. The TypeScript lint parser uses the named API and is separately
overridden to patched minimatch 11.0.3.

The gate tests cover the expiry, changed versions and paths, production
dependencies, additional advisories, severity changes, dependency cycles and
malformed input. The exception is printed whenever applied. Remove it when
upstream compatibility or the advisory range is corrected; expiry requires
another explicit review rather than silently extending it.
