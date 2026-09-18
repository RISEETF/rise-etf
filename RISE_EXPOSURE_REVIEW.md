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

## 미국S&P500 투자설명서 추가 검토 (2026-09-18 KST)

공식 상세 페이지에서 연결된 [투자설명서](https://riseetf.co.kr/upload/cdn/2026/08/07/202608077ee54aeec9bc426.pdf)를 직접 내려받아 검토했다. 작성기준일은 2026-07-20, 효력발생일은 2026-08-07이다. PDF 17쪽(인쇄 16쪽)의 환헤지 방침은 렌더링으로도 확인했다. 검토 파일 SHA-256은 `5064105725d4180e956ef984f99a04aeecf4c7dfffb5cc67f66a727f6051caa0`이며 원본 PDF는 저장소에 보관하지 않는다.

| 확인 항목 | 공식 근거 | 시스템 적용 범위 |
|---|---|---|
| 환헤지 | PDF 17–19쪽, 제2부 9항: 환헤지 미실시 방침 | 운용 방침으로 기록. 실제 일별 보유 포지션 검증과 구분 |
| 복제 방식 | PDF 17–18쪽: 완전복제 계획, 부분복제 및 ETF·장내파생상품 편입 가능 | 현물 100% 완전복제를 전제로 계산하지 않음 |
| 공시 기준가격 | PDF 31쪽, 제2부 12항: 직전일 순자산총액과 총좌수로 산정 | NAV 산정 설명으로만 기록 |
| 상장주식 평가 | PDF 31쪽: 평가기준일 취득 국가 시장의 최종시가 | 미국 거래일과 한국 공시일 간 구체적 매핑은 추가 확인 필요 |

### 통합 RS에 적용할 해석

거래소 ETF 시장가격, 공시 NAV, 기초지수는 별도 시계열이다. NAV의 직전일 산정 설명을 근거로 수집된 한국 ETF 종가를 하루 이동시키면 안 된다. 상품명에 있는 `T-1`만으로 달력일/미국 영업일/한국 영업일의 대응, 휴장일 처리, 지수 환율 고시시각을 확정할 수 없다. 설정·환매 절차의 T-1도 기초지수 날짜 규칙의 근거가 아니다.

이번에 검토한 조항에서는 기초지수 및 NAV에 적용되는 정확한 환율 고시시각을 확인하지 못했다. S&P의 다른 KRW 지수 변형에 있는 환율 규칙을 이 상품에 전용하지 않는다. 현재 수집하는 ECB 기준환율을 해당 지수의 공식 환율로 취급하지 않는다.

다음 검증은 이 상품의 정확한 지수 식별자와 방법론 연결, 해당 지수의 날짜·환율·휴장일 규칙, 실제 NAV/지수 관측치 대조다. `issuer_evidence.json`에 확인 사실과 미확인 값을 분리해 추가했으며, 대표 선정 및 RS 계산 자격은 계속 미승인 상태다.

## First scheduled operation evidence

GitHub reported successful scheduled source capture 35196063898 and series capture 35199748550. Their refresh workflows 35196085308 / 35199771003 succeeded, followed by successful Pages builds 35196092525 / 35199778539. This establishes observed scheduled executions, not a guarantee of future availability or validated prices.
