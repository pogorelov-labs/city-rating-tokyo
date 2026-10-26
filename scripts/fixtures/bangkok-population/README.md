# Bangkok population snapshots

`adoption/` contains exact committed Bangkok files from
`d7e2ddf5c5d906e155e0f310015f45441360fa06`, before the spatial refresh. They
retain the historical adoption replay and normalization characterization,
including the already reviewed rent scope. The immutable historical baseline
remains `data/bangkok/population-baseline.json`; its signatures are unchanged.

The current snapshot is the generated app/data output, tested against
`data/bangkok/population-baseline-refresh-2026-10-24.json`. Replay requires an
explicit `--baseline adoption` or `--baseline refresh-2026-10-24`. The historical
baseline deliberately rejects current geometry rather than weakening its guard.

`provenance-only.json` freezes release-snapshot fingerprints of the shared
institutions/noise documents, excluding only authorized Bangkok input-hash
fields. It proves that no other Tokyo/shared metadata or values changed.
