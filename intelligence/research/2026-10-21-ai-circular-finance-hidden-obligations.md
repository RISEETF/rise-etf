# AI 순환금융·숨은 자본부담 실증 연구 v0.1
기준일: 2026-10-21. 상태: CANDIDATE / 연구 전용. 기존 v2·P0 베이스라인 보존.

## 요약
1. Oracle FY2027 Q1 10-Q (2026-08-31): 약 $288bn 미개시 추가 임대약정. 대체로 데이터센터, FY2027 Q2~FY2029 개시 예정, 15~19년 기간. **현재 인식 차입금과 합산 금지**; 계약총액과 할인현재가치 구분 필요. 현금 CAPEX FY2027 Q1 $28.5bn vs 전년 동기 $8.5bn. 공식 문서의 현금흐름 기간과 별도 확인.
2. CoreWeave: Reuters 2026-10-15 약 $50bn 채무(보도 정의에 주의), CDS 약 1000bp, 2025 Microsoft 매출 비중 약 67%. Nvidia는 2026-01 $2bn 지분투자와 2032년까지 최대 $6.3bn 미판매 용량 구매지원 계약. 지원 약정 총액을 부도 손실액으로 계산하지 않음.
3. Reuters Breakingviews 2026-10-20: 최근 일부 CoreWeave 금융은 3년 고객계약에 5년 차입을 연결해 재계약·잔존가치 위험이 존재할 수 있음. 원계약 검증 필요.
4. S&P Global 2026-10-19: 하이퍼스케일러 AI 관련 연결구조의 숨은 의무 가능성을 경고했으나 당시 추가 등급조정 불필요 견해. S&P Global 2026-08-27: SPV, JV, 잔존가치보증(RVG), 리스가 신용분석 복잡성을 높임.

## 위험 전달 경로 (확인 vs 가설)
A. Nvidia --[확인: 지분투자·미판매 용량 구매지원]--> CoreWeave --[확인: 클라우드 공급]--> Microsoft 및 AI 모델 개발사.
B. 은행·사모신용 --[확인: 담보대출·DDTL]--> CoreWeave/SPV --[확인: GPU·시설]--> 고객. 고객 계약의 종료일과 차입 만기 불일치 = 재계약/차환 위험 가설.
C. Oracle --[확인: 미개시 임대약정]--> 데이터센터 개발·임대 주체 --[추정: 외부 조달 필요]--> 프로젝트 금융시장. Oracle의 보증/소구 범위는 계약별 미확인.
D. AI 기업 채권 발행 증가 --[가설]--> 국채 수요 잠식/기간프리미엄 상승. 국채 입찰 및 기간프리미엄 독립 확인 전 미승인.

## 노출 측정: 절대 단순합산 금지
- 인식된 금융부채: 연결 총차입금 및 만기별 원리금.
- 리스: 이미 인식된 리스부채 vs 아직 개시되지 않은 계약총액(별도); 할인율과 계약개시일.
- 구매약정: 최소구매/선급/조건부 구매, 계약 취소 가능성.
- 보증·RVG: 최대 지급노출, 발동조건, 상대방, 담보, 예상손실은 별도.
- SPV/JV: 연결 여부, 지급보증·환매·운영지원, 최종 소구 주체.
- 계약잔고(RPO): 확정 매출 아님; 이행·전력·가동·고객 지급능력 필요.
- 회계현금흐름: OCF-Cash CAPEX를 FCF로 정의하고 리스 금융 및 비현금 GPU 취득 별도 표기.

## P0 검증 항목
1. Oracle 10-Q 원문에서 $288bn 계약 개시일·기간·해지조항·리스 유형, FY2027 Q1 CAPEX 및 현금흐름 대조.
2. CoreWeave 10-Q와 대출약정에서 DDTL 실제 인출·미인출, 담보, 보증, 만기, 고객계약 종료일 및 Nvidia 지원 발동조건.
3. Nebius/IREN/Applied Digital과 MSFT/AMZN/GOOGL/META 최신 공시 동일 스키마 정렬.
4. 신용시장: 동일 신용등급·만기 비AI 회사채 스프레드, IG/HY OAS, 은행·사모신용 노출. 데이터 지연·중복 신호는 독립확인 불인정.
5. RISE ETF 실제 보유 종목·비중·벤치마크 확인 후 노출 매핑.

## 잠정 평가
기업별 스트레스 관측 가능, 시스템 전염은 UNCONFIRMED. 내부 2026-10-20 기준 레짐 gate CHALLENGE, 검증 INSUFFICIENT_HISTORY. 투자 신호 및 레짐 승격 금지.

## 근거
- Oracle 10-Q 원문 재현: https://companiesmarketcap.com/oracle/sec-reports-10q/0001193125-26-389274/
- Oracle MD&A: https://filings.tools/orcl/10-q/2026-08-31/item-2
- Reuters CoreWeave 계약·대주단: https://www.investing.com/news/stock-market-news/factboxcoreweaves-ai-contracts-and-the-lenders-financing-its-buildout-4952427
- Reuters Breakingviews: https://www.breakingviews.com/40925ca4af2b/columns/considered-view/nvidia-emerges-central-bank-ai-2026-10-20/
- S&P Global 보도자료: https://press.spglobal.com/2026-08-27-AI-Infrastructure-Investment-To-Exceed-1-3-Trillion-By-2027%2C-S-P-Global-Ratings-Says
- Reuters S&P 경고: https://www.investing.com/news/stock-market-news/top-hyperscalers-likely-to-have-more-ailinked-debt-than-now-known-sp-global-warns-4958070
