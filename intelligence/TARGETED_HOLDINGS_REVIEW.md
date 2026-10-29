# Targeted holdings review — 2026-10-29

User-approved sequence: scheduled price/volume/NAV screening → inspect only shortlisted ETFs on Naver or issuer pages → obtain KRX PDF when dates, scope or weights are insufficient. Google Finance is not a confirmed domestic holdings export source. Do not treat an index portfolio or a top-holdings table as the complete ETF PDF.

The existing ETF investigation table now provides per-ticker Naver CU composition links, the RISE issuer website for RISE products, and KRX's official PDF screen. External pages open only after an explicit click; the portal does not scrape, prefetch, or accumulate third-party tables. The scheduled KRX screening and private official PDF importer remain unchanged.

Each collapsed review panel records source category, actual data date, scope (unknown/top only/full), whether weights are supplied, and a short personal interpretation/follow-up. Records are explicitly saved in this browser under ticker + investigation date. They are not uploaded, shared across devices or used to promote official acquisition/attribution status. Different observation dates are flagged, missing weights defer attribution, and stored text is rendered without HTML interpretation. This is assisted investigation, not unattended holdings analysis.

Current acquisition history remains preserved: 0164G0, 2026-10-27, KRX CSV with missing security weights. Today's queue must not inherit that verification. No raw observations, existing reports or research thresholds changed.

Branch: feat/targeted-holdings-review; base 2ce37d06726d0178ac372b7fce2d880f1842a4b6. Validation: `node --check etf-investigations.js`; `python -m unittest tests.test_etf_investigations tests.test_krx_pdf -q`; existing CI `node tests/test_etf_explorer.cjs` covers links, required date, partial scope, date mismatch, missing weights, persistence and safe text rendering. PR records final commit, CI and deployment results. Next: open the current shortlist's review panel, inspect actual dated holdings, record scope, and use the existing KRX importer only when an official file is needed.
