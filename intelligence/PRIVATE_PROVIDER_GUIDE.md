# 개인용 FunETF 파일 누적 및 비교

2026-10-21 사용자 지시: 본인 열람용. 원본·정규화값·DB·상세 화면은 공개 저장소와 Pages에 올리지 않는다. 공개 포털 첫 화면은 유지한다. 앞선 FUNETF_HANDOFF_20261021의 허가 확인 대기는 공개 배포/무인 수집에 관한 경계로 남기고, 사용자 요청에 따라 개인용 로컬 파일 처리를 구현했다. 이것이 제공처의 이용허가를 새로 확보했다는 의미는 아니다.

## 사용

Python 3.11 이상과 openpyxl 3.1.5 필요. 기존 저장소에서:

```
python -m pip install openpyxl==3.1.5
python scripts/process_etf_provider_inbox.py
python scripts/process_etf_provider_inbox.py --watch --interval 60
```

FunETF 일반 다운로드 기능으로 받은 국내 ETF 엑셀을 `var/provider_inbox`에 저장한다. 감시 프로그램이 실행 중이면 60초 간격으로 같은 검증 파이프라인을 적용한다. `var/provider_private/index.html`을 브라우저에서 열고, 갱신 후 새로고침한다. 프로세스가 종료되거나 PC가 꺼지면 감시도 중단된다. 이 작업 공간에 상시 감시가 설정된 것은 아니다. GitHub Actions는 공개 코드와 합성 테스트만 실행하며 회원 세션·비밀번호로 다운로드하지 않는다.

선택적으로 `파일.xlsx.json`에 다음을 넣는다. 비밀번호/토큰은 허용 필드가 아니며 저장 금지:

```json
{"source":"funetf","market":"KR","retrieved_at_utc":"2026-10-21T04:35:00+00:00","observation_date":null,"screen_date":"2026-10-20"}
```

예시 시각은 해당 다운로드 확인 분 단위 기록이다. 실제 입력 시에는 자신의 파일 입수 시각을 사용한다. sidecar가 없으면 파일 수정시각을 사용하므로 새로 복사한 파일의 수정시각과 실제 다운로드 시각이 다르면 sidecar로 구분한다. 관측일이 확인되지 않으면 null을 유지한다. 화면 기준일만으로 수익률·보수·구성종목의 개별 관측일을 확정하지 않는다. 서로 다른 기준일의 자료를 현재값으로 합치지 않는다.

KRX 비교는 `data/quality/krx_rise_inventory.json`의 최신 관측 RISE 목록이다. 저장소를 최신 main으로 갱신해야 최신 KRX 저장본을 사용한다. 전체 국내 ETF 비교 또는 공시 기반 상장폐지 확정으로 확대 해석하지 않는다.

## 결과와 보존

- raw/{sha256}/original.xlsx: 파일 원본. 잘못된 입력도 원본 보존 후 실패 기록.
- provider.sqlite: 파일별 captures, ETF별 observations, KRX 대조 reconciliations, 직전본 대비 changes. 트랜잭션 실패 시 누적 취소.
- index.html: 외부 요청 없는 개인용 검색·상세·선택 ETF 비교 화면. 총보수/TER/실부담비율, 순자산(억원), 기간 수익률, TOP3와 출처/기준일 표시.
- status.json 및 runs/: 실행 상태, 원인, 마지막 성공 시각. 일부 파일 실패는 PARTIAL. 마지막 성공은 검증 처리 성공 시각이며 새 데이터 발표 시각이 아니다.

동일 해시 파일은 DB에서 중복하지 않는다. 같은 원본에 관측일을 다르게 지정하면 충돌로 차단한다. 과거 기준일 파일은 보존하지만 최신 화면을 과거로 돌리지 않는다. 제공처에서 빠진 종목을 상장폐지로 간주하지 않으며 KRX 원천은 수정하지 않는다. 새 파일의 항목 변화는 changes에 남긴다. 신규 기준 파일은 BASELINE이고 신규상장으로 판정하지 않는다.

출력 경로를 저장소 안으로 지정하면 var 하위만 허용한다. var 및 SQLite는 기존 .gitignore로 제외된다. .processing.lock가 남으면 실행 프로세스가 없는지 확인하고 원인 확인 후 제거한다. 원본과 DB는 삭제하지 않는다.

## 실제 실행

직접 다운로드한 1,181행/22열 파일로 성공, 재실행은 DUPLICATE, DB captures=1 / observations=1181. KRX RISE145 vs 보조144, 미수록0254H0 유지. 누락된 기간 수익률은 null, TOP3는 전체 보유내역이 아님. 미국5,731건 화면은 확인했으나 일괄다운로드 버튼은 없어 실제 미국 파일 수집은 미완료. 미국 티커를 국내 코드로 처리하지 않고 미검증 US 입력을 차단한다.

로컬 165 Python 테스트 통과: DB 롤백, 중복, 과거파일 최신유지, 실패 시 정상화면유지, 날짜충돌, 공개출력차단, 렌더링 주입방지. 브라우저 상호작용은 CI의 합성자료로 검증한다. 실데이터 HTML을 Cloud Browser에서 열려던 시도는 file 프로토콜 정책으로 차단됐으며 우회하지 않았다. 실데이터 화면의 클라우드 시각검수는 미완료다.

남은 사항: 무인 FunETF 로그인/정기 다운로드는 미설정; 현재는 사용자 다운로드+실행 중인 로컬 폴더 감시 방식. 미국 다운로드/공식 유니버스 연결, 전체시장 KRX 대조, 거래소 공시 기반 상장폐지 확정, 공개 포털 수치 연동은 미완료. 개인 자료를 공개 GitHub Pages로 배포하지 않는다.

## 포털 ETF 탐색 연결
수집기 실행 후 생성되는 `var/provider_private/portal.json`을 공개 포털 `etf.html`의 개인용 데이터 연결에서 선택합니다. 미국 목록은 `var/us_etf_directory/latest.json` 또는 GitHub Actions `us-etf-state` 보관파일의 `latest.json`을 선택합니다. 원본 XLSX를 직접 선택하는 기능은 아닙니다. 파일은 브라우저 메모리에서만 사용하고 새로고침 시 해제됩니다. 현재 KRX RISE 목록을 기본으로 유지하며 미수록 종목을 삭제하지 않습니다. 미국 자료는 종목 식별 목록만 표시합니다.
