# FunETF direct-download verification — 2026-10-21

User requested direct cloud-browser download first, KRX-primary integration, and then added US-listed ETFs. Existing repo/importer reused. Base main: 975b016. Working branch: fix/funetf-export-validation. No credentials, cookies, tokens or account identifiers are saved here.

## Observed results

- Login succeeded through secure email/password handoff; site also offers Kakao and Apple. Navigations reused the authenticated session during this task. Cross-session persistence and unattended login are not established.
- Domestic search: https://www.funetf.co.kr/product/etf/search/KR — 1,181 entries, screen basis 2026-10-20; ordinary Whole Information Download button exists.
- First download event returned an inaccessible file path. One retry delivered a readable 307,676-byte XLSX. Actual SHA256: 43fb6cfa0de3d0103ffade702d05a1a7d750b930bd7b37b5fde2cb9ea9d74d66. Original kept privately for the user, not in this public repository.
- Actual file has 1,181 ETF rows / 22 columns. Workbook incorrectly declares A1:A1; existing read-only importer therefore read only the first column. Fix resets read-only dimensions, with a synthetic OOXML regression test and bounded expanded size/row count.
- Fields include returns (1 day/week/month, 3/6 months, YTD, 1 year), total fee, TER, actual burden ratio, net assets in KRW 100 million, 3-month deviation, manager, and TOP3 holdings/weights. TOP3 is not complete holdings. Repeated weight column headers require positional mapping. Missing values stay null.
- Workbook contains no explicit numeric observation date column. The search screen states 2026-10-20, but file-wide metric dates remain unverified; inspection leaves provider_observation_date null. Retrieval date is 2026-10-21.
- Latest repository KRX inventory observed 2026-10-20, retrieved 2026-10-21T01:22:02.822751+00:00, raw hash d19245d73098af26d0f02ae77ad387aef539236e1a40fc8c2cd36abce06d1b41. RISE 145; downloaded provider RISE 144; intersection 144; missing 0254H0 RISE 반도체소부장액티브; no provider-only RISE or name differences. This is a RISE subset reconciliation, not full-market KRX reconciliation. No deletion/delisting inferred.
- US search: https://www.funetf.co.kr/product/etf/search/US — 5,731 entries, screen basis 2026-10-20. No Whole Information Download button in the signed-in rendered page. US file download/normalization is NOT completed. Do not apply Korean six-character code validation or KRX authority to US tickers.

## Usage boundary requiring user action

Observed footer restricts unauthorized database use. Investor terms https://www.funetf.co.kr/agreement/investor restrict commercial use and third-party distribution without prior consent. User explicitly required compliance with permitted use. Permission covering periodic collection, internal database storage and public GitHub Pages redistribution has not been supplied. A member export button alone does not establish those rights.

No scheduled FunETF download, real-data database accumulation, public data upload or portal metrics publication was enabled. Manual folder ingestion is also subject to the same usage scope; it is not a way around the restriction. Obtain/confirm provider permission before implementing/enabling those operations. Do not request password/token in chat or commit them.

## Implemented and tested

Existing importer now reads actual export dimensions correctly and supports read-only --inspect-only with --krx-inventory. Exact schema mapping rejects unexpected headers, duplicates, nonfinite metrics and negative fees/assets. Primary inventory remains unchanged, unknown/different dates stay explicit and publication_eligible remains false. CI installs the XLSX reader so the regression test actually runs. 159 tests passed locally; PR CI/merge/Pages outcomes must be appended after verification.

Resume:
```
git fetch origin
git status --short --branch
python -m unittest discover -s tests -q
python scripts/import_etf_provider_export.py --source funetf --file /path/to/export.xlsx --inspect-only --krx-inventory data/quality/krx_rise_inventory.json
```

Remaining after permission: shared validated manual/automatic inbox pipeline, immutable raw captures, transactional supplementary DB/history/receipts, authoritative full-market KRX reconciliation, notices-based lifecycle classification, licensed ETF detail/comparison views, and actual public verification. US export availability and an authoritative US identity source must be resolved separately. Authentication and licensing are different prerequisites. No P2 completion claimed.
