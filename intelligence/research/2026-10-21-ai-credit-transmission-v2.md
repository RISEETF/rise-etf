# AI CAPEX·신용전파 연구 v2 (2026-10-21)

상태: CANDIDATE. 투자·레짐·상품 승인 불가. 기존 연구 v1 보존. 내부 관문은 2026-10-20 생성본 기준 CHALLENGE, 독립 지속 채널 0, 관찰 1, 검증 INSUFFICIENT_HISTORY.

## 1. 분석 범위
- 네오클라우드: CoreWeave, Nebius, IREN
- 확장형 클라우드: Oracle
- 현금창출형 하이퍼스케일러: Microsoft, Amazon, Alphabet, Meta
- 데이터센터 개발·운영: Applied Digital, Equinix, Digital Realty
- 전파 수혜·피해 공급망: Nvidia, 메모리, 전력·냉각·네트워크
- 자금 제공자: 은행, 사모신용, 회사채, 프로젝트금융 SPV

## 2. 신규 관측 (발표일과 수치 구분)
- Reuters 2026-10-20: JPMorgan은 CoreWeave의 약 500억달러 채무, 약 240억달러 지연인출 약정(약 150억 인출, 90억 미인출), 2031년물 수익률 약 16%, 5년 CDS 약 1000bp를 논의. 은행 직접 위험은 담보·SPV 구조 때문에 제한적이라는 반론도 제시. https://www.reuters.com/business/finance/coreweave-debt-selloff-poses-limited-risk-global-banks-jp-morgan-says-2026-10-20/
- Reuters 2026-10-15: CoreWeave 2025년 매출의 Microsoft 비중 약 67%. 고객집중과 계약 잔고 현금화 시차 확인 필요. https://www.reuters.com/legal/transactional/coreweaves-ai-contracts-lenders-financing-its-build-out-2026-10-15/
- Reuters 2026-10-15: Oracle 5년 CDS 288bp(전일 대비 +26bp), CoreWeave 1000bp 이상. CDS는 채무불이행 보험 비용이며 신용위험의 시장 가격이지 확정 부도확률이 아님. https://www.investing.com/news/stock-market-news/ai-credit-default-swap-spreads-widen-sharply-4950549
- FT 2026-10-15: Hyperion, Excalibur 등 일부 데이터센터 프로젝트 채권이 액면가 아래로 거래. 개별 프로젝트 채권과 발행사 일반채 구분 필요. https://www.ft.com/content/678bcd31-6c2a-447b-a68c-ce6dec220bbc
- FT 2026-10-20: AI 관련 CDS 거래 증가; 거래량 확대 자체가 부도 확정이나 신규 현금유출을 의미하지는 않음. https://www.ft.com/content/6dd31584-064c-4015-bf5d-e5747799ccd5

## 3. 연구 설계: 충격→전파→흡수→적응→실패/레짐 변화
1. 충격: 장기금리, CDS, 신규발행금리, 전력·인허가 지연
2. 전파: 신규 투자 경제성, 차환, 프로젝트 SPV, 고객·GPU 공급망, 은행·사모신용
3. 흡수: 현금, 미사용 약정, 담보·계약의 질, 만기분산, FCF
4. 적응: CAPEX 조절, 고객가격 인상, GPU 재배치, 계약재협상, 자산매각
5. 실패: 프로젝트 연기, 차환 불가, 계약 취소, 신용시장 광범위 확산

## 4. 기업별 데이터 템플릿
기업/분기/자료일/출처, 현금·유동성, 총부채(연결/비연결 구분), 미사용 약정, 향후 3년 만기, 이자비용, 한계조달비용, CDS·채권수익률, CAPEX(현금/금융리스 구분), 영업현금흐름, FCF, 매출, 잔여계약잔고(RPO), 계약의 취소·가격변경 조항, 고객 집중, 가동률·전력 MW, 증분 ROIC-WACC, 신용등급·전망, SPV 보증/소구 구조.

## 5. 가설과 반증
H1 선별적 신용 스트레스: 네오클라우드/특정 프로젝트 집중. 반증은 동급 비AI 회사채·은행펀딩으로 지속 확산.
H2 AI 전반 CAPEX 수익성 저하: 신규 투자수익률이 한계 자본비용 하회, 프로젝트 취소·투자 축소로 이어짐. 반증은 가동률·매출·FCF 개선과 신규 발행 정상 소화.
H3 자금조달 구조가 충격을 흡수: SPV, 담보, 장기계약으로 직접 은행손실 제한. 반증은 보증·소구 확대, 담보가치 급락, 프로젝트 차환 실패.
H4 국채 수요 잠식: 회사채 순발행과 국채 입찰 수요/기간프리미엄의 동시 변화로만 판정. 단순 AI 회사채 공급 증가만으로 인정 금지.

## 6. 우선 작업
P0: CoreWeave/Oracle/Microsoft/Amazon/Alphabet/Meta/Nebius의 최신 10-Q/10-K 및 회사채 만기·현금흐름 표 작성. P1: AI 프로젝트 채권/SPV/사모신용 노출 연결지도. P2: ETF 기존 편입 중복·고객 수요·지속가능 자본생산성 상품성. 데이터 없는 값은 UNAVAILABLE; 추정은 ESTIMATE로 분리.

연구는 CANDIDATE 유지. 실시간 신용시스템 신호, 실제 부도확률, 레짐 전환을 단정하지 않음.
