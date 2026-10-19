# Dated-data reporting checkpoint — 2026-10-20

User instruction: continue through completion; use last available close/observation with its date instead of blocking simply for publication delay. No pending user decision identified. Password remains deferred.

Branch: feat/dated-data-reporting. Base: 0101323 (includes a separate October 20 draft README; retained unchanged).

Implementation: FULL 1.2 DATED_OBSERVATIONS_V1, keeping historical 1.0/1.1 contracts. Successfully fetched dated values must match the fetched history tail. Their dates, levels, elapsed days and prior-observation deltas are shown in the report; they cannot support current signal decisions or ETF signal matches. All-dated reports explicitly withhold current judgments. Invalid/missing/future/error data and stale collection execution still block. Collector adds source URL, retrieval timestamp and success metadata. Portal labels distinguish dated values from unavailable analysis; VIXCLS close classification verified against official FRED metadata.

Changed files: build_intelligence_full.py, collect_gclri_market.py, run_intelligence_daily.py, validate_intelligence_snapshot.py, update_intelligence_portal.py, dashboard.js, intelligence/index.html, schema.json, OPERATIONS_V2, full-report tests, browser label assertion and this checkpoint.

Local tests: 146 Python tests pass, including all-dated publication, delayed rates over 14 days, invalid source/tail/date rejection, collection-failure preservation, dated-value/previous-change tampering rejection and old 1.1 behavior. Browser tests are run in GitHub CI. Live isolated collection started; result is not yet claimed. PR/merge/runtime/deployment/public-byte checks must be recorded after completion.

Remaining outside this change: verified holdings/exposure, investor flows, competitor metrics and independently observed historical calibration. Dated reference values are not today's prices. Do not erase prior reports or source histories.

Resume: git fetch origin; inspect branch/PR/latest operations; python -m unittest discover -s tests -q. Use an isolated checkout for collector/engine experiments. Production path: existing GCLRI collection workflow -> daily workflow -> versioned report -> validate -> single publication commit -> Pages.

Checkpoint identity: git log -1 --format='%H %s' -- intelligence/DATED_DATA_HANDOFF.md
