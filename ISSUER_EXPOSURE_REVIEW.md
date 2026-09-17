# Candidate issuer evidence — 2026-09-17

Two manual, partial objective checks are stored in `data/universe/issuer_evidence.json` and linked by both exposure group and instrument. The generation script hashes the fact file, not the original issuer document. Raw issuer documents were not retained; this is not an automated official feed.

SPY: the official State Street factsheet dated 2026-06-30 identifies S&P 500 as its target and describes the index as US large-cap, float-adjusted market-cap weighted. The document was accessed on 2026-09-17; its date is not promoted to September. This supports the stated objective only, not equivalence to RISE 미국S&P500 or full current holdings validation.

IEF: the official product page identifies ICE US Treasury 7-10 Year Bond Index and a remaining-maturity target of seven to ten years. Effective duration of 6.90 years is explicitly dated 2026-09-15. The page contains multiple metric dates, so it has no invented single observation date. Duration and remaining maturity are not interchangeable.

The UI displays the scope and review date. Both candidates retain all representative-selection blockers. Required next evidence: full holdings and structure, comparable returns, liquidity/alternative-proxy comparison, session/FX alignment and sensitivity checks. No RS or representative selection is activated.

Tests reject promoted eligibility and evidence attached to a mismatched exposure group. Existing unknown/duplicate candidate and history preservation checks continue to run.

Sources:
- https://www.ssga.com/library-content/products/factsheets/etfs/us/factsheet-us-en-spy.pdf
- https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf
