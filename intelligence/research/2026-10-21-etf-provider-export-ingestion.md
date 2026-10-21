# ETFcheck·FunETF 보조 파일 수집 운영안 (2026-10-21)

## 구현
- 수집기: `scripts/import_etf_provider_export.py` (CSV UTF-8/CP949, XLSX openpyxl)
- 외부 사이트를 스크래핑하거나 비공개 API를 호출하지 않는다. 운영자가 제공되는 다운로드 기능을 통해 얻은 파일만 입력한다.
- 명령 예시: `python scripts/import_etf_provider_export.py --source etfcheck --file /path/to/export.csv --observation-date 2026-10-20`
- FunETF: `python scripts/import_etf_provider_export.py --source funetf --file /path/to/export.xlsx --observation-date 2026-10-20`
- 기본 출력: `var/provider_exports/{source}/{observation_date}/{sha256}/original.csv|xlsx` 및 `manifest.json`.
- 날짜는 파일 내 자료의 **실제 관측일**을 입력한다. 다운로드한 날짜와 다를 수 있다.
- 데이터는 QUARANTINED, publication_eligible=false. KRX 데이터·공식 상품 마스터를 덮어쓰지 않는다.
- 같은 해시의 원본은 중복 저장하지 않지만, 원본을 수집·검증한 사실은 운영기록으로 남길 수 있다.

## 확인 필요
- ETFcheck 웹 화면에 비교/구성종목/자금유입/월간 리포트 표가 있으나 직접 CSV/XLSX 다운로드 기능은 현재 미확인.
- FunETF의 일반 공개 파일 다운로드 기능도 미확인.
- ETFcheck 사이트는 사전 허가 없는 데이터베이스화를 제한한다고 명시. 이용 범위를 확인하지 않은 자동 스크래핑 및 대량 복제는 금지.
- 실제 샘플 파일을 확보한 뒤 헤더·단위·종목코드·자금유입 계산 정의를 검증하고 정규화 스키마를 설계해야 한다.
- 이 파일 수집기는 실제 파일이 확보되지 않은 상태이므로 실운영 통합·실행 검증 전이다.

## 검증 기준
1. 파일 관측일·발행일·다운로드일 구분.
2. 종목코드(6자리 및 영문 혼합 가능), 운용사, 통화, 단위 및 시세 기준일 일치.
3. 자금유입은 AUM 증감이나 거래대금과 혼동 금지.
4. 서로 다른 제공처의 불일치 값은 원본 유지 및 대조 큐에 보관.
5. 정규화 및 게시 승인 전에는 연구 참고용 파일 보관만 허용.

## 출처
- https://www.etfcheck.co.kr/mobile/main
- https://www.etfcheck.co.kr/?redirect=%2Fmobile%2Fscreener%2Fresult%2F%EA%B8%B0%EB%B3%B8%EC%A0%95%EB%B3%B4
