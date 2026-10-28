# ETF selective PDF investigation — 2026-10-28

User decision: do not bulk-download all ETF PDFs or substitute index holdings. Screen the KRX universe using daily price/volume/NAV and request actual KRX PDF only for a few anomalous ETFs.

## Implemented scope
The existing KRX workflow restores its SQLite history, validates and collects official daily data, then runs build_etf_investigations.py. It publishes at most five deduplicated research candidates with dates, evidence and PDF_PENDING. Thresholds (absolute price change 5%, absolute close/NAV gap 2%, volume 3x prior 20 observations) are provisional triage rules, not calibrated trading signals. Ranking is number of triggers then maximum normalized threshold exceedance. The deferred count is explicit. New listings/missing history never become a zero baseline; today's volume is excluded from its baseline. Latest same-date revisions are selected. No fund-flow or holdings attribution is inferred.

Successful queue snapshots are content-addressed by date; latest is replaced atomically after validation. Failures keep the prior queue and record an attempt status. The ETF detail/explorer page loads the queue automatically and marks PDF pending and collection failures. Source collector failure skips screening and is separately surfaced from krx_collection_status.json.

## Publication blocker repaired
Main's manually published October 28 snapshot used PARTIAL_STALE_INPUTS and placed incomplete context rows in schema 1.2. The existing run_intelligence_daily.py was executed against the repository's successful October 28 source collection. All four engines, draft, canonical full report and atomic publisher succeeded. The prior JSON/HTML is preserved under intelligence/data/vintages/2026-10-28. Raw source data and validator rules are unchanged. A local execution receipt identifies the run explicitly; it is not claimed as an Actions execution. This is a newly generated canonical report, not a metadata-only edit of the manual narrative.

## Verification and boundaries
180 Python tests passed locally, including five triage tests covering window exclusion, revisions, bounded selection, missing history, stale/future receipt and last-good preservation. Browser integration adds synthetic queue/XSS verification; CI checks its result. Actual KRX screening, commit and deployment must each be verified after merge.

PDF login/download and import/analysis are not implemented by this change. No holdings are fabricated and no state is marked ANALYZED. Next: take one real queue ticker/date into KRX's PDF screen, authenticate if required, download the actual table, inspect its schema, then reuse private import/history conventions. Credentials and tokens must not be committed. A known PDF export schema is required before writing an importer. UI remains concise on the homepage; investigation details are on etf.html.

Branch: feat/etf-investigation-queue. Next commands: python -m unittest discover -s tests -q; node tests/test_etf_explorer.cjs; inspect PR checks, then inspect KRX workflow receipt and data/etf_investigations/latest.json after merge. Commit and Actions evidence are recorded in the PR.
