# Publication repair — 2026-10-29

Base: c72ebb619e2256a24a3d58fb2def92aa0cbbafbb. Branch: fix/daily-publication-contract-20261029.

The separate scheduled Daily Intelligence task wrote October 29 report, daily, latest and archive files through multiple commits without executing the canonical validator. Main validation run 40781639860 failed with `invalid dated-data coverage` despite a successful Pages deployment.

The existing publisher's constrained `canonical_repair_metadata` and `preserve_existing_report` mode repaired missing dated-context labels and moved research limitations out of collection blockers. All 11 observation dates/values match the successful October 28 GCLRI source; collection age was below the existing 36-hour gate at repair. These are dated research limitations, not a suppressed collection error. HTML narrative and research values/judgments are unchanged. The previous JSON and HTML are preserved in same-date vintages. This schema repair does not independently validate the report's external news claims.

Twenty publisher/snapshot tests and the full archive validator passed locally. CI, merge and deployment results are recorded in the linked repair PR. Commit success, validation success and public deployment success remain separate.

The existing RISE Daily Intelligence scheduled task (6abda0c8c0ec8191bd56cc0a5b361812) now explicitly requires the integrated publisher, actual Python validation and one atomic PR publication. When its runtime cannot execute these, it must deliver an unpublished chat draft and leave the portal unchanged. Research requirements and schedule were preserved. This is an instruction-level safeguard, not a GitHub branch-protection rule; verify its next run.

Selective PDF continuation: PR #72 is deployed; the October 27 queue has 1,186 ETFs screened, 108 candidates and five PDF_PENDING requests. No actual PDF export has been acquired. The resumed cloud browser on October 29 shows signed-out state; the earlier credential-submission result did not establish a reusable signed-in session. Next: secure KRX authentication, individual PDF export for 0164G0 / 2026-10-27, inspect real schema, then implement validated import. Do not invent an export format or mark holdings verified before retrieval.

Next commands: `python -m unittest tests.test_intelligence_portal tests.test_intelligence_publish -q`; `python scripts/validate_intelligence_snapshot.py intelligence/data/latest.json`. Check the repair PR's CI and exact public JSON before resuming PDF import work.
