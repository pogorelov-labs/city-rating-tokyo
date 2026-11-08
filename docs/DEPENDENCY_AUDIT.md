# Dependency audit policy

Run `npm run audit:ci` from `app/`. The command tests the gate and then evaluates
one full `npm audit --json --audit-level=moderate --include=dev` report against
the lockfile. Every moderate, high and critical finding blocks the build,
including development dependencies. Valid low and informational findings do
not block, matching npm's moderate threshold. Registry failures, malformed or
inconsistent reports, unexpected exit statuses, and unresolved dependency
causes fail the gate. No advisory or dependency is currently excepted.

The report validator checks advisory severity and counts, resolves dependency
paths against the lockfile, and recognizes npm aliases by their upstream package
identity. The gate's tests cover the former minimatch advisory, all blocking
severities, low and informational reports, aliases, malformed input, dependency
cycles and npm process errors.

## Historical v0.2.1 exception

The v0.2.1 release temporarily excepted [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)
for the development-only `minimatch` 3.1.5 path until 2026-11-08. That exception
was specific to v0.2.1 and does **not** apply to v0.3.0. The current release
uses the patched minimatch engine with a scoped, fail-closed compatibility
bridge for legacy ESLint callers; see [the bridge documentation](../app/tooling/minimatch-compat/README.md).
The full audit still checks the underlying npm alias and blocks the former
advisory if an affected version returns.
