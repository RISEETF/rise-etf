# RISE candidate benchmark review

Official detail HTML was retrieved directly and reviewed at 2026-09-17 22:58 UTC (2026-09-18 in Korea). Search-tool fetches timed out; direct public HTTP reads succeeded. The extracts are manual and the full HTML is not retained in Git; no raw-source hash or automated issuer feed is claimed.

| Code | Official benchmark field | Remaining comparison issue |
|---|---|---|
| 148020 | KOSPI200 | Full holdings/structure reconciliation and total-return verification |
| 379780 | S&P 500 Index (KRW)(T-1) | KRW and T-1 labels must be resolved before comparison to SPY; do not infer exact FX fixing, hedging or total-return conventions |
| 114100 | KTB채권지수 | Product-name “3년” does not prove actual duration; index construction and dated duration still needed |

The pages displayed 2026-09-18 but that is not a certified price observation date. Only the benchmark field and identity were extracted. Prices and AUM on these pages were not promoted into the database. All representative-selection blockers remain.

Sources:
- https://riseetf.co.kr/prod/finderDetail/4435
- https://riseetf.co.kr/prod/finderDetail/44B3
- https://riseetf.co.kr/prod/finderDetail/4427

## First scheduled operation evidence

GitHub reported successful scheduled source capture 35196063898 and series capture 35199748550. Their refresh workflows 35196085308 / 35199771003 succeeded, followed by successful Pages builds 35196092525 / 35199778539. This establishes observed scheduled executions, not a guarantee of future availability or validated prices.
