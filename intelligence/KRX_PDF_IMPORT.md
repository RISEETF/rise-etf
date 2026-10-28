# Selective KRX PDF import — 2026-10-29

## Verified acquisition

Normal KRX username/password sign-in succeeded in the cloud browser. The visible page offered a 30-minute automatic logout timer. Via Statistics → ETF → PDF (13108), selected 0164G0 RISE 차이나AI반도체TOP4Plus and 2026-10-27, default units 주(계약) and 원, then Download → CSV.

Downloaded 997 bytes at 2026-10-28T23:51:58.486727Z (October 29 KST). SHA256: c2ab1f68f63fd2ec4fccf64f14268a25a1fa46fc30935d244c0a93472fb3e1c5. CP949 CSV, six columns, 17 rows: 15 securities and two cash-related rows. Security quantities are present but their valuation, market value and weight fields are empty. Missing values remain null. Setting cash is not an extra stock or an additive investment amount. This file cannot support weighted attribution or a full-portfolio verification claim.

The CSV itself contains neither parent ETF identity nor query date. The separate receipt records the browser-observed search context and SHA256. This is an operator assertion bound to bytes, not a signed KRX identity certificate. Never infer observation date from download date or filename alone.

## Implemented path

`scripts/import_krx_pdf.py` reuses existing CSV decoding/number parsing and atomic JSON writing. It requires an exact observed schema, receipt hash/date/units/count and a matching ticker/name/date in a real investigation queue. Unknown schemas, nonfinite values, duplicate constituent codes and mismatched requests fail closed. All original bytes and normalized documents are retained under ignored `var/etf-pdf`; SQLite transactions preserve previous imports. Same ticker/date/hash is idempotent even after a later redownload; revised bytes create a separate historical import. Failures record a reason and last successful attempt without replacing public metadata.

Only acquisition/quality receipts are public. Constituent rows and private SQLite are not committed. ETF explorer joins receipts to the exact queue ticker AND date, displays partial availability, and never calls it a verified cause. Other dates remain pending. Acquisition does not change the source screening queue or research rules.

```bash
python scripts/import_krx_pdf.py var/pdf-inbox/KRX_PDF_0164G0_20261027.csv \
  --receipt var/pdf-inbox/receipt.json \
  --queue data/etf_investigations/latest.json \
  --public-receipts data/etf_investigations/pdf_receipts.json
python -m unittest tests.test_krx_pdf -v
node tests/test_etf_explorer.cjs
```

For an older investigation, pass its immutable queue history file. Download CSV through the normal authenticated KRX UI; create a receipt with ticker, name, observation_date, retrieved_at (timezone required), source_url (13108 menu URL), date_basis=BROWSER_OBSERVED_QUERY, quantity_unit=주(계약), amount_unit=원, row_count and sha256. The command is the common importer for legitimately acquired files. There is no unattended login, bulk scraper, background file watcher or scheduled PDF download in this change. Price/volume/NAV screening remains scheduled in GitHub Actions. Do not store credentials or session cookies.

## Verification and continuation

186 Python tests passed locally, including six import tests. Local browser tests could not launch because Chromium is absent; use the existing PR CI browser gate. Tests cover absent weights, cash separation, hash/date/count mismatch, duplicates, revisions, last-good preservation and metadata-only public output. Browser tests cover pending, wrong-date receipts and partial acquisition display. Check CI and public deployment separately in the PR.

Private original/receipt/DB/normalized bundle: Library item libfile_4d6ff1cb2970819184855fce006a693c, RISE_KRX_PDF_0164G0_20261027.zip. No credentials included. Branch feat/krx-pdf-import, base 3af314dd2b9f2387bda2d60f8a3fa12a09ab0ff7; final commit and deployment evidence in the PR. Report repair PR #73 passed CI and Pages run 40790144507.

Next: verify the actual receipt UI after merge, then acquire another selected ETF only when useful. For this overseas ETF, obtain a legitimate issuer weight source before computing weighted concentration or explaining the NAV gap. The existing signal remains a research candidate; PDF rows alone do not establish causality.
