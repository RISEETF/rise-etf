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

Contract version is `schema_version: "1.0"`; unversioned historical files are
read as version 1.0. Unknown versions fail validation. New routine publications
write the version explicitly. FULL retains all required decision fields.

SUMMARY_ONLY requires type, report date, market date, regime text/status, top
change, report path, and a timezone-aware generation timestamp. Optional fields
are explicitly listed in `SUMMARY_OPTIONAL` in the shared validator: risk, flow,
RISE/product mappings, research notes, triggers, non-actions and provenance/status.
Their types are validated. Unknown fields require a contract change, rather than
being silently ignored. Confidence and regime-history gates remain FULL-only;
a summary cannot declare production eligibility. RESEARCH_REQUIRED means research
is outstanding and is not a framework promotion. The UI displays supplied optional
information and labels absent fields as unavailable; chart gaps remain unfilled.

A null report path requires SUMMARY_ONLY_FULL_REPORT_PENDING or HTML_PUBLISH_BLOCKED.
A published path must be `reports/<asof_date>.html`; pending status and a live path
cannot coexist. Archive validation checks linked files and accepts explicit pending
reports without creating false links. `latest.json` must equal the latest daily file.

`SUMMARY_ONLY` is retained only for historical/read-only or emergency compatibility. Routine Daily Intelligence publishing MUST use the canonical FULL snapshot and is rejected by `update_intelligence_portal.py` when a summary snapshot is supplied. This preserves the operating rule: Full Daily Intelligence → canonical Dashboard Snapshot → validation → publication.

Validate with `python scripts/validate_intelligence_snapshot.py intelligence/data/latest.json`
before publishing. Adding the summary type does not upgrade or invent evidence.
Full PR CI and the dedicated intelligence workflow retain report validation.
The scheduled master and price/FX collectors run their dependency tests separately
so report-format failures do not halt independent market observations.

`data/operations/{master,series}.json` records workflow step outcomes, including
failures before a collector starts. Immutable run receipts are kept under runs/.
Source receipts and last successful snapshots remain separate. These receipts
cannot report checkout failure, abrupt runner termination, or a failed Git push;
GitHub Actions remains the authority for final job/publication success.


## Freshness governance

The portal must distinguish report/build time from each raw series observation date. A signal computed from a lagged observation remains valid only for that observation vintage and must not be presented as if it were a live market quote. STALE/UNAVAILABLE observations remain explicitly labelled and cannot become current confirmation channels without fresh independent evidence. This display-layer guardrail does not alter signal, episode, regime-gate, market-data, or validation collectors.
