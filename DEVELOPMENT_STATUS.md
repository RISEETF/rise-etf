# Research portal checkpoint — 2026-09-16

## Implemented on PR #1

- Official RISE identity master: 143 products, official effective date 2026-09-16.
- Original listing and overview HTML preserved with SHA-256; overview establishes
  the displayed count/date. Capture time is separate from that date.
- Official master search, category filter and source links on the default portal.
- Legacy prices, news and marketing text isolated in `legacy.html` and unverified.
- First daily master vintage preserved; new captures retained separately;
  latest cannot move to an earlier effective date. Collection attempts are logged.
- Source and master workflows share a per-branch concurrency group to avoid
  competing automated pushes. PR validation workflow added.

## Validation evidence

- Python: 10 tests passed, including current raw hashes/overview/listing consistency,
  historical 143-identity reconciliation and immutable daily-vintage behavior.
- Node legacy date checks and portal JavaScript syntax passed.
- New Playwright browser checks authored for search, category filtering, missing
  data, duplicate rejection and narrow-screen overflow. Local execution blocked:
  Chromium was unavailable and browser download timed out/returned HTTP 502.
  GitHub Actions subsequently ran all browser checks successfully on commit
  `90f6a5a64d541f9061c17622920e3992501534b4`:
  https://github.com/RISEETF/rise-etf/actions/runs/35044168352
  Automated interaction/mobile-overflow QA passed; manual visual review remains.
- PR validation workflow passed. Scheduled collection workflow execution and
  production deployment are not yet verified. PR remains draft.

## Remaining implementation order

### Bounded issuer reconciliation

- AAPL official amount comparison: eight recent dividends plus one 2020 dividend.
- Real 2020 4:1 split trading-date/ratio match and double-adjustment regression.
- Record dates are not promoted to ex-dates. Official source facts were manually
  extracted from accessible web-page text; automatic refresh hit an access challenge.
- Historical fixture is outside live coverage. Python suite: 24 passing tests.
- See APPLE_ISSUER_VALIDATION.md; partial evidence only, RS still blocked.

### Overseas extension

- SPY/IEF/AAPL: 501 observations each, 40 cash events in total and zero observed
  split events. Provider-internal adjustment diagnostics found no flags.
- One shared prices table for domestic ETFs, foreign ETFs and foreign equities;
  adjusted close and corporate actions retained separately. No RS promotion.
- Python suite: 20 passing tests. Details: OVERSEAS_ADJUSTMENT_AUDIT.md.

### Price/FX foundation added

- Three official-master-linked price candidates: 300 dated rows each; adjustment
  and final close semantics remain unconfirmed. ECB cross FX: 64 reference dates.
- Immutable captures, failure records and a reproducible SQLite query database.
- Portal coverage view and weekday series workflow staged on this PR.
- Python suite expanded to 15 passing tests. New series browser assertions are
  included in CI; the earlier browser success above applies to the prior commit.
- See SERIES_AND_RS_CONTRACT.md. No ranking or trading signal has been enabled.

1. Review the portal before merge/deployment; automated browser/CI checks passed.
2. Establish daily price/NAV observation dates, corporate actions, distributions,
   FX and trading calendars. Current Naver capture is not an approved daily close.
3. Accumulate validated price history and news URLs/publication timestamps in a
   durable database; preserve raw captures and revision history.
4. Define one cross-market exposure universe for RS. Select representatives by
   exposure coverage, history, liquidity and data quality; avoid duplicating the
   same underlying exposure across KR ETFs, overseas stocks and overseas ETFs.
   Keep currency, leverage/inverse and total-return conventions explicit.
5. Link market changes to verified RISE holdings/exposures and peer ETFs, then
   assess product gaps. Names alone do not establish portfolio exposure.

No RS, trading signal, product recommendation or automated marketing claim is
live. No merge or production deployment has been performed by this change.
