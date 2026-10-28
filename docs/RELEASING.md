# Releasing City Rating

## Policy and prerequisites

- Use semantic versions with a `v` tag prefix. The first release was **v0.1.0**.
  **v0.1.1** was the first patch data release, packaging the post-v0.1.0 Bangkok
  refresh. That release bumped `app/package.json` and `app/package-lock.json`
  from `0.1.0` to `0.1.1`.
  **v0.1.2** packages compatible map/scoring fixes and Bangkok MCP district tools;
  its release PR bumps the same two files from `0.1.1` to `0.1.2`.
  During 0.x, use a minor version for incompatible behavior or substantial
  features and a patch for compatible fixes. After 1.0, incompatible changes
  require a major version. Make any future package-version changes explicit.
- Release from a **clean, reviewed main commit** through a PR and a **merge
  commit**. Do not release a branch head, a dirty checkout or a failing main.
- All four jobs in [CI](../.github/workflows/ci.yml) must pass on the PR and
  again on the exact main merge SHA: **`build`, `schema`, `mcp`, `bangkok`**.
  `build` covers lint, UI tests, TypeScript, the Next build and runtime audit;
  `schema` covers codegen drift and pipeline/parity tests; `mcp` covers lint
  and unit tests with offline fixtures; `bangkok` covers offline pipeline/data tests.
  MCP production smoke checks are separate and are not implied by green CI.
- Update [CHANGELOG](../CHANGELOG.md), `docs/releases/<tag>.md`, README and any
  affected methodology/developer docs before merging. Notes must name known
  limitations and distinguish code availability from published data freshness.
- **Public release copy:** This repository is public. Changelog and release
  notes describe user-visible changes, compatibility and user-impacting limits.
  Do not include internal infrastructure or deployment details: host/service
  names, deployment platform, host, container, or orchestrator names, network
  topology, private URLs, credentials, worker/session identifiers, CI run IDs or
  internal QA artifacts. Do not paste engineering receipts such as hashes, manifests or
  internal gate lists; put technical evidence in a research note or the PR body
  and link it. Release notes in `docs/releases/<tag>.md` follow the same rules.
- Never put secrets, credentials, private host details or raw caches in notes.
  Never mix regenerated data with a code/docs release. A data refresh has a
  separate PR, review and acceptance process (see below).

## 1. Prepare and review the documentation

From the repository root, authenticate with `gh auth status`, fetch origin and
confirm the worktree is clean with `git status --short`. Start a release-docs
branch from the intended `origin/main` commit; in AO use the session namespace.
For v0.1.0 the starting commit is `f30fb329810b0a6fce94bf2622312a96cc0729a4`.

Write a dated changelog entry and the release body. Include product scope,
sources/attribution, known limitations and deployment implications. Update
targeted docs rather than replacing the project guides. Check the diff:

```sh
git diff --check
git diff --stat origin/main
git diff --name-only origin/main
```

List any approved app-version bump explicitly in the release PR. From `app/`,
`npm version <version> --no-git-tag-version` updates the package and lock metadata;
inspect that only the intended version fields changed. A docs-only release has
no package changes. Review and remove accidental `next-env.d.ts`, sitemap,
dependency, generated-data or grid-binary drift; do not discard another
contributor's changes. **Do not run a data build** to prepare a code/docs release.
Commit and push the release-preparation branch, then open:

```sh
gh pr create --base main --title "docs: release v0.1.0 and release runbook" --body-file /path/to/pr-body.md
```

Review the published PR diff and discussion. Wait for all four jobs, including
checks not enforced by branch protection:

```sh
pr_number=<docs-pr-number>
pr_head=$(gh pr view "$pr_number" --json headRefOid --jq .headRefOid)
gh pr checks "$pr_number" --watch
gh pr view "$pr_number" --json headRefOid,statusCheckRollup,mergeable,reviewDecision
```

Verify the head still equals `pr_head`, all four named jobs concluded success
and all required review feedback is addressed. If the head changes, repeat
verification. A missing, skipped, cancelled or failed job is not a pass.

## 2. Merge and verify main

Merge only the release-docs PR, without bypassing checks or protections:

```sh
gh pr merge "$pr_number" --merge --match-head-commit "$pr_head"
release_sha=$(gh pr view "$pr_number" --json mergeCommit --jq .mergeCommit.oid)
git fetch origin
git show --no-patch --format=fuller "$release_sha"
git rev-list --parents -n 1 "$release_sha"
git rev-parse origin/main
```

Confirm the SHA has two parents and is the expected main merge commit. If main
advanced unexpectedly, inspect the new changes and coordinate before releasing;
never silently tag a different commit. Ensure the release notes read below are
the ones committed at `release_sha` and the worktree is clean.

Find the **push** workflow for this exact commit, not the earlier PR run:

```sh
gh run list --workflow ci.yml --event push --commit "$release_sha" --json databaseId,headSha,status,conclusion,url
main_run=<matching-run-id>
gh run watch "$main_run" --exit-status
gh run view "$main_run" --json headSha,conclusion,jobs,url
```

Confirm `headSha` equals `release_sha` and `build`, `schema`, `mcp`, `bangkok`
each succeeded. If the run has not appeared, wait for it. On failure, stop the
release; fix only an in-scope docs issue in a new PR or escalate an unrelated
failure. Repeat the merge/main gates on the eventual release commit.

