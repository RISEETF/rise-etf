# Price/FX database and unified RS contract — 2026-09-16

## What is implemented

`python scripts/collect_series.py` captures dated Naver chart candidates for three
official-master-linked RISE ETFs and the ECB's rolling 90-day reference FX XML.
This is a bounded ingestion pilot, not a selected investable RS universe.

`python scripts/build_research_db.py` validates raw SHA-256 hashes, reparses each
successful capture, verifies normalized values and rebuilds `var/research.sqlite`.
Only a successful transactional rebuild replaces the prior database. The SQLite
file is a local query cache; durable source/normalized captures are committed to
Git. A fresh checkout reproduces the DB without fetching the sources again.
This Git storage approach is for the initial pilot; large history/news volumes
will require an external persistent database/object store.

Tables: `instruments`, `captures`, `prices`, `fx`. The observation grain includes
capture ID, market-qualified instrument ID or currency pair, and observation date.
`latest_prices`/`latest_fx` select the most recently captured version of each date.
Do not use these latest-vintage views for point-in-time backtests. Filter captures
by `retrieved_at <= decision_time` before selecting each date's latest version.
Retrieval time is known; original publication time is not inferred or fabricated.
Historical rows captured today were not necessarily available in that form then.

## Measured coverage from the first successful run

| Dataset | Unique dates | First | Last | Status |
|---|---:|---|---|---|
| RISE 200 (148020) | 300 | 2025-06-27 | 2026-09-16 | Quarantined |
| RISE 미국S&P500 (379780) | 300 | 2025-06-27 | 2026-09-16 | Quarantined |
| RISE 국고채3년 (114100) | 300 | 2025-06-27 | 2026-09-16 | Quarantined |
| ECB-derived KRW per USD | 64 | 2026-06-18 | 2026-09-15 | Reference only |

Three initial encoding failures are retained, followed by successful corrected
captures. The final price date includes the collection day and may be an intraday
bar. No confirmed daily closing prices or total-return series are claimed.

## FX definition and limits

[ECB official source and reference-rate methodology](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
publishes units per EUR. On each identical reference date:

`KRW per USD = (KRW per EUR) / (USD per EUR)`.

Both legs are retained. This derived cross is not the BOK reference rate, an
executable quote or the FX rate at a Korean/US equity closing time. Missing legs,
duplicate dates/currencies, future dates, nonfinite and nonpositive values are
rejected. No forward filling or nearest-date substitution is performed.

## Unified universe: exposure first

Domestic ETFs, overseas stocks and overseas ETFs will share one instrument
registry and comparison policy. Listing market is an attribute, not a separate
RS league. The present pilot does not yet collect foreign-listed securities.

Representative selection must be recorded per exposure, with alternatives:

1. Define geographic/sector/asset exposure and validate benchmark/holdings.
2. Require adequate dated, adjusted history and stable source access.
3. Compare actual trading liquidity, spread, tracking and operational history.
   Do not assume the largest/familiar product is automatically best.
4. Select one representative per exposure for the market overview. Keep equivalent
   listings in an alias/peer mapping, avoiding duplicate exposure votes.
5. Keep individual-company concentration distinct from broad index/sector exposure.
   Separate leverage/inverse overlays from the unlevered core comparison.
6. Record selection/replacement effective dates; retain old members for backtests
   to avoid survivorship bias. A proposed instrument is not a validated exposure.

## Gates before any RS calculation

- Confirm close finality, exchange sessions/timezones and missing sessions.
- Verify price basis, splits, distributions and total-return construction. Do not
  mix raw price returns and reinvested total returns in the same ranking.
- Freeze a reporting currency and FX alignment policy. Native-currency and KRW
  comparisons are separate views of the same universe, not interchangeable ranks.
- Define a decision cutoff and use only information available by that time;
  same calendar labels across Korea, Europe and the US do not imply simultaneity.
- Require adequate comparable history. The current 253-observation check is a
  proposed 12-month coverage diagnostic, not a validated RS model parameter.
- Choose horizons, benchmark and scoring method, then validate out of sample.

Current output deliberately has `rs_status=BLOCKED`, `ranking=null` and explicit
per-instrument blockers. Obtaining 300 price rows does not clear these gates.

## Checks and operations

`python -m unittest discover -s tests -v` covers identity/duplicate/range/date
validation, EUC-KR decoding, cross-rate direction, missing FX legs, immutable
captures, historical revisions, repeat DB builds and tamper rejection preserving
the previous database. The portal shows counts, coverage dates, last-attempt status
and the RS hold state rather than unapproved prices or returns.

Weekday collection workflow is staged on the PR; schedule activation requires
merging to the default branch. News ingestion, foreign-listed history, production
DB hosting and RS signal computation remain separate work.
