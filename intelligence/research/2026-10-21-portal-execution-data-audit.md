# RISE Portal 실행·배포 경로 및 데이터 구조 점검 — 2026-10-21

상태: VERIFIED_PARTIAL. 본 문서는 GitHub Actions 실제 실행 로그와 main 저장소 파일 확인 결과를 기록하며, 최종 공개 URL 검증을 완료했다고 주장하지 않는다.

## 실행 경로 실증
- GitHub Actions run 39521283497 / job 118965449187: completed, success.
- 엔진·게시 게이트 테스트 및 실행: 성공. publication receipt status PUBLISHED, full_report SUCCESS, archive_count 16.
- 아티팩트: intelligence-run-39521283497-1, ID 12310249792, SHA256 e31abb72ddb7a5f43dc5bf5acb52ef0f8a58947842bc9acf14ddb6879ef2a1c6.
- git commit: 7fd6876, HEAD -> main push 성공 (로그 2026-10-21 00:26:18 UTC).
- GitHub Pages: source branch main, path /, legacy build POST 접수, API 응답 status queued (2026-10-21 00:26:21 UTC).
- **미확인**: Pages build final status, 공개 사이트 HTML/JSON의 200 및 내용 일치, CDN 캐시, 최근 대시보드 수정 커밋의 실제 반영.

## 데이터 구조·무결성
- data/operations/intelligence.json: checkout 단계의 PUBLISHED; Git push 및 Pages 배포 성공과 별도.
- intelligence/data/latest.json: asof_date 2026-10-21, report_mode DATED_OBSERVATIONS_V1, regime_reference_date 2026-10-15, regime_assessment CARRIED_FORWARD_NOT_RECONFIRMED, production_eligible false. 이월 레짐을 당일 신규 판단으로 표시 금지.
- data/signals/latest.json: built_at_utc 2026-10-21T00:26:15Z, 관측일 혼재. SIG-CREDIT-001 NORMAL, IG OAS 0.87%p 및 HY OAS 3.29%p 관측 2026-10-19.
- data/regime/gate_latest.json: CHALLENGE, independent_persistent_channel_count 1 (VOLATILITY), CREDIT/FUNDING no episode, regime_change_authorized false. RATES 두 신호 DGS10 중복 채널 미산입.
- data/quality/krx_rise_inventory.json: observed_on 2026-10-20, observed_count 145. 당일 실시간 상장 수로 표현 금지.
- dashboard.js: 발행/배포 구분, 신호 실제 관측일, 레짐 이월 표시 개선.

## 수집 장애 단서
- 같은 실행의 테스트 로그에서 KB Asset Management Finder 검증에 TimeoutError 및 incomplete page 사례 출력. 테스트 fixture의 오류 출력인지 실제 정기 수집 실패인지 분리 검증 필요. KRX 종목 관측 파일이 존재한다는 사실만으로 Finder 검증 성공을 추정하지 않는다.

## 필수 후속 검증
1. Pages build 최신 status 및 배포 커밋 SHA 확인; URL index.html, dashboard.js, data/operations/intelligence.json, intelligence/reports/2026-10-21.html 각각 HTTP status/캐시/콘텐츠 SHA 비교.
2. collector별 latest_successful_observation, last_attempt, source_status, error_code, fallback_age, publication_eligible 별도 공개. 실패 시 기존 검증값 보존 및 실패 시각 공개.
3. GitHub Actions run receipt에 git_push_status, pushed_commit_sha, pages_build_request_status, pages_build_final_status, public_smoke_test_status를 **별도 기록**. Pages 빌드 후 별도 잡/워크플로로 확인해야 함.
4. KR ETF 공식 마스터와 KRX 관측 인벤토리의 분류·상장폐지·상품명 차이 검증. 수치 145는 10/20 KRX 관측값.
5. 외부 URL 검증 도구가 해당 페이지에 접근하지 못했으므로 실제 브라우저/HTTP 200 검증 완료로 표시하지 않음.

## 안전 조건
CANDIDATE/SHADOW 상태의 신호를 실전 신호로 승격 금지. 지연자료와 중복 기초계열을 독립 확인으로 계산 금지. 데이터 오류 발생 시 새 가격/날짜 생성 또는 최신값 덮어쓰기 금지.
