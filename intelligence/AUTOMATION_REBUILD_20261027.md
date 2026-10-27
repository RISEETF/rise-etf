# Automation recovery — 2026-10-27

User priority: complete data collection and refresh before adding menus or migrating hosts. Keep provider names out of operational UI; retain original provenance in source records. Prior reports and research rules are not rewritten.

## Verified diagnosis
- Daily workflow receipt: PUBLISHED for 2026-10-26; four engines, research draft, FULL report and publisher succeeded. Latest report was separately updated to 2026-10-27; report date is not proof that every underlying dataset refreshed.
- KRX run 40357042965 failed KRX_FIELD_COVERAGE_LOW. Existing status discarded the field and ratio, preventing evidence-based repair. New structured diagnostics retain field coverage and allowlisted API field-presence counts without secrets, while leaving the 95% gate unchanged.
- US directory workflow collects into an artifact; explorer accepts manual JSON. There is no automatic artifact-to-portal publication.
- Personal supplementary data uses browser memory/optional IndexedDB. This is retention, not an unattended ingestion service.
- A successful Pages deployment only proves hosting, not source collection or analytical readiness.

## Rebuild sequence
1. Restore primary collection: inspect new KRX diagnostics, fix only demonstrated schema/response defects, preserve rejected captures and last-good data. Do not reduce thresholds simply to get a green run.
2. Introduce a validated portal snapshot for public permitted datasets: collection -> immutable source capture -> validation -> history -> one versioned portal snapshot. Automate the US directory connection and expose status/date per dataset. Separate dataset health from report publication status.
3. KRX all-market master first, issuer details second. Add observed prices/NAV/AUM only with units/date/source, then comparable-period returns. AUM changes are not investor net flows.
4. Replace file-dependent personal imports with an authenticated ingestion/store only when a suitable private execution/storage route is established. Keep current manual pipeline as fallback. Provider website login and export permissions remain separate from a technical parser.
5. Activate analytical sections by evidence: price/identity modules can use validated primary inputs; flow needs investor-type flows; regime confidence and product evaluation require their documented validation. Nulls must not be converted to zero or invented scores.

## Delivery rules
One collection outcome per source, one last-success timestamp, observation date separate from acquisition, immutable history, atomic last-good snapshot, failure details and publication verification. Run collection in existing GitHub Actions first; keep Python engines and publisher. Cloudflare/auth migration is deferred, not a prerequisite for current public-data automation.

This change adds diagnosis and neutral UI labels. It does not claim KRX recovery, automatic provider downloads or US portal publication until actual runs verify them. Next commands: python -m unittest tests.test_krx_etf tests.test_provider_inbox -v; inspect data/krx_collection_status.json after KRX workflow; use source_field_present_rows and failed_fields to select the repair. Current branch fix/collection-diagnostics; implementation commit and Actions evidence are in its PR.

## Verification stop point
PR #70 head 4fcea08aba68acc9bd47aeb1f42c91edb4394751 is committed but not merged. Targeted tests: 17 passed. Full CI 40424498580 failed (173 tests, 9 failures/1 error); snapshot CI 40424498567 failed. Both expose pre-existing 2026-10-27 latest/daily snapshot contract violations: product_candidates populated under bounded report, research gaps placed in collection blockers, noncanonical unverified exposure basis, and age suffixes inside exact asof_label. Report text also discusses dated observations, so changing only labels is insufficient to certify analytical consistency.

Do not bypass tests or change research conclusions just to merge. The 2026-10-27 report and raw snapshots have not been altered. Next repair must preserve original JSON/HTML as vintage, reconcile the report schema and evidence with the existing atomic publisher, then rerun full validation. Only then merge PR #70 and inspect its triggered KRX diagnostic run. UI source-label change is prepared but not deployed.
