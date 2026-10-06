# RISE Intelligence Portal v0.4

JSON-driven decision UI for Daily RISE Market Intelligence.

- `index.html`: portal UI
- `data/latest.json`: canonical current snapshot
- `data/archive.json`: archive manifest
- `data/daily/*.json`: daily snapshots
- `data/framework_history.json`: framework lineage
- `reports/*.html`: full-report drill-down

Pipeline: Full Daily Intelligence → Dashboard Snapshot → validation → daily/latest/archive → full-report HTML → GitHub Pages.

## Snapshot contracts

Full snapshots retain all required decision fields. A report-link summary must
explicitly declare `snapshot_type: SUMMARY_ONLY` and contain the report date,
market date, regime text/status, top change, dated local report path, and a
timezone-aware generation timestamp. Summary snapshots do not provide confidence,
transition-gate decisions, product mappings, or framework changes. The UI labels
these fields as unavailable and leaves historical chart gaps unfilled.

Validate with `python scripts/validate_intelligence_snapshot.py intelligence/data/latest.json`
before publishing. Adding the summary type does not upgrade or invent evidence.
Full PR CI and the dedicated intelligence workflow retain report validation.
The scheduled price/FX collector runs its market-data dependency tests separately
so report-format failures do not halt independent market observations.


## Freshness governance

The portal must distinguish report/build time from each raw series observation date. A signal computed from a lagged observation remains valid only for that observation vintage and must not be presented as if it were a live market quote. STALE/UNAVAILABLE observations remain explicitly labelled and cannot become current confirmation channels without fresh independent evidence. This display-layer guardrail does not alter signal, episode, regime-gate, market-data, or validation collectors.
