# AI CAPEX·신용전파 P0 — 기업별 비교 및 연결지도 (2026-10-21)

**상태:** CANDIDATE / RESEARCH_ONLY. 출처와 관측일 없는 수치는 UNAVAILABLE. 투자·상품·레짐 변경 승인 불가. 선행 연구: 2026-10-21-ai-credit-transmission-v2.md.

## 결론과 강한 반론
- **가설:** AI 인프라의 자본조달 비용 상승이 선행 투자와 매출 실현 간 시차를 통해 차입 의존 기업을 압박하고, 프로젝트·공급망으로 전파될 수 있다.
- **반론:** 글로벌 은행의 CoreWeave 직접 노출은 담보와 SPV 구조로 보호될 수 있고, 대형 기술기업은 현금창출력·장기계약으로 충격을 흡수할 수 있다. 채권가격 급락이 전체 AI 수요 붕괴를 증명하지는 않는다.
- **내부 판정:** GitHub 2026-10-20 생성본 gate=CHALLENGE, independent persistent channels=0, watch=1, override=false, validation=INSUFFICIENT_HISTORY. 신용 SIG-CREDIT-001 NORMAL, Z=+1.28(관측 2026-10-16). 현재 레짐 변경 없음.

## 기업 비교 — 정량 값의 정의를 엄격히 구분
| 기업 | 사업군 | 확인된 최근 근거 | P0 미확보/검증 항목 | 예비 위험 축 |
|---|---|---|---|---|
| CoreWeave | 네오클라우드 | Reuters 2026-10-20: 채무 약 $50bn(금융약정/인출액과 중복합산 금지), 2031년 채권 수익률 약 16%; Reuters 2026-10-15: Microsoft가 2025 매출 67% | 최신 분기 연결총부채·현금·CAPEX·FCF·만기·SPV별 소구구조 | 고객 집중·차환·선투자 시차 |
| Oracle | 기업 소프트웨어+클라우드 | S&P Global 2026-10-19 보도: 2026년 7월 신용등급 하향; AI 투자 관련 복잡한 채무·우발부담 경고 | 최신 10-Q 현금/영업현금흐름/CAPEX/FCF, 발행·리스·RPO 현금화 | 기존 사업의 흡수력 대 AI 투자속도 |
| Nebius | 네오클라우드 | Reuters 2026-10-14: 고금리 우려로 관련 주가 급락(주가만으로 신용위기 확증 불가) | 차입 구조, 계약 고객, RPO, 현금소진, 시설별 가동 | 계약 집중·신규조달 |
| IREN | 데이터센터·GPU 인프라 | Reuters 2026-10-14: 관련 주가 급락 | 프로젝트별 CAPEX, 담보·비소구, 전력, 계약수익, FCF | 전력·시설·조달 |
| Applied Digital | 데이터센터 개발 | Reuters 2026-10-14: 관련 주가 급락 | 시설별 임대계약, 건설비, 선순위 담보, 완공일, 차환 | 프로젝트 건설·임대 |
| Microsoft | 하이퍼스케일러 | CoreWeave 2025 매출 67% 고객(Reuters 10/15) | 최신 공시 CAPEX·리스약정·FCF·공급자 의존 | 수요자이자 자금 제공자 역할 |
| Amazon | 하이퍼스케일러 | S&P Global 10/19: AI 관련 채무의 가시성 한계 지적 | CAPEX/OCF, AWS 수익화, 리스·SPV | 규모 대비 현금흐름 |
| Alphabet | 하이퍼스케일러 | 동일 | CAPEX/OCF, 클라우드 수익화, 리스·채권 | 자본생산성 |
| Meta | 하이퍼스케일러 | 동일 | CAPEX/OCF, AI 직접 수익화, 장기약정 | 수익화 시차 |
| Equinix / Digital Realty | 데이터센터 REIT | 개별 수치 미확보 | 조달금리, 임대·전력, REIT 재무제약 | 장기 자산 차환 |

