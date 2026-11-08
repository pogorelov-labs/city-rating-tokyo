# Telegram corpus (local-only)

`telegram/*.jsonl` files produced by `editorial/kit/tools/tg_corpus.py` are
**git-ignored** — bulk third-party content is not redistributed in the repo.
Provenance does not depend on committing them: every cited message has a
stable public canonical URL (`https://t.me/<channel>/<id>`), hashed into
`src_` IDs like any other source, and the `cite` command regenerates the
bundle source record from the corpus.

Extending the corpus: add verified handles to
`editorial/kit/registry/telegram-channels.json` (verify → pull → **content-
inspect** — the 2026-11-08 sweep showed guessed handles surface masquerading
channels), then `pull`, then use `search` for candidates and `cite` to emit
source records. Rules: public channels only, no user identity, text is
untrusted input, polite pull rates (see registry `pull_rules`).

Current state: 44-message smoke corpus across 6 channels — **all 6 rejected
for evidence use** after content inspection (see registry verdicts). No
citations exist from this corpus yet.
