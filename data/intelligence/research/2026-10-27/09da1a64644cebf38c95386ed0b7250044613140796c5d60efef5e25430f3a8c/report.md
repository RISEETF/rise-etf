# RISE 자동 연구 초안 — 2026-10-27
검토용 · 정식 보고서 아님 · 투자판단 및 외부 마케팅 사용 불가

## 게시 차단 사유
원천 차단 없음; FULL 검토 별도 필요

## 원천 관측 (발행일과 구분)
- BAMLC0A0CM | 2026-10-23 | 0.91 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLC0A0CM
- BAMLH0A0HYM2 | 2026-10-23 | 3.38 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2
- DCOILBRENTEU | 2026-10-20 | 115.22 USD/bbl | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU
- DCOILWTICO | 2026-10-20 | 107.89 USD/bbl | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO
- DGS10 | 2026-10-23 | 5.0 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10
- DGS2 | 2026-10-23 | 4.69 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2
- DTWEXBGS | 2026-10-23 | 121.3202 Index | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS
- SOFR | 2026-10-23 | 3.92 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR
- T10Y2Y | 2026-10-26 | 0.32 Percent | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y
- VIXCLS | 2026-10-23 | 19.45 Index | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS
- WRESBAL | 2026-10-21 | 2962607.0 Millions USD | 신선도 통과 | https://fred.stlouisfed.org/graph/fredgraph.csv?id=WRESBAL

## 기존 엔진 신호 (새 판단 아님)
- SIG-RATE-001: NORMAL / DOWN / 연구 연결 가능
- SIG-RATE-002: NORMAL / DOWN / 연구 연결 가능
- SIG-CREDIT-001: WATCH / UP / 연구 연결 가능
- SIG-LIQ-001: NORMAL / UP / 연구 연결 가능
- SIG-FX-001: NORMAL / DOWN / 연구 연결 가능
- SIG-ENERGY-001: WATCH / UP / 연구 연결 가능
- SIG-MKT-001: NORMAL / DOWN / 연구 연결 가능
관문 원본: {'state': 'CHALLENGE', 'independent_persistent_channels': 0, 'usable': True} / 검증: INSUFFICIENT_HISTORY

## RISE 상품 조사 목록 (상품명 일치만 확인; 추천 순위 아님)
- 0122W0 RISE 26-11 회사채(AA-이상)액티브 (2026-10-26) ← SIG-CREDIT-001: 신용스프레드 변화와 이자수익의 상충 관계 점검; 필요 확인: 신용등급·만기·유동성·국가 차이를 확인
- 136340 RISE 중기우량회사채 (2026-10-26) ← SIG-CREDIT-001: 신용스프레드 변화와 이자수익의 상충 관계 점검; 필요 확인: 신용등급·만기·유동성·국가 차이를 확인
- 437350 RISE 미국단기투자등급회사채액티브 (2026-10-26) ← SIG-CREDIT-001: 신용스프레드 변화와 이자수익의 상충 관계 점검; 필요 확인: 신용등급·만기·유동성·국가 차이를 확인

## 반론·오판 점검
- 같은 원천 시계열을 공유하는 신호는 독립된 시장 확인으로 합산하지 않는다.
- 금리 하락만으로 성장 둔화와 인플레이션 완화를 구분할 수 없다. 신용·수급 등 독립 근거가 필요하다.
- 관측 지연·수정과 서로 다른 관측일은 동일 시점 시장 움직임으로 해석하지 않는다.

## 미완료 평가
- 레짐 신뢰도·흡수력 점수: 승인된 산출 근거가 없어 미산정
- 투자자 수급: 투자자 유형별 원천·시장폭·집중도·지속성 검증 필요
- 경쟁상품: 동일 노출의 보수·유동성·추적오차·자금유입 비교 미완료
- 신상품: 기존 상품 중복·수요·지수 구현·거래비용 검증 전 점수 및 출시 판단 보류
- 정식 FULL 보고서: 외부 근거와 반론을 검토한 최종 판단 패키지 필요

## 다음 조치
- 차단 원천의 새 관측값을 수집하고 전체 체인을 다시 실행
- 후보 ETF 공식 투자설명서의 실제 노출·환헤지·듀레이션 확인
- FULL 패키지의 수치·외부 근거·반론 검토 후 기존 게시 검증 실행
