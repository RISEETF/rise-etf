# RISE market metrics and targeted holdings — 2026-10-30

The user requested automatic holdings acquisition for shortlisted ETFs and price/flow/performance fields in the RISE list. Existing KRX collection, ledger, screening and official PDF importer are reused. No source observations, thresholds or existing reports are replaced.

## Implemented market view
`scripts/build_etf_market_metrics.py` reads the existing cumulative KRX SQLite ledger and the matching successful collection receipt/inventory. It publishes current observed RISE products, close, NAV, computed close/NAV premium, volume, trading value, net assets and dated unadjusted close returns. Historical NOT_OBSERVED identities remain in the inventory but are not given invented current prices. Revisions select the latest retrieval. Invalid identity/count/date/source binding or nonfinite values stops publication; last-good prices and content-addressed history remain. The existing twice-daily KRX workflow builds the view after collection and commits it with the screening outputs. The browser reports data dates and failed/unknown collection status.

Periods: 1D uses the preceding weekday only if its close exists (a missing weekday/holiday is not silently bridged). 1W targets seven calendar days earlier. 1M/3M use calendar months, month-end clamped. YTD targets prior December 31. Longer periods select the last market observation on/before the target within seven calendar days and require that ETF's value on that date. Actual base/end dates are displayed; history gaps remain null. These are **unadjusted price returns**, not distribution-reinvested total returns. No interpolated prices or fabricated zero flows.

Initial inspected artifact: KRX run 40804830784, observation 2026-10-28, 1,186 ETFs; ledger 2026-09-21–2026-10-28 (24 observation dates). 145 RISE price/1D/1W records, 144 1M records, no 3M/YTD baseline. These counts are audit results, not fixed code constants. A historical backfill must preserve raw responses/revisions and use the authorized KRX key, with bounded requests; the current change does not claim it has completed that backfill.

UI: price/returns/flow views, numeric sorting (missing values last), dated detail/comparison, existing private supplemental upload preserved. Investor flow tab explicitly reports missing source; no estimates from volume or AUM.

## Holdings research and experiment
The KRX official public API service list (https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd, checked 2026-10-29) lists ETF daily trading but no ETF PDF or investor-level flow service. The logged-in Data Marketplace has separate PDF and investor-trading screens. Existing authenticated CSV acquisition/import remains a usable fallback; a personal browser session is not a durable GitHub runner credential.

Naver composition links remain a screen reference, not an assumed full daily PDF/export feed. Search-cached holdings are not current source data. The RISE site migrated to kbam.co.kr; the existing master supplies ticker-to-product identity. A candidate issuer JSON holdings endpoint was found, but this environment returned HTTP 503/connection timeout for the product page and candidate endpoint. This is a connection failure, not evidence of bot detection or a successful acquisition.

`probe_etf_holdings.py` and the manual/PR `holdings_source_probe.yml` test at most the already shortlisted RISE products from GitHub's runner. They retain raw JSON as a runtime artifact and report HTTP outcomes. JSON receipt is deliberately **unvalidated**: no automatic schedule, public holdings table, source-date claim or cause attribution is enabled before inspecting actual responses. Other issuers remain separate unverified adapters. No cookies/passwords/tokens are copied to GitHub.

Production acceptance: prove ticker identity via official master, actual observation date in response, complete vs top-only scope, units and weight denominator; archive original and hash; idempotent ticker/date/hash accumulation; limited rate/no retry loops; preserve last-good on failure; same-date changes retained. Only dates matching the investigation can support same-date composition analysis. Missing weights block attribution. Implement issuer adapters incrementally; do not replace actual ETF holdings with index components.

Investor flow: needs separate actual KRX export/API or a documented provider feed covering ETF codes, dates and investor categories. Preserve buy/sell/net amount units and avoid double-counting institutional totals and subgroups. No verified automated feed is connected by this change.

## Continuation
Branch `feat/etf-market-metrics`; final PR records commit/CI/Pages/probe outcomes. Commands: `python -m unittest tests.test_etf_market_metrics tests.test_krx_etf tests.test_etf_investigations -v`; `python scripts/build_etf_market_metrics.py`; `node tests/test_etf_explorer.cjs`. Next inspect the probe artifact, then decide whether the issuer response can support a validated targeted adapter. Source-blocked features are not marked completed.

### Endpoint backfill and actual source probe result
`backfill_etf_return_baselines.py` now reuses `fetch_latest`, completeness checks and append-only accumulation for at most four missing target dates (1W/1M/3M/YTD; at most eight calendar-date attempts each). It preserves historical raw responses under `var/krx-output/baselines` and caches successfully resolved target dates in SQLite. No current master/receipt is changed. Old universe completeness is not compared to today's larger universe. Failed targets remain PARTIAL without leaking exception text; available current prices still build. Return rows also retain the base close's raw hash. Baseline acquisition must be verified in the actual authenticated workflow before reporting 3M/YTD coverage as complete.

