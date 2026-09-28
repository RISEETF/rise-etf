# RISE Intelligence Portal v0.4

JSON-driven decision UI for Daily RISE Market Intelligence.

- `index.html`: portal UI
- `data/latest.json`: canonical current snapshot
- `data/archive.json`: archive manifest
- `data/daily/*.json`: daily snapshots
- `data/framework_history.json`: framework lineage
- `reports/*.html`: full-report drill-down

Pipeline: Full Daily Intelligence → Dashboard Snapshot → validation → daily/latest/archive → full-report HTML → GitHub Pages.


## Freshness governance

The portal must distinguish report/build time from each raw series observation date. A signal computed from a lagged observation remains valid only for that observation vintage and must not be presented as if it were a live market quote. STALE/UNAVAILABLE observations remain explicitly labelled and cannot become current confirmation channels without fresh independent evidence. This display-layer guardrail does not alter signal, episode, regime-gate, market-data, or validation collectors.
