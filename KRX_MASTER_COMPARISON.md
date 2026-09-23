# KRX 기본 관측과 운용사 상품 상세 대조

KRX ETF 일별매매정보는 거래소 관측 자료이며 법적 상장·상장폐지 공시가 아니다. 운용사 상품 목록에 있는 종목을 거래소 코드로 대조하고, 운용사 코드가 없는 경우에만 명칭 일치 후보를 제시한다. 후보로 원래 상품 코드를 덮어쓰거나 RS 가격 수집에 연결하지 않는다.

## 판정

| 상태 | 의미 |
|---|---|
| MATCHED_CODE_NAME | 코드와 공백·유니코드 정규화 명칭 일치 |
| NAME_DIFFERENCE | 코드 존재, 명칭 차이 확인 필요 |
| CODE_PENDING_NAME_CANDIDATE | 공식 코드 대기 상품에 명칭 일치 거래소 코드 후보 1개 |
| IDENTITY_REVIEW_REQUIRED | 복수 후보, 6자리 이외 코드, 기존 코드와 후보 충돌 |
| LISTED_AFTER_KRX_DATE | 운용사 상장일이 KRX 관측일보다 나중이며 해당 코드가 관측되지 않음 |
| NOT_OBSERVED | 해당 코드가 그날 응답에 없음. 상장폐지 판정 금지 |
| NO_NAME_CANDIDATE | 코드 대기 상품의 명칭 후보 없음 |

운용사 확정 코드와 미연결된 KRX RISE 명칭도 별도로 표시한다. 이름만 일치한 후보는 이 목록에도 남는다. 브랜드 접두어는 조사 대상을 찾는 용도이며 법적 운용사 식별을 확정하지 않는다.

## 자동 실행과 증거

- 기존 GitHub Secret `KRX_AUTH_KEY`를 사용하는 수집기 안에서 대조한다. 평일 한국시간 08:00·18:30 예약과 수동 실행을 지원한다.
- 요청일과 응답 기준일 일치, 전체 시장 수량·필드 충족률·이전 수량 급감·7일 초과 지연을 검사한다. NaN/Infinity를 거부한다.
- `data/quality/krx_master_reconciliation.json`에 종목 식별 대조·기준일·원문 해시를, `data/krx_collection_status.json`에 최근 시도 상태를 기록한다. 시장 가격 원문·DB·인증키는 공개 비교 파일에 넣지 않는다.
- 실패하면 마지막 성공 대조를 유지하고 실패 상태를 공개한다. 더 과거 관측일로 공개 대조를 되돌리지 않는다.
- 운용사 목록이 먼저 바뀌면 포털은 기존 비교를 현재 결과로 표시하지 않고 재대조 대기로 전환한다. 수집 시각이나 원문 가격만 달라진 경우는 상품 식별 필드로 동일성을 판정한다.
- 새 파일 두 개만 커밋하고 기존 Pages 후속 실행에 연결한다. 모든 데이터 쓰기 작업은 같은 동시 실행 그룹을 사용한다.
- 기존 KRX 누적 DB·30일 artifact 보관을 유지한다. 캐시/단기 artifact는 영구 백업을 대체하지 않는다.

## 남은 경계

법적 상태를 확정하려면 KIND 신규상장·상장폐지 공시의 문서 식별자, 종목 식별자, 효력일과 정정/철회 여부를 별도 수집해야 한다. 이번 대조에는 그 확정 기능이 없다. 일별 응답 누락을 근거로 종목이나 과거 가격을 삭제하지 않는다.

공식 출처:
- https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd
- https://kind.krx.co.kr/disclosure/disclosurebystocktype.do?method=searchDisclosureByStockTypeEtf
