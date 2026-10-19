# Automation handoff — 2026-10-19

- Branch: `feat/automatic-research-report`; base: `cbb58b1`.
- User deferred password/Vercel authentication; do not resume unless asked.
- Modified: `scripts/run_intelligence_daily.py`, new `scripts/build_intelligence_research.py`, daily workflow, `tests/test_intelligence_daily.py`, OPERATIONS_V2 and this file.
- Local validation: 129 Python tests passed. Real data tested in isolated repository copy: four engines + research draft SUCCESS; publication BLOCKED (`STALE_OR_UNAVAILABLE:DTWEXBGS`, `FULL_INPUT_PACKAGE_MISSING`). 11 observed series, 7 signals, 0 allowed ETF candidates while blocked. Existing portal/data source files preserved.
- Research drafts are auditable artifacts, never FULL reports. Current strict FULL confidence and external-evidence contracts unchanged. No speculative scores, invented flows or relaxed freshness.
- Reviewed package now binds calculated outputs and inventory as well as raw sources/rules. Use `--publish-prepared` / workflow input `publish_prepared=true` to publish that exact vintage without regenerating engine timestamps. Scheduled/default flow still computes engines.
- Remaining: fresh dollar observation from original source; source-backed FULL final-analysis implementation; actual ETF holdings, investor flows and comparable competitor inputs; historical calibration. These are not marked complete.
- Notice for follow-up: validation history depth currently counts executions, not independent observation dates (`build_validation_status.py`). Repeated runs must not be treated as extra statistical samples; READY_FOR_HISTORICAL_CALIBRATION still grants no production authorization. Address the counting policy with historical provenance before claiming calibration readiness.
- Next commands: `git fetch origin`; `git log -5 --oneline`; `python -m unittest discover -s tests -q`; inspect latest `data/operations/intelligence.json`, `data/intelligence/research_latest.json` and daily Actions run. Do not run production scripts on the working copy merely to inspect: they mutate calculated histories. Use an isolated copy for exploratory checks.
- Commit identity: `git log -1 --format='%H %s' -- intelligence/AUTOMATION_HANDOFF.md` identifies this checkpoint. CI/merge/deployment outcome will be recorded after completion.
