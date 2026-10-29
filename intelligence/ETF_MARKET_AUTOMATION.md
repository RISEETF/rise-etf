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
