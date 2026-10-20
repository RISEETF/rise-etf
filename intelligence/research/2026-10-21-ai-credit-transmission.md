# AI 자본투자·신용시장 전파 연구 — 2026-10-21

상태: CANDIDATE / 연구용. 데이터 vintage: GitHub main 2026-10-20 00:57 UTC 생성본. 최종 레짐 변경 권한 없음.

## 연구 질문
AI 설비투자 증가와 차입 확대가 자본비용·현금흐름·국채수요·주식 가치평가에 전파되는가? 개별기업 충격과 시스템 충격을 구분한다.

## 확인 사실
- DGS10 5.09%(10/16); DGS2 4.74%(10/16); T10Y2Y +0.38%p(10/19); SOFR 3.88%(10/16); WRESBAL 3,022,140 million USD(10/14).
- IG OAS 0.85%p, HY OAS 3.31%p(10/16); HY 직전 관측 대비 +8bp. 내부 CREDIT 신호 NORMAL, Z +1.2807.
- 금리 SIG-RATE-001/002는 같은 DGS10을 사용, 중복 독립 채널로 인정하지 않음. VIX SIG-MKT-001 Z +3.8529, ACTIVE_CANDIDATE, 에피소드 persistence 1회.
- Gate CHALLENGE, independent_persistent_channel_count=0, watch_channel_count=1, extreme_event_override=false. Validation INSUFFICIENT_HISTORY(신호 24/60, 에피소드·관문 24/40).
- Reuters(2026-07-29): hyperscaler 채권 발행 증가 및 수요 선별화 https://www.reuters.com/business/hyperscaler-debt-binge-pushes-yields-up-investor-demand-cools-2026-07-29/
- Reuters(2026-10-15): AI 데이터센터 자금조달과 CoreWeave 채권 우려 https://www.reuters.com/legal/transactional/coreweave-shares-bonds-slide-further-ai-debt-fears-mount-2026-10-15/
- Reuters(2026-08-19) 반론: AI 채권 공급이 자동으로 미국 국채 수요를 잠식한다고 볼 수 없음 https://www.reuters.com/commentary/reuters-open-interest/dont-blame-us-bond-market-indigestion-ai-debt-binge-mcgeever-2026-08-19/

## 경쟁 가설
H1 선택적 스트레스: 부채의존형 AI 인프라 기업만 조달비용 상승. 대형 우량기업 및 전체 신용시장으로 전염되지 않음.
H2 광범위 전파: AI 관련 채권 공급·프로젝트 지연·전력 병목이 신용 스프레드 확대, 투자 축소, 주가 재평가로 이어짐.
H3 흡수·적응: 장기계약, 프로젝트금융, 현금 보유, 투자 조절로 충격 흡수. 실물 수요가 CAPEX를 정당화.

## 판별에 필요한 관측
1. AI 발행사별 신규 발행 스프레드·CDS·채권 거래량과 동일 등급 비AI 기업의 상대 스프레드.
2. 만기별 차환액, 고정/변동금리 비중, 한계 조달비용, 현금흐름 대비 이자비용, 프로젝트 금융의 비소구 여부.
3. 분기별 CAPEX, 가동된 전력/GPU, 고객 계약 실현 매출, FCF 전환, 증분 ROIC-WACC.
4. 국채 입찰 응찰률·간접낙찰·딜러 재고·기간프리미엄 및 회사채 순발행을 함께 확인. 단순 발행액 증가만으로 crowding-out 판정 금지.
5. IG/HY/CCC OAS, 금융기관 펀딩·repo, 주식 시장폭 및 ETF/펀드 순유입의 독립 지속 확인.

## 반증과 승격 금지
- H2 반증: 비AI 동급 채권 스프레드 안정, repo 정상, CAPEX 생산성·FCF 개선, 신규발행 소화 양호.
- H1 반증: AI 외 신용·조달시장으로 확산되고 서로 다른 날짜에 독립 지속 신호 2개 이상 확인.
- 정책 대응은 별도 evidence_role=POLICY_RESPONSE이며 독립 확인이 아님.
- 이 연구는 CANDIDATE. 과거 오탐/미탐, 추가 설명력, 선행성, 중복성 및 의사결정 유용성 검증 전 VALIDATED 승격 금지.

## ETF 연구 연결
- 기존 RISE 미국S&P500/RISE 200의 AI·반도체 집중위험을 먼저 측정.
- 신규 '지속가능 자본생산성' 후보는 FCF 전환, 증분 ROIC-WACC, 차환 의존도, 고객 집중, 신용시장 검증, 가치평가, 기존 ETF 중복·자기잠식 점검 후 상품성 판단.
- 지금은 투자·마케팅 승인 신호가 아니라 심층조사 대상.
