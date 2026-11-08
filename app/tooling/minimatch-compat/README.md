# Development-only minimatch bridge

This private package bridges the narrow minimatch API consumed by the app's
current ESLint dependency tree to the real upstream `minimatch` engine, pinned
as `minimatch-core` at **11.0.3**. Every path match delegates to that engine;
this package contains no legacy glob or regex engine. The upstream version is
above the fixed version for [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
The alias identifies the unmodified upstream npm package in the dependency tree.

The ESM default and the value returned by CommonJS `require()` are callable.
The latter uses Node’s synchronous ESM interop and requires Node 20.19 or newer
within the supported 20.x line, or Node 22.12 or newer. The bridge also exposes
`Minimatch` (including `.pattern` and `.match(path, partial)`), `minimatch`,
`filter`, `braceExpand`, `match`, `sep`, and `GLOBSTAR`. Their matching behavior
is minimatch 11 behavior, including its supported options; this is **not** a
promise of general minimatch 3 or 10 semantic equivalence. Callers and glob
patterns outside the tested ESLint configuration need their own compatibility
review, especially on Windows and for unusual negation or `..` patterns.

Minimatch 11 removed the RegExp-producing `makeRe` API. Both `makeRe()` and
`Minimatch#makeRe()` throw an actionable error instead of approximating the
old regex or silently skipping a rule. The installed `eslint-plugin-import`
`no-internal-modules` rule uses that legacy API and must fail visibly if enabled;
it is not enabled in the current app configuration. The legacy `defaults()`
and `Minimatch.defaults()` APIs are also deliberately unsupported and throw;
no inspected installed caller uses them. Do not enable affected rules or rely
on unsupported APIs without replacing the bridge with a verified compatible
upstream solution or implementing and testing an explicit safe migration.

The app's lockfile and scoped npm overrides must resolve this package for the
legacy lint dependencies and the unmodified patched engine for its alias. Clean
installs must keep the adapter inside the app's Docker build context; validate
`npm ci`, the real resolved tree, ESLint configuration and negative rule cases,
audit, and the Node 20 build. Audit success alone does not prove the adapter was
installed or executed correctly.

Remove this bridge when all consuming ESLint packages support a patched upstream
minimatch release directly, and the bridge can be removed while retaining the
same lint rules and their tested behavior. Re-review it whenever ESLint,
plugins, minimatch, npm, Node, configured rules or supported platforms change.