## 3. Create an annotated tag and publish the release

Set the version explicitly. Check that neither the remote tag nor release
already exists; an existing published version must not be overwritten.

```sh
release_tag=v0.1.0
git ls-remote --tags origin "refs/tags/$release_tag" "refs/tags/$release_tag^{}"
gh release list
git tag -a "$release_tag" "$release_sha" -m "v0.1.0 — City Rating: Tokyo + Bangkok"
git cat-file -t "$release_tag"
git rev-parse "$release_tag^{commit}"
git push origin "refs/tags/$release_tag"
gh release create v0.1.0 --target "$release_sha" --title "v0.1.0 — City Rating: Tokyo + Bangkok" --notes-file docs/releases/v0.1.0.md --latest --verify-tag
```

`git cat-file` must report `tag`; the peeled commit must equal `release_sha`.
Create and push the annotation first because `gh release create` alone can
create a lightweight tag. `--verify-tag` prevents creating a missing remote
tag, and `--target` records the exact release commit. For later releases,
replace the version, title, annotation and notes path together.

If tag push succeeds but release creation fails, verify the remote tag and
resume release creation at that same SHA. Do not move the tag. Investigate a
pre-existing tag/release before retrying rather than deleting it automatically.

## 4. Verify tag, release and production

```sh
gh release view v0.1.0 --json tagName,targetCommitish,url,isDraft,isPrerelease
gh api repos/pogorelov-labs/city-rating-tokyo/releases/latest --jq '{tagName: .tag_name, url: .html_url}'
git fetch origin tag v0.1.0
git cat-file -t v0.1.0
git rev-parse 'v0.1.0^{commit}'
git ls-remote --tags origin 'refs/tags/v0.1.0' 'refs/tags/v0.1.0^{}'
gh run view "$main_run" --json headSha,conclusion,jobs,url
curl --fail --silent --show-error --location --max-time 30 --output /dev/null --write-out '%{http_code} %{url_effective}\n' https://city-rating.pogorelov.dev
```

Confirm the release is published, is not a prerelease, targets `release_sha`,
and `/releases/latest` names v0.1.0. `gh release view --json
tagName,targetCommitish,isLatest,url` may work in other CLI versions; when
`isLatest` is unsupported, use the `/releases/latest` API above. For an annotated
tag, the unpeeled ref is the **tag object SHA**; the `^{}` ref is the **release
commit SHA**. Record both and ensure the latter equals `release_sha`.

Production deployment is automated from `main`; publishing a tag does not
initiate a manual deployment. The app uses build-time static city pages/JSON.
v0.1.2 needs **no database migration**. Check production deployment status/logs
and the deployed commit through private maintainer tooling when access is
available; never infer deployment completion from CI or HTTP 200 alone. Do not
deploy manually for this release. Smoke-check Tokyo, Bangkok and locale
navigation at the public production URL. Record HTTP status, CI links and
anything that could not be verified.

After verification, announce the version with its release link, highlights and
known limitations in the approved channel. Obtain channel/recipient approval
before sending an external announcement if it was not already authorized.

## Rollback and hotfix

Keep published tags and notes auditable; do not force-push main or retag a
published version. For a regression, stop promotion/announcement, record the
affected SHA and open a focused revert or hotfix PR. Pass all four gates and
merge normally; production deployment then updates from `main`. A maintainer
may use an approved production rollback through private maintainer tooling
during an incident, but that is a separate authorized action, not part of this
release procedure. Reconcile any rollback with main afterwards.
Publish a new patch version (for example v0.1.3) for the fix and link the incident
or superseded release in its notes. Do not rerun data pipelines as a rollback.

## Data refresh separation

The [Bangkok remediation record](DATA_REFRESH_REMEDIATION.md) documents the
completed refresh, merged separately after v0.1.0 and packaged by v0.1.1. The
v0.1.0 tag and release body remain unchanged. Future data-refresh PRs must freeze
inputs, preserve enrichments, validate deliberate new baselines, review source
rights/attribution, and provide reproducibility and visual evidence. Historical
fixtures remain historical. Update the changelog after the data PR is accepted;
never fold regenerated data into a code/docs release.

## Release checklist

- [ ] Version, dated changelog, release body and affected docs agree; no secrets.
- [ ] Worktree clean; release-preparation diff checked; only docs and approved
  version metadata changed, with no generated-data drift.
- [ ] PR reviewed; `build`, `schema`, `mcp`, `bangkok` all pass at the recorded head.
- [ ] Merged with a merge commit and head-match guard; merge SHA recorded.
- [ ] Main push CI passes all four jobs at that exact SHA.
- [ ] Annotated remote tag peels to the merge SHA; no existing version overwritten.
- [ ] GitHub release is published/latest with the committed notes and correct target.
- [ ] Public production URL returns 200; Tokyo/Bangkok/locales checked; production
  deployment status recorded or explicitly listed as unverified; no manual
  deploy or DB migration.
- [ ] Approved announcement sent, or its pending status recorded.
- [ ] PR, CI, release, tag object/commit SHAs and verification limits reported.
