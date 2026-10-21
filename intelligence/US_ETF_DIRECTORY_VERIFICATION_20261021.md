# US directory execution checkpoint

Branch main; implementation merge d68429c122d1a52a15bec7dd95209d67f06ba326, PR #59.

- 168 local Python tests passed.
- PR Actions 39554315794 and 39554315862 succeeded.
- Production collection 39554431350 succeeded on 2026-10-21 at 15:16 KST. Logged count 5,776; directory date 2026-10-20; duplicate=false.
- Artifact us-etf-state uploaded successfully, 580,643 bytes, containing raw files, history.sqlite, latest.json and receipts. Scheduled Tuesday–Saturday 11:23 KST; next scheduled invocation has not yet occurred.
- No login/API key needed. Previous-run artifact restore is implemented but first-run success does not prove a subsequent restore execution. Retention is 90 days, with cumulative history carried forward by successful runs. Archive expiration after a long interruption requires manual recovery; never reset silently.
- No portal metric or KRX/RS changes. Fees, holdings, AUM, returns, legal structure and delisting confirmation remain unresolved. Directory date is not a closing-price date.

Resume: git pull --ff-only origin main; python -m unittest tests.test_us_etf_directory -v; python scripts/collect_us_etf_directory.py. See US_ETF_DIRECTORY_HANDOFF.md. All implementation files committed; local raw outputs stay in ignored var/us_etf_directory. Verify next Actions run restores the prior artifact and reports duplicate or a new preserved snapshot.
