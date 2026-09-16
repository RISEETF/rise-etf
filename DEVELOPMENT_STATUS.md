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
  Browser visual/interaction QA is pending, not passed.
- New workflow execution and deployment are not yet verified. PR remains draft.

## Remaining implementation order

1. Complete browser/CI checks and review the portal before merge/deployment.
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
