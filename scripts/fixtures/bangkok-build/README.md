# Bangkok signals snapshot

`signals.json` is the byte-for-byte committed output of the frozen October 2026
refresh at main commit `3698d167788761c81fb5306e34a1f7a7bf50b388`. Its source
inputs are identified by `data/bangkok/refresh-inputs.json`. The snapshot test
protects all district and station-area signal values and metadata during the
build refactor. It does not itself run a full spatial rebuild: that requires the
archived raw inputs described in `scripts/bangkok/README.md`.
