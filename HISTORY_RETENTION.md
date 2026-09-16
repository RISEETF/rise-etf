# Historical overseas identities

Removing a symbol from `overseas_sources.json` stops its future collection and removes it from the active coverage list. It must not destroy historical prices or dividends, nor prevent database reconstruction.

Successful overseas captures are now revalidated against their saved instrument contract and hashed raw provider response. The supported contract remains USD, US_LISTED, ETF/EQUITY and America/New_York. This does not certify an exchange MIC or resolve symbol reuse.

The database retains each capture's full contract in `instrument_contracts`. Current display-name edits are allowed; historical names remain in those contracts. Conflicting type/currency/market/timezone for the same identifier requires an explicit migration and fails reconstruction without replacing the previous database. Names alone are not provider-certified identity.

Regression coverage exercises removal, renamed labels, conflicting identity, original dividend evidence, and preservation of the prior database on failure. Domestic master ordering now uses the actual `retrieved_at` field.

Operational checkpoint: PR #1 was merged as `61d89ba1916d285959da29423f40e0ed6457e62b`; Pages run 35161366332 succeeded. Public HTML/JS/CSS matched the reviewed files, master returned 143 products dated 2026-09-16, and coverage returned six series with RS blocked. At the subsequent check no post-merge scheduled collector run existed. Automatic refresh is still awaiting its first observed execution; initial publication success is not evidence of successful scheduled operation.
