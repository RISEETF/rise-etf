# Official RISE instrument master validation

- Official source: https://riseetf.co.kr/prod/finder
- Official effective date: 2026-09-11
- Official products captured: 143
- Snapshot revalidated offline: 2026-09-16. This is not a fresh market capture.
- Official identity fields: exchange code, product name, detail URL, category labels, published total fee, listing date

## Legacy portal reconciliation

| Result | Count |
|---|---:|
| Identity match | 20 |
| Official name mismatch | 4 |
| Not in official current master | 124 |

The legacy portal rows were not overwritten automatically. A missing legacy code is a current-master difference, not proof of delisting. The official master is the canonical identity source for later price and return joins.

## Independent market capture check

The preserved Naver ETF response contained 143 RISE identities. Its code and name set matched the official 143-product identity set exactly after the official capture was made. The independent response is used as a secondary identity check only; it does not establish official status or observation dates for prices, NAV, returns, AUM or fees.

Reproduction: `python -m unittest discover -s tests -v`. The preserved-snapshot test checks both source SHA-256 hashes, reparses the official raw HTML, checks unique codes and detail IDs, compares all 143 code/name pairs and reproduces the legacy reconciliation counts. All 8 Python tests and the Node portal date checks passed on 2026-09-16. The original reconciliation JSON predates this secondary check; its null secondary field means no result was recorded in that original report.

## Scope boundary

The following remain separate validation tasks: market price and NAV observation dates, total-return methodology, distributions, AUM and volume units, pension eligibility, fee semantics, corporate actions, product status changes and marketing claims.
