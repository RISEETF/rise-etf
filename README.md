# RISE ETF research portal

## Recovery scope

This branch repairs data integrity before extending RS and marketing research.
The existing source snapshot is unverified. Its market values, news, ETF metadata
and marketing statements have NOT been validated against original sources.
The default portal reads only the official identity master, capture status and
reconciliation report. Legacy prices/news are isolated in `legacy.html`, labeled
unverified, with customer-copy export blocked.

- Date choices come from `data/manifest.json`; missing dates never fall back to latest.
- `data/YYYY-MM-DD.json` preserves the first stored baseline for its stated date.
- `data/latest.json` remains unchanged by quote capture; it is not a live feed.
- Source responses are stored by SHA-256 under `data/raw/naver/`.
- Timestamped quote captures and run outcomes accumulate separately.
- A capture timestamp is NOT an observation date. The legacy Naver endpoint's
  field semantics and market timestamp require verification before promotion.
- API failure produces a failed run record and leaves published values unchanged.
- The scheduler is in `.github/workflows/`, where GitHub can recognize it.

## Run

`python -m unittest discover -s tests -v`

`python scripts/update_daily.py`

`python -m http.server 8000`

Open the local server to view the existing portal. Python standard library only.
The portal supports code/name search and official-category filters, displays
source dates and KST retrieval times, and rejects missing or malformed masters.
Browser QA: `node tests/test_master_portal.cjs` (Playwright + Chromium).
Legacy date QA: `node tests/test_portal.cjs`.
The workflow becomes active after this branch is merged to the default branch.
No live orders or model-generated replacement prices are implemented.

## Next implementation gates

1. The official identity master is generated from the RISE ETF Finder. Keep
   validating fee semantics, pension eligibility and effective-date changes.
2. Add validated daily prices, distributions, FX and market calendars; promote
   each field only with observation date, source URL and retrieval timestamp.
3. Store news URLs, publication timestamps and entity links; calculate changes
   from comparable observations instead of rewriting old reports.
4. Map evidence-backed market points to RISE exposures and peer products.
5. Add unified RS, product-gap candidates and historical review views.

Current capture JSON is an initial append-only collection layer, not a completed
market database. No production data-quality approval is implied by passing tests.

## Master history

The first `data/master/YYYY-MM-DD.json` vintage is immutable. New captures are
stored under `data/master/captures/`; `latest.json` must not regress to an earlier
effective date. New captures preserve both listing and overview HTML by SHA-256,
so the official page's count/date can be traced. Attempts, including failures,
are logged in `data/master_runs/` and `data/master_collection_status.json`.
The September 11 snapshot predates overview retention and retains that limitation.

## Dated price and FX pilot

`python scripts/collect_series.py` appends source and normalized captures.
`python scripts/build_research_db.py` verifies and rebuilds `var/research.sqlite`
and the portal's `data/series/status.json`. Python standard library only.
Run the builder after a fresh checkout for offline DB reconstruction.
The three price series are quarantined; ECB FX is reference-only. No RS rank is
computed. See `SERIES_AND_RS_CONTRACT.md` for schema, coverage, limitations and
the unified cross-market representative-selection policy.
