# US ETF directory collection — 2026-10-21

Source: https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt and otherlisted.txt.
Definitions: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs

Actual initial download: 2026-10-21 UTC; both source creation stamps 2026-10-20 21:31 (source timezone not independently established). 5,776 ETF-flagged non-test securities. This is a directory universe, not a validated count of registered investment-company ETFs. ETNs, trusts and other ETP structures need separate classification. It is not a price or closing-price dataset. FunETF's observed US screen count is not a matching universe and is not treated as an error automatically.

Implementation: scripts/collect_us_etf_directory.py; tests/test_us_etf_directory.py; .github/workflows/us_etf_directory.yml. No KRX or existing RS rules changed. Output defaults to ignored var/us_etf_directory: immutable SHA256 raw files, transactional SQLite snapshots, latest.json and per-run receipts. Source dates must agree; future/stale dates, schema/flag errors, duplicates and >20% count drops are rejected. Missing symbols are review candidates, never automatically confirmed delistings. Source timestamps and download time are distinct. Snapshot deduplication uses both complete raw hashes.

Schedule: Tuesday–Saturday 11:23 Asia/Seoul, subject to GitHub delays; manual dispatch and implementation push also run. No login/key required. Each run restores last successful artifact, collects both files, and uploads history plus receipts with 90-day retention. A missing/expired previous artifact blocks restore instead of silently resetting history. Artifacts in this public repository are not a confidential storage system. Long interruptions require a backed-up artifact restore. No continuously running local process is required for Actions.

Resume commands:
```
git pull --ff-only origin main
python -m unittest tests.test_us_etf_directory -v
python scripts/collect_us_etf_directory.py
```

The collection result is a separate US directory; no unsupported fee/AUM/return/holding values are published to the portal. Next: legal structure classification, issuer details, and adjusted price/dividend histories before RS integration. Workflow/commit/deployment status must be checked separately; initial local collection success alone is not scheduled execution evidence.
