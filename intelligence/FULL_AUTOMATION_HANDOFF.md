# FULL automation checkpoint — 2026-10-19

Branch: `feat/automatic-full-report`, base `d16bdcb7da752498f96c95a296f503de4b374cea`.

Implemented: versioned FULL 1.1 bounded research report; null+reason confidence and explicitly unassessed domains; prior regime reference date; exact-input regeneration checks; narrowly scoped dollar exclusion with PARTIAL coverage; no manual inbox overwrite; stable semantic report and same-day vintage preservation; visible portal coverage/unknown labels; CI browser assertion for missing confidence rendering.

Changed: build_intelligence_full.py, run_intelligence_daily.py, validate_intelligence_snapshot.py, update_intelligence_portal.py, daily workflow, dashboard.js, intelligence/index.html, schema documentation, OPERATIONS_V2, tests/test_intelligence_full.py, tests/test_master_portal.cjs, this checkpoint.

Local: 139 Python tests pass. Isolated real-data run: PUBLISHED with 6 usable decision rows, 14 name-based research matches and DTWEXBGS excluded; second actual engine run: UNCHANGED. No raw/history data from the operational checkout was edited during this test. Generated report HTML was inspected for content; browser rendering is checked by PR CI.

Pending until recorded: PR CI, merge, production scheduled-path execution, Pages deployment and public HTTP verification. Do not claim these outcomes from the local test.

Remaining research quality work: verified holdings/exposure, investor-type flow data, competitor comparison, justified product opportunity assessment, independent-observation historical calibration. No investment or framework promotion. Password deferred.

Resume: `git fetch origin`; inspect PR/status and `data/operations/intelligence.json`; `python -m unittest discover -s tests -q`. Production CLI is `python scripts/run_intelligence_daily.py` (mutates calculated outputs); use isolated checkout for experiments. Prepared manually reviewed package mode remains `--publish-prepared`.

Checkpoint commit can be identified with `git log -1 --format='%H %s' -- intelligence/FULL_AUTOMATION_HANDOFF.md`.