GitHub runner experiment 40976626720 completed, but the RISE 302450 holdings endpoint returned URLError. Other four shortlisted issuers have no verified adapters. Thus experiment execution succeeded; actual holdings acquisition did not. Artifact 12943230910 contains the failure receipt only. This does not establish production automation capability.

## 2026-11-02 continuation: source access and diagnostics
Main checkpoint before this change: cb38c21f28213d154e67c63d994a89fede7b46d8.
KRX run 41376130907 and Pages run 41397660208 succeeded. Latest verified
observation is 2026-10-30: 145 RISE price/1D/1W, 144 1M, 141 3M, 132 YTD;
YTD baseline is 2025-12-30. These are measured coverage, not fixed targets.

Official source candidates inspected:
- KIS official example: https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/etfetn/inquire_component_stock_price/inquire_component_stock_price.py
  GET `/uapi/etfetn/v1/quotations/inquire-component-stock-price`, transaction
  `FHKST121600C0`, market `J`, screen `11216`, input ETF code. It returns
  output1/object and output2/list. Authentication is required. The adjacent
  example's display mapping contains inconsistent labels (e.g. stck_prpr
  labelled a date), so do not infer observation dates or units from that mapping.
  ETF coverage for overseas/synthetic assets, completeness, dates and weights
  must be verified with an entitled real response before any production import.
- KIS investor example: https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_investor/inquire_investor.py
  GET `/uapi/domestic-stock/v1/quotations/inquire-investor`, transaction
  `FHKST01010900`. Official notes say today's information is provided after
  close and foreign includes other foreign investors. ETF coverage and amount
  units remain unverified. No API credentials were requested in chat or stored.
- Koscom https://koscom.gitbook.io/open-api/api/marketv3 lists
  `/v3/market/extra/stocks/kospi/{issuecode}/pdf`. Its terms explicitly require
  a market-data licence for processing/accumulation, including sandbox data.
  https://datamall.koscom.co.kr/kor/main.do also lists daily ETF PDF and investor
  trading data products. Existing company entitlement needs confirmation;
  no subscription or agreement has been made on the user's behalf.

The current source experiment still does not enable production collection.
Connection errors are now categorized without recording exception messages
(DNS, timeout, TLS, connection, invalid JSON, oversized or unknown). HTTP
status remains separate. Three new tests cover safe diagnostics, no promotion
of received JSON, and the maximum-five request gate.

Resume on `fix/holdings-source-diagnostics`; final commit and CI are recorded
in its PR. Run `python -m unittest tests.test_holdings_probe -v`, then
`python scripts/probe_etf_holdings.py --output var/holdings-probe`.
Next required input: whether an existing KIS API or company Koscom data
entitlement is available. Do not request raw credentials in chat. Keep existing
KRX prices running independently; holdings and investor flows remain incomplete.

## Download inbox fallback (2026-11-02)
The user has no KIS/Koscom entitlement. Do not block existing KRX price jobs on
new credentials. Official KIWOOM 459790 product page was found, but direct
retrieval failed; neither cached search snippets nor index holdings were imported.
No additional live holdings acquisition succeeded in this session.

`scripts/import_krx_pdf_inbox.py` reuses the validated KRX CSV importer. Put each
locally downloaded export in a separate directory under `var/etf-pdf-inbox/`:
- `original.csv`: unchanged KRX export.
- `receipt.json`: the existing importer receipt, including browser-observed
  ticker/name/date, retrieval time, units, row count and SHA256. Do not infer
  observation date from the filename or download date.
- `queue.json`: the original maximum-five investigation shortlist for that date.

Run `python scripts/import_krx_pdf_inbox.py --inbox var/etf-pdf-inbox --output var/etf-pdf --public-receipts data/etf_investigations/pdf_receipts.json`.
Confirm the existing portal receipt path before publication; see etf-investigations.js.
The command handles at most five changed bundles per invocation, leaves all input
files intact, skips successful unchanged bundles and records pending/failed states
in private `inbox_status.json`. One bad export does not stop others. Existing raw
archive, SQLite idempotence and same-date revisions are reused. Only metadata is
eligible for publication; constituent rows remain private. A complete receipt is
still a human/browser assertion, not independent proof of its date.

This is a batch ingestion command, not an installed background watcher or an
automatic KRX download service. To schedule on a persistent workstation, run the
same command from its scheduler after downloads; ephemeral GitHub runners cannot
see local folders. No scheduler was installed in this session.
Continuation branch: feat/krx-pdf-inbox. Tests: python -m unittest
 tests.test_krx_pdf_inbox tests.test_krx_pdf -v. Final CI/merge results are in the PR.
