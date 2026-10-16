# RISE Intelligence 2.0 — 운영 단순화 및 자동화 전환 (2026-10-16)

## 최종 목표
시장 데이터 수집 → 신선도·원천 검증 → 신호·레짐 사전관문 → Daily 최종 판단 → 기존 RISE ETF·상품기획 연결 → 한 번의 원자적 게시. 기존 00~07 연구 규정 및 원천 이력을 보존한다.

## 실제 저장소 확인
- 이미 존재하는 단일 게시기: `scripts/update_intelligence_portal.py` (snapshot+narrative 입력, 일별/latest/archive/HTML 생성, 동일일자 이전 JSON vintage 저장)
- 검증기: `scripts/validate_intelligence_snapshot.py` 및 `tests/test_intelligence_portal.py`
- 검증 워크플로: `.github/workflows/intelligence_portal_validate.yml`은 수동·PR만 실행. 매일 예약 자동 게시가 아니다.
- 원천 데이터 예약 실행: `daily_update.yml`, `gclri_market_update.yml`, `master_update.yml` 등은 별도 실행. `refresh_pages.yml`은 일부 수집 워크플로 완료 후 Pages 빌드를 요청한다.
- 현재 Daily 작성·검증·게시를 하나로 묶는 예약 오케스트레이터는 확인되지 않았다. 따라서 데이터 수집 성공과 Daily 발행 성공은 별개이다.

## 즉시 적용할 설계 원칙
1. 기존 게시기를 재사용한다. 보고서 HTML·일별 JSON·latest·archive를 GitHub API로 개별 수동 갱신하지 않는다.
2. 단일 일자별 입력 패키지: `snapshot.json` + `report.txt` + 내부 데이터 vintage/원천 근거. 모든 분석은 원천 관측일과 발행일을 구분한다.
3. 원천 데이터·신호·에피소드·레짐 관문·검증 상태를 분리한다. 레짐 관문은 최종 의사결정이 아니다.
4. `SUMMARY_ONLY`는 복구·호환 용도이며, 정기 자동 발행은 기존 검증기가 요구하는 `FULL` 형식으로 한다.
5. 게시 전 검증: 스키마, 동일일자 vintage, HTML 생성, 모든 보관일 JSON/링크, 원천 신선도, 외부 근거, 프레임워크 승격 여부.
6. 게시 원자성: 임시 작업 디렉터리에 전체 결과 생성 → 검증 통과 → 한 커밋으로 게시. 실패 시 latest/archive는 이전 정상본 유지.
7. 동일일자 수정은 원본 및 이유를 vintage에 남긴다. 이전 결론을 조용히 덮어쓰지 않는다.
8. 보고서가 없거나 외부 근거가 불충분하면 실패/부분 성공으로 명시한다. 자동으로 시장 전망을 만들어내지 않는다.

## 단계별 구현
### P0 — 기존 자산 재사용과 장애 제거
- 기존 게시기와 테스트를 로컬/CI에서 실행해 정상 동작 기준선 확보
- 게시기의 부분 쓰기 위험 제거(현재 일별/latest/archive 쓰기가 HTML 생성보다 앞선다)
- `intelligence_portal_validate.yml`의 보관 링크 및 latest/date 정합성 검사 강화
- `report_status`와 실제 HTML 존재 여부를 일치시킨다

### P1 — 하루 한 번 실행
- 기존 수집 워크플로가 완료된 뒤 단일 Daily 실행을 시작하는 오케스트레이터 추가
- 자료 신선도 기준 미달·검증 실패 시 보고서를 게시하지 않고 장애 로그만 기록
- 동일 날짜 중복 실행 시 불필요한 신규 vintage 생성 금지

### P2 — 실무 의사결정 품질
- Daily 요약 + 반론/반증 + RISE 상품 연결 + 신규 ETF 후보의 근거와 상품 중복 검증
- Flow는 원천·투자자 유형·시장폭·집중도·지속성 교차확인 전까지 미확정 유지
- RS는 가격 조정·배당·거래일·환율 정합성 검증 전까지 연구용

## 변경 통제
이번 문서는 설계·감사 기록이며 자동화 배포 완료를 뜻하지 않는다. `.github/workflows`, `scripts`, `data` 변경은 별도 구현·테스트 후 수행한다. 운영 중인 수집기·레짐·검증 규칙을 임의 수정하지 않는다.

## P0 구현·운영 경계 (2026-10-16)

게시기는 기존 portal을 임시 디렉터리에 복사하고 보고서·daily/latest·archive·framework history·vintage를 모두 만든 다음 전체 보관 링크와 latest 정합성을 검증한다. 검증 전에는 기존 portal을 수정하지 않는다. 작업 디렉터리 교체 중 예외는 이전 디렉터리로 rollback한다. 과거 날짜 보완 시 latest는 최신 날짜를 유지한다.

동일 날짜 snapshot 또는 HTML 수정은 `--revision-reason '수정 이유'`가 필요하다. 이전 JSON·HTML·수정 이유는 `data/vintages/<date>/<UTC timestamp + UUID>/`에 함께 보존한다. 기존 vintage 형식도 삭제하지 않는다. 동일 입력 재실행은 신규 vintage를 생성하지 않는다. FULL만 정기 게시하며 빈 본문은 차단한다. 과거의 명시적 SUMMARY_ONLY/pending 기록은 그대로 허용한다.

**원자성 경계:** 이 스크립트는 Git checkout용이다. 두 번의 디렉터리 rename 사이에는 짧은 공백이 있으므로 live HTTP 디렉터리를 직접 대상으로 사용하지 않는다. 검증된 전체 변경을 한 Git 커밋으로 push하고 Pages가 그 커밋을 배포해야 공개 게시가 일관된다. P0는 자동 commit/push나 Pages 배포 성공을 보장하지 않는다.

**강제 종료 복구:** 일반 예외는 rollback하지만 SIGKILL/전원 중단은 보장하지 않는다. 형제 경로 `.intelligence.publish.lock`가 남으면 재실행을 차단한다. 실행 중인 프로세스가 없는지 먼저 확인하고 `.intelligence.backup-*`와 `.intelligence-stage-*`를 검사한다. portal이 없으면 정상 backup을 intelligence로 복구하고 전체 검증을 실행한다. portal이 존재하면 전체 검증 및 Git diff로 정상 여부를 확인한다. 검증 전에는 commit/push하지 않는다. 원본 보존 후 잔여 lock를 제거한다. 백업과 임시 데이터는 자동으로 연구 원본 대신 사용하지 않는다.

재검증:
```bash
python -m unittest tests.test_intelligence_portal tests.test_intelligence_publish -v
python -m unittest discover -s tests -v
```

P1에서는 수집·분석·FULL 보고서 생성 및 신선도/외부 근거 관문을 연결하고, 성공한 게시 전체를 한 커밋으로 저장해야 한다. 현재 P0의 문서/HTML 검사만으로 분석 근거·프레임워크 승격의 타당성이 검증된 것으로 취급하지 않는다. 기존 신호·GCLRI·RS 및 연구 규칙은 변경하지 않았다. 저장소에서 별도 00~07 전체 헌법 원문 묶음은 확인되지 않았으며 운영 문서·레지스트리·테스트에 구현된 기준을 확인했다.
