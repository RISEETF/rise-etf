# P1 실행 연결 — 2026-10-16

## 완료와 현재 한계
- P0 PR #47 main 병합: `091a6fafc0893cccc8f7ad5220ffcd9498401283`.
- P0 Pages 배포 성공: https://github.com/RISEETF/rise-etf/actions/runs/38861858386
- 공개 OPERATIONS_V2.md HTTP 200 및 P0 문구 반영 확인.
- P1 브랜치: `feat/intelligence-daily-orchestrator`; 마지막 코드 커밋은 `git log -1 -- intelligence/P1_HANDOFF.md`로 조회.
- 기존 일일 GCLRI 수집 완료 후 기존 4개 엔진을 한 job에서 순서대로 실행. 기존 개별 엔진 workflow는 수동 복구용으로 유지하고 자동 중복 실행을 제거.
- 입력 근거 묶음, 게시 관문, 상태/실행별 영수증, 실패 artifact, 단일 커밋, Pages build 요청 연결.
- 로컬 Python 114개 테스트 PASS. 실제 데이터 복사본 실행: 4개 엔진 SUCCESS, 게시는 BLOCKED; 과거 portal 파일 모두 byte-for-byte 보존.
- 실제 차단 사유: `STALE_OR_UNAVAILABLE:DTWEXBGS`, `FULL_INPUT_PACKAGE_MISSING`.
- **완전 자동 Daily 분석·FULL 보고서 작성은 미완료.** 오늘자 보고서를 임의 생성하거나 기존 SUMMARY_ONLY를 FULL로 승격하지 않는다. P2 기관마케팅/경쟁상품 분석도 미완료.

## 자동 게시 입력 계약
`intelligence/inbox/YYYY-MM-DD/`에 다음 3개 파일을 커밋하면 실행된다.
1. `snapshot.json`: 기존 FULL 계약, `snapshot_type: FULL`, 한국 날짜 일치.
2. `report.txt`: 실제 보고서 본문. 빈 본문 불허.
3. `evidence.json`: 아래 구조. source_hashes는 해당 실행의 `data/intelligence/daily_input.json`에서 가져오며 원천이나 레지스트리가 바뀌면 재검토해야 한다.

```json
{
  "asof_date": "YYYY-MM-DD",
  "source_hashes": {"data/gclri/latest.json": "sha256", "data/signals/signal_registry.json": "sha256", "data/episodes/episode_registry.json": "sha256", "data/regime/channel_registry.json": "sha256"},
  "content_hashes": {"snapshot.json": "sha256", "report.txt": "sha256"},
  "external_evidence": [{"url": "https://primary-source/...", "observation_date": "YYYY-MM-DD", "claim": "이 근거가 뒷받침하는 주장"}],
  "revision_reason": "동일 날짜 수정일 때 이유"
}
```

근거 URL과 날짜·해시 검사는 내용의 진실성이나 분석 타당성을 자동 인증하지 않는다. 보고서 작성 단계에서 근거 검토가 필요하다. 현 단계는 모든 등록 시장계열의 CURRENT 및 원천 등록 stale_after_days를 요구하는 보수적 관문이며, 지연 계열을 맥락으로만 사용하는 선택적 발행은 아직 지원하지 않는다. 보고서 날짜는 KST, 수집/실행 시각은 UTC로 구분한다. 이전 레짐·프레임워크 또는 production 권한을 자동 승격하지 않는다.

## 실행·기록
```bash
git fetch origin
git switch feat/intelligence-daily-orchestrator
python -m unittest discover -s tests -v
python scripts/run_intelligence_daily.py
```
실제 실행은 기존 엔진 출력 및 operations 기록을 갱신한다. 검증용은 별도 checkout에서 실행한다. exit 2는 BLOCKED 또는 FAILED이며 영수증에서 구분한다. BLOCKED는 4개 계산 결과와 차단 사유를 저장하고 과거 보고서를 유지한다. 엔진 FAILED는 workflow에서 영수증만 커밋하며 부분 계산 산출물을 게시하지 않는다. runner 강제 종료/checkout 실패/push 실패의 최종 권위는 GitHub Actions다.

동시 원천 갱신으로 push가 거절되면 자동 rebase하지 않는다. 최신 main에서 다시 계산하여 입력 vintage를 재검토한다. 성공한 push 후 Pages build를 요청한다. Pages 완료 여부는 별도 배포 run을 확인한다. 원격 PR CI 및 첫 실제 실행 상태는 PR/Actions를 확인해야 한다.

## 남은 작업
1. 달러 원천 지연의 원인 확인(공식 발표 주기 vs 수집 지연), 값을 추정해 메우지 않음.
2. 외부 근거와 반론·반증을 포함한 FULL 보고서 작성 단계 연결. 기존 레짐 신뢰도 임의 복사/합성 금지.
3. ETF 마스터·수급·경쟁상품 근거를 별도 검증 후 P2에 연결.

## 첫 운영 실행과 후속 결함 수정
- P1 PR #48 병합 후 실행: https://github.com/RISEETF/rise-etf/actions/runs/38862492133
- 4개 엔진·결과 커밋(`a81e240`)·Pages 요청 성공. 보고서 BLOCKED(달러 지연/FULL 없음); workflow 최종 failure는 의도된 게시 상태 표시.
- 사후 비교에서 기존 에피소드 엔진이 동일 관측일 재실행을 새 확인으로 누적하는 결함 발견. 기존 evidence와 persistence_runs 이력은 삭제하지 않는다.
- 후속 `fix/intelligence-observation-persistence`: 동일 관측/값 재실행 시 확인을 추가하지 않고, 같은 날짜 수정으로 정상 확인 횟수를 늘리지 않는다. Gate는 evidence의 서로 다른 관측일을 계산하고 2일 이상만 persistent로 인정한다. 이전 실행 횟수는 보조 진단값이며 지속성 근거로 사용하지 않는다.
- 후속 검증: Python 117개 PASS. 실제 데이터 복사본에서 2회 실행해 episode evidence가 변하지 않음. Gate CHALLENGE 및 독립 지속 채널 1 유지: 현재 RATE-002에는 서로 다른 관측일 근거가 2개 존재한다. 동일 날짜 99회 합성 테스트에서는 독립 지속 채널로 인정하지 않는다. 과거 10월 15일 Daily와 현재 관측 vintage는 구분한다.
- 전체 역사 기간의 재보정·독립 관측 수 기반 calibration 표본수 재설계는 별도 연구 과제이며 현재 production 권한은 계속 False.
