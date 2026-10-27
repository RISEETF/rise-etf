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

## Validation recovery (2026-10-27)
The stop point above is historical. The current revision repairs only the 1.2 metadata contract, using the atomic publisher. The original invalid JSON and unchanged HTML are in data/vintages/2026-10-27 with a revision reason. Research ideas and missing evidence are retained in research_candidates/research_gaps; they are not promoted to approved products or concealed as completed research. All observation dates, values, freshness flags, decision rows and narrative HTML are unchanged. Canonical labels separate the observation date from age; VIX uses the established close label. The existing 7-day oil and 5-day daily-series limits admit the recorded ages on October 27; the dollar remains excluded from today's decision board. This does not certify that the October 27 narrative was newly collected or externally fact-checked.

The publisher's explicit --preserve-existing-report mode requires a revision reason, an existing same-date report, and an exact match to the limited metadata transformation. Arbitrary changes to observations or judgments are rejected. All ordinary staging, archive validation, vintage preservation and rollback remain active. A main-branch push now also triggers snapshot/archive validation so direct updates cannot fail silently (this is detection, not branch protection).

Local verification: 175 Python tests passed, latest snapshot and all 19 archive dates valid. Failed-collection lines printed during tests are injected test scenarios, not live collection outcomes. Raw source files and research validators are unchanged. PR/CI/deployment outcomes must be checked separately.

Resume: branch fix/report-validation-recovery (local), remote PR #70 fix/collection-diagnostics. Run python -m unittest discover -s tests -q; inspect PR #70 checks; merge only after success; inspect Pages deployment and exact latest/daily JSON; then examine KRX diagnostic artifact.

## Post-merge live verification
PR #70 merged as 47c709b9b3dbf466c318b1c087ff02df656e8567 after both PR checks passed (40428581524, 40428581574). Main archive validation 40428744247 succeeded. KRX run 40428744277 succeeded and committed 4eeb8766c3715cebaae61b7f1ec0e6dd228ba813. Daily run 40428744241 generated and validated a complete report, but its push was rejected because the KRX commit arrived first. Its checkout-level PUBLISHED receipt is not a successful public publication; evidence remains in that run artifact.

The follow-up unifies the existing Intelligence collector/engine/publisher locks with the existing primary data-writer concurrency group. All affected workflows check out main at execution time. cancel-in-progress stays false; no forced push or automatic rebase of reviewed report vintages is introduced. GitHub's pending-run coalescing still applies, so this is a mutual-exclusion fix, not an every-event queue guarantee. Recurring schedules and manual workflow dispatch remain recovery paths. Changes by users or other uncoordinated writers still safely reject a stale report push.
