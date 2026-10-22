# ETF explorer checkpoint — 2026-10-22

Current branch main. Implementation merge 34b447c546193c4cf74f09a97b4975cf2e1f30da (PR #60); tested head dcb122a808f383d54060c084f851d739b6da39fc.

Changed: etf.html/js/css, dashboard index links, private provider portal.json export, deployment verifier assets, synthetic browser integration test, CI and private provider guide.

Validation: 168 Python tests passed before PR. First CI failed because test clicked a control in a collapsed details panel; test now opens panel through visible UI. Corrected PR runs 39697579623 and 39697579535 succeeded. Pages 39697684012 and public deployment verification 39697684572 succeeded. Direct HTTP checks confirmed exact bytes of index.html, etf.html, etf.js and etf.css after deployment (initial requests before deployment returned prior page/404).

Behavior: KRX RISE list is fetched by default. Optional FunETF portal.json and Nasdaq latest.json files are read in browser memory, never uploaded or saved to localStorage. Up to four same-market selections, detail metrics, dates and missing values. Missing FunETF rows do not remove KRX rows. US file is identity directory only. Reload clears personal data. Current public KRX scope covers RISE, not all domestic ETF listings.

Actual existing files passed browser input validator: FunETF 1,181 rows; US directory 5,776. Both acquired 2026-10-21; do not call them today's refreshed data. A user-facing ZIP with both JSON files and usage instructions was delivered privately; no provider data committed.

Next commands:
```
git pull --ff-only origin main
python scripts/process_etf_provider_inbox.py
python scripts/collect_us_etf_directory.py
```
Open https://riseetf.github.io/rise-etf/etf.html and select generated var/provider_private/portal.json or var/us_etf_directory/latest.json in the personal-data section. Synthetic UI verification: node tests/test_etf_explorer.cjs (requires Playwright Chromium; CI installs it).

Remaining: automated permitted FunETF retrieval, full-market KRX reconciliation, US issuer metrics/adjusted-price validation, and persistent private-data delivery. Cloudflare migration and authentication remain deferred by user. Do not describe manual browser import as unattended portal data refresh. Core daily reports and prior research rules remain unchanged.
