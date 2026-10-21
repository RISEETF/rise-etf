# FunETF private pipeline checkpoint — 2026-10-21

- Branch: main. Implementation merge: a94e3677e3df72e6fd4be5c6cbd772ad5be146f1 (PR #58); parser fix PR #57: df0e1eb93f77c2d13cc59be5c053700728dd38a0.
- Changed: scripts/import_etf_provider_export.py, scripts/process_etf_provider_inbox.py, templates/provider_private.html, tests/test_etf_provider_export.py, tests/test_provider_inbox.py, tests/test_provider_private.cjs, validation workflows, handoff/usage guides.
- Local Python suite: 165 passed. PR #58 Actions 39552764777 and 39552764303 succeeded, including synthetic browser interaction tests. Pages deployment 39553063006 succeeded at implementation merge.
- Direct public URL verification from this environment was unavailable (search fetch inaccessible; direct HTTP attempted separately). Do not equate successful Pages build with independently verified live content.
- Actual FunETF KR export downloaded after secure ordinary email login. Credentials and tokens never saved. Session reused during task; unattended persistence unverified.
- Raw file: 1,181 rows, 22 columns; SHA256 43fb6cfa0de3d0103ffade702d05a1a7d750b930bd7b37b5fde2cb9ea9d74d66. Download date 2026-10-21; screen date 2026-10-20; numeric observation date unknown because file has no explicit date column.
- Latest repository KRX RISE inventory: 2026-10-20, 145. Provider RISE: 144, no provider-only RISE. Missing 0254H0 RISE 반도체소부장액티브. Comparison covers RISE subset, not full KRX universe. No removal from KRX master.
- Private run: 1 capture / 1,181 observations. Reimport deduplicated. Original, SQLite history, receipts and private HTML are under ignored var/, never committed or published. Personal HTML and kit delivered separately.
- Actual-data HTML preview was blocked by cloud browser file URL policy; no workaround attempted. Synthetic CI UI tests passed.
- US search page showed 5,731 entries and 2026-10-20 screen date, but no bulk export control. US file not downloaded; schema deliberately rejected until verified.

## Resume

1. git pull --ff-only origin main
2. python -m pip install openpyxl==3.1.5
3. Put ordinary downloaded KR XLSX and optional metadata sidecar into var/provider_inbox.
4. python scripts/process_etf_provider_inbox.py
5. Optional local watcher: python scripts/process_etf_provider_inbox.py --watch
6. Open var/provider_private/index.html locally. Consult intelligence/PRIVATE_PROVIDER_GUIDE.md.

Remaining: permitted US export/source and schema; full-market KRX reconciliation; unattended download/session authorization and technical verification; independently confirm public URL. No background watcher or login automation was deployed. Public FunETF metrics remain unpublished. Missing provider rows never imply delisting; unknown dates never relabeled as closing dates.
