#!/usr/bin/env bash
#
# refresh-ratings.sh — one-command rating pipeline refresh
#
# Chains: compute-ratings.py → export-ratings.py → optional commit + push
#
# Usage:
#   scripts/refresh-ratings.sh              # compute, export, verify, offer to commit
#   scripts/refresh-ratings.sh --auto       # compute, export, commit without prompting
#   scripts/refresh-ratings.sh --push       # also push to current branch
#   scripts/refresh-ratings.sh --dry-run    # compute with --dry-run, no NocoDB writes
#   scripts/refresh-ratings.sh --no-build   # skip Next.js build verification
#
# Safety:
# - Refuses to run if the working tree has unrelated dirty files
# - Refuses to push to main unless --force-main is passed
# - Never uses --amend or force push
#

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AUTO=0
PUSH=0
DRY_RUN=0
DO_BUILD=1
FORCE_MAIN=0

for arg in "$@"; do
    case "$arg" in
        --auto) AUTO=1 ;;
        --push) PUSH=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --no-build) DO_BUILD=0 ;;
        --force-main) FORCE_MAIN=1 ;;
        -h|--help)
            sed -n '3,17p' "${BASH_SOURCE[0]}" | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo "unknown flag: $arg" >&2
            exit 2
            ;;
    esac
done

# ANSI helpers
bold() { printf '\033[1m%s\033[0m' "$*"; }
green() { printf '\033[32m%s\033[0m' "$*"; }
yellow() { printf '\033[33m%s\033[0m' "$*"; }
red() { printf '\033[31m%s\033[0m' "$*"; }
step() { echo; echo "$(bold "==>") $(bold "$*")"; }
ok() { echo "    $(green "✓") $*"; }
warn() { echo "    $(yellow "⚠") $*"; }
die() { echo "    $(red "✗") $*" >&2; exit 1; }

# ---- 1. Preflight ----
step "Preflight checks"

command -v python3 >/dev/null || die "python3 not found"
python3 -c "import requests" 2>/dev/null || die "python3 'requests' module not installed"
ok "python3 + requests available"

[[ -f scripts/compute-ratings.py ]] || die "scripts/compute-ratings.py not found"
[[ -f scripts/export-ratings.py ]] || die "scripts/export-ratings.py not found"
ok "pipeline scripts found"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
ok "current branch: $CURRENT_BRANCH"

if [[ "$CURRENT_BRANCH" == "main" && "$PUSH" == 1 && "$FORCE_MAIN" != 1 ]]; then
    die "refusing to push directly to main — use a feature branch or pass --force-main"
fi

# Check that the working tree has only the allowed dirty files (demo-ratings.ts)
DIRTY="$(git status --porcelain 2>/dev/null | grep -v '^?? \.claude/worktrees/' | awk '{print $2}' || true)"
ALLOWED_DIRTY="app/src/data/demo-ratings.ts"
for f in $DIRTY; do
    if [[ "$f" != "$ALLOWED_DIRTY" ]]; then
        die "unrelated dirty files in working tree (e.g. $f) — commit or stash first"
    fi
done
ok "working tree clean (or only demo-ratings.ts modified)"

# ---- 2. Compute ----
step "Running compute-ratings.py$([[ $DRY_RUN == 1 ]] && echo ' (dry-run)')"
if [[ "$DRY_RUN" == 1 ]]; then
    python3 scripts/compute-ratings.py --dry-run
else
    python3 scripts/compute-ratings.py
fi
ok "compute done"

# ---- 3. Export ----
step "Running export-ratings.py"
if [[ "$DRY_RUN" == 1 ]]; then
    python3 scripts/export-ratings.py --dry-run
    warn "dry-run: demo-ratings.ts NOT written"
    exit 0
fi
python3 scripts/export-ratings.py
ok "demo-ratings.ts updated"

# ---- 4. Build verification ----
if [[ "$DO_BUILD" == 1 ]]; then
    step "Verifying Next.js build"
    if ! command -v npx >/dev/null; then
        warn "npx not found — skipping build verification"
    else
        (cd app && npx next build) > /tmp/refresh-ratings-build.log 2>&1 || {
            echo
            tail -40 /tmp/refresh-ratings-build.log
            die "build failed — see /tmp/refresh-ratings-build.log"
        }
        ok "build passed"
    fi
else
    warn "skipping build verification (--no-build)"
fi

# ---- 5. Diff check ----
step "Checking demo-ratings.ts changes"
if git diff --quiet -- app/src/data/demo-ratings.ts; then
    ok "no changes — nothing to commit"
    exit 0
fi

LINES_CHANGED="$(git diff --numstat -- app/src/data/demo-ratings.ts | awk '{print $1 "+/" $2 "-"}')"
ok "changes detected ($LINES_CHANGED)"

# ---- 6. Commit ----
if [[ "$AUTO" != 1 ]]; then
    echo
    read -r -p "    Commit demo-ratings.ts? [y/N] " reply
    case "$reply" in
        y|Y|yes) ;;
        *) warn "skipped commit"; exit 0 ;;
    esac
fi

step "Committing"
DATE_TAG="$(date +%Y-%m-%d)"
git add app/src/data/demo-ratings.ts
git commit -m "chore(data): refresh computed ratings ($DATE_TAG)

Regenerated via scripts/refresh-ratings.sh:
- compute-ratings.py → NocoDB computed_ratings
- export-ratings.py → app/src/data/demo-ratings.ts"
ok "committed"

# ---- 7. Push ----
if [[ "$PUSH" == 1 ]]; then
    step "Pushing to origin/$CURRENT_BRANCH"
    git push -u origin "$CURRENT_BRANCH"
    ok "pushed"
else
    warn "not pushing (pass --push to auto-push)"
    echo "    Next step: git push"
fi

echo
echo "$(bold "$(green '✓ refresh complete')")"