## 전파 지도 (가설/확정 관계 구분)
- Microsoft → CoreWeave: **확인된 고객 매출 의존**(2025년 매출 비중 67%). 계약 변경·수요 축소가 CoreWeave 현금흐름에 미치는 정도는 미검증.
- CoreWeave ↔ 은행/사모신용/SPV: **확인된 자금조달 구조**. J.P. Morgan의 은행 위험 제한 평가는 반론으로 기록. 전체 은행 손실 추정은 하지 않음.
- CoreWeave/네오클라우드 → GPU·전력·냉각·네트워크: **산업 연결은 명확, 기업별 매출 충격은 미측정**.
- AI 회사채 발행 → 미국 국채 수요 잠식: **작업가설, 미확인**. 국채 입찰·기간프리미엄·외국인 수요와 독립 검증 필요.
- 고객 RPO/계약잔고 → 실제 현금흐름: **시차와 이행·취소 조건 확인 필요**. 계약잔고를 현금과 동일시 금지.

## P0 표준 계산식
1. CAPEX 부담 = 현금 CAPEX / 영업현금흐름(OCF). OCF<=0이면 비율 무의미/별도 표기.
2. FCF = OCF - 현금 CAPEX. 금융리스·GPU 담보구매는 별도 재구성.
3. 차환압력 = 36개월 만기 원리금 / (현금 + 제한 없는 미사용 약정 + 검증 가능한 FCF). 분모 음수/미확보 시 산출 금지.
4. 신용시장 검증 = 개별 발행사 채권 OAS 또는 동일 만기 국채 대비 스프레드와 동급 비AI 발행사 비교. CDS bp는 확정 부도확률이 아님.
5. 프로젝트 흡수여력 = 사용가능 자금 - 확정 잔여 건설비 - 12개월 만기 원리금. 프로젝트별 소구·비소구 구분.
6. 고객집중 = 최대 고객 매출 / 총매출. RPO 집중과 구분.
7. 증분 ROIC-WACC = 신규 프로젝트 세후영업이익/증분 투자자본 - 가중평균자본비용. 세부 수치 없으면 UNAVAILABLE.

## 우선 검증 큐
- P0-A: 9개 핵심기업 최근 10-K/10-Q 원문 기준 표 작성. 각 수치에 회계기간·발표일·단위·원문 URL 필수.
- P0-B: CoreWeave/Oracle의 차입·리스·SPV·고객계약 연결관계; 계약자와 채권자의 법적 주체 식별.
- P0-C: 대조군: 동일 신용등급 비AI 발행사와 신용스프레드 비교, 유사 만기 조정.
- P0-D: 이익·수익률 아닌 실현 현금흐름으로 기업을 평가하고 RISE ETF 실제 편입 확인 후 상품 검토.

## 공개 근거
- Reuters 2026-10-20 CoreWeave 채무·은행 반론: https://www.reuters.com/business/finance/coreweave-debt-selloff-poses-limited-risk-global-banks-jp-morgan-says-2026-10-20/
- Reuters 2026-10-15 고객·대주단·차입구조: https://www.reuters.com/legal/transactional/coreweaves-ai-contracts-lenders-financing-its-build-out-2026-10-15/
- Reuters 2026-10-19 S&P Global 경고: https://www.reuters.com/business/top-hyperscalers-likely-have-more-ai-linked-debt-than-now-known-sp-global-warns-2026-10-19/
- Reuters 2026-10-14 네오클라우드 주가: https://www.investing.com/news/economy-news/ai-infrastructure-firms-slump-as-us-rate-hike-bets-rise-4949759

**검증 메모:** 이 문서는 P0 기업군·공개 근거·관계·계산식의 첫 실증 베이스라인이다. 기업별 최신 공시 전체 수치 입력·점수 산출·전파의 인과 검증은 아직 완료되지 않았다.
