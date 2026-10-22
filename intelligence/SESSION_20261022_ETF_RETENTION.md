# ETF local retention checkpoint — 2026-10-22

Branch main; implementation merge e0decb118a161637a90eee682f053a83093d5506, PR #61. Head b7639827241433c2bcd0b3c2165c6c67a35f3b19. Files: etf.html, etf.js, tests/test_etf_explorer.cjs, intelligence/PRIVATE_PROVIDER_GUIDE.md.

CI 39709847449 and 39709847554 passed. Includes full Python suite and browser tests: opt-in IndexedDB save/reload, invalid future timestamp rejected with previous data preserved, clear/reload, existing comparison and no POST requests. Basic JS syntax checked locally. Deployment and public bytes checked separately after merge; do not infer a fresh market-data collection from this UI change.

Default remains memory-only. Users may explicitly retain validated KR/US datasets in the current browser. Unchecking removes stored bundle while retaining current memory; clear removes both. No cross-device synchronization, no server upload, no background download. Stored input is revalidated before restoration. Basis text includes calendar age and acquisition timestamp; unknown metric dates remain unknown. Browser deletion or storage limits can remove/prevent retention.

Resume: git pull --ff-only origin main; open etf.html, connect validated JSON, choose local retention on personal PC if desired. Regenerate input with python scripts/process_etf_provider_inbox.py and python scripts/collect_us_etf_directory.py. Core remaining work: permitted unattended provider acquisition, full-market KRX reconciliation, US issuer metrics and adjusted-price checks. Hosting migration/auth remain deferred. Existing KRX/RS/research rules and raw history preserved.
