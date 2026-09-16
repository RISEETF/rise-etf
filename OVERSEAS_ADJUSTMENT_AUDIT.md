# Overseas ingestion and adjustment diagnostics — 2026-09-16

## Result

SPY, IEF and AAPL were captured from Yahoo's public chart endpoint. Each returned
501 complete dated observations from 2024-09-16 through 2026-09-15. They use the
same SQLite `prices` table and portal coverage view as the three Korean ETFs.
The foreign identifiers use a provisional `US_LISTED` namespace, not a verified
exchange MIC or issuer-approved master. This pilot is not a recommendation or
the final representative universe.

| Instrument | Cash events | Split events | Missing returned price rows | Diagnostic flags |
|---|---:|---:|---:|---:|
| SPY | 8 | 0 | 0 | 0 |
| IEF | 24 | 0 | 0 | 0 |
| AAPL | 8 | 0 | 0 | 0 |

Zero missing returned rows does not prove exchange-calendar completeness. Zero
split events means no split was present in this sample; live split adjustment
has not been empirically validated. Synthetic split tests check that the code
does not apply a split a second time.

## Source and method

[Yahoo's adjusted-close explanation](https://help.yahoo.com/kb/SLN28256.html)
describes adjustments for applicable splits and dividends. We preserve provider
close and adjusted close separately, alongside dividends, capital gains and split
events. The public chart endpoint is a candidate without an assumed API service
guarantee. Access/rate-limit responses stop remaining requests; no host rotation
or access workaround is implemented.

For adjacent observed prices, calculate the ratio of `adjusted_close / close`
between the previous and current row. Compare a cash-event day's factor ratio
with `1 - cash_amount / previous_close`. A residual above 0.0005, an unexplained
factor change above 0.000001 or a split is marked for review. These are diagnostic
tolerances, not calibrated trading-signal thresholds. Cash events and source
adjustment conventions can vary, so this is not a universal total-return formula.

All 40 captured cash events were present on price dates. Provider-internal
diagnostics found no flags under this rule. This checks internal consistency;
it does not independently establish issuer action dates, distribution tax treatment,
event completeness, execution returns or publication-time availability.

## Integrity and remaining gates

- Validate symbol, currency, instrument type and exchange timezone against each
  pilot contract before ingesting. Dates come from timestamps in America/New_York.
- Reject duplicate/future dates, nonfinite values, invalid OHLC and misaligned arrays.
- Record missing price rows explicitly; never synthesize adjusted prices or fill gaps.
- Retain each raw response by hash and each retrieval as a separate vintage.
  Rebuilding the DB reparses events and adjustment diagnostics from original bytes.
- Preserve all corporate actions in `corporate_actions`; do not replace prior vintages.
- Local Python suite: 20 tests passed. Browser assertions now use the configured
  combined-universe row count rather than a hard-coded three-row assumption.

Still unresolved: independent issuer-event reconciliation, actual split-event
empirical validation, Korean ETF distribution adjustment, exchange calendars,
decision cutoffs and FX alignment. All six instruments remain quarantined;
`rs_status=BLOCKED` and `ranking=null` are unchanged.

Run `python scripts/collect_overseas.py`, then `python scripts/build_research_db.py`.
The weekday workflow stages this same sequence after Korean-price/FX collection.
Scheduled production execution requires merging and has not yet been verified.
