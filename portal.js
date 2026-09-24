'use strict';
const el = id => document.getElementById(id);
let products = [];
async function readJSON(path) {
  const response = await fetch(path, {cache: 'no-store'});
  if (!response.ok) throw new Error(`자료를 읽을 수 없습니다 (${response.status})`);
  return response.json();
}
function validDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}
function validateMaster(data) {
  if (data.status !== 'OFFICIAL_IDENTITY_MASTER' || !validDate(data.effective_date) ||
      !Number.isFinite(Date.parse(data.retrieved_at)) || !Array.isArray(data.products) ||
      !data.products.length || data.products.length !== data.instrument_count) throw new Error('공식 마스터 형식 또는 기준일 오류');
  const codes = new Set();
  for (const row of data.products) {
    if (!/^[0-9A-Z]{6}$/.test(row.code) || codes.has(row.code) ||
        typeof row.name !== 'string' || !row.name.startsWith('RISE ') || !validDate(row.listed_on) ||
        !/^https:\/\/(?:riseetf\.co\.kr\/prod\/finderDetail|kbam\.co\.kr\/products)\/[a-zA-Z0-9]+$/.test(row.detail_url)) throw new Error('종목 식별 정보 오류');
    codes.add(row.code);
  }
  const pending=data.pending_products || [];
  const details=new Set(data.products.map(r=>r.detail_id));
  if(!Array.isArray(pending) || (data.source_product_count ?? data.instrument_count)!==data.instrument_count+pending.length) throw new Error('공식 상품 수량 오류');
  for(const row of pending) {
    if(row.code!==null || row.identity_status!=='OFFICIAL_CODE_PENDING' || typeof row.name!=='string' || !row.name.startsWith('RISE ') || !validDate(row.listed_on) || details.has(row.detail_id) || !/^https:\/\/kbam\.co\.kr\/products\/[a-zA-Z0-9]+$/.test(row.detail_url)) throw new Error('대기 상품 식별 정보 오류');
    details.add(row.detail_id);
  }
  return data;
}
function localTime(value) {
  return Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('ko-KR', {timeZone:'Asia/Seoul', hour12:false}) + ' KST' : '시각 미확인';
}
function renderProducts() {
  const query = el('search').value.trim().toLocaleLowerCase();
  const category = el('category').value;
  const selected = products.filter(row => (!category || row.primary_category === category) &&
    `${row.code} ${row.name}`.toLocaleLowerCase().includes(query));
  const body = el('products'); body.replaceChildren();
  for (const row of selected) {
    const tr = document.createElement('tr');
    for (const value of [row.code || '공식 코드 확인 중', row.name, row.primary_category || '미분류', row.listed_on]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    const td = document.createElement('td'), link = document.createElement('a');
    link.href = row.detail_url; link.textContent = '공식 상세 ↗'; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.setAttribute('aria-label', `${row.name} 공식 상세`); td.append(link); tr.append(td); body.append(tr);
  }
  el('resultCount').textContent = `전체 ${products.length}종목 중 ${selected.length}종목 표시`;
  el('empty').hidden = selected.length !== 0;
}
async function loadMaster() {
  try {
    const data = validateMaster(await readJSON('data/master/latest.json'));
    products = [...data.products,...(data.pending_products || [])];
    el('total').textContent = products.length.toLocaleString('ko-KR');
    el('identityCounts').textContent=`종목코드 확인 ${data.instrument_count}개 · 공식 코드 대기 ${data.pending_products?.length || 0}개`;
    el('effective').textContent = data.effective_date;
    el('retrieved').textContent = `수집 ${localTime(data.retrieved_at)}`;
    const age = Math.floor((Date.now() - Date.parse(data.retrieved_at)) / 86400000);
    el('masterStatus').textContent = `공식 종목 식별 자료 · ${data.effective_date} 기준 · ${age >= 0 ? `수집 후 ${age}일 경과` : '수집 시각 확인 필요'}. 현재 상장 목록과 다를 수 있습니다. 가격·투자 신호는 검증 전입니다.`;
    for (const value of [...new Set(products.map(row => row.primary_category).filter(Boolean))].sort()) {
      const option = document.createElement('option'); option.value = value; option.textContent = value; el('category').append(option);
    }
    for (const id of ['search','category','reset']) el(id).disabled = false;
    renderProducts();
    loadKrxComparison(data);
    await loadMasterChanges(data);
  } catch (error) {
    products = []; el('products').replaceChildren();
    el('krxStatus').textContent='운용사 목록을 확인할 수 없어 KRX 대조를 표시하지 않습니다.';
    el('kindStatus').textContent='공시 수집 결과를 불러오지 못했습니다.';
    el('masterStatus').textContent = `공식 마스터를 표시할 수 없습니다. ${error.message}.`;
    el('resultCount').textContent = '자료 없음 · 기존 자료로 대체하지 않습니다.';
  }
}
async function loadKrxComparison(master) {
  let kindLoaded=false;
  const labels={MATCHED_CODE_NAME:'코드·명칭 일치',NAME_DIFFERENCE:'코드 일치·명칭 확인 필요',
    CODE_PENDING_NAME_CANDIDATE:'명칭 일치 코드 후보',IDENTITY_REVIEW_REQUIRED:'식별 검토 필요',
    LISTED_AFTER_KRX_DATE:'상장일이 KRX 관측일 이후',NOT_OBSERVED:'KRX 관측 없음 · 폐지 확정 아님',
    NO_NAME_CANDIDATE:'코드 후보 미확인'};
  try {
    const report=await readJSON('data/quality/krx_master_reconciliation.json');
    renderKindNotices(report.lifecycle_notices);
    kindLoaded=true;
    if(report.status!=='KRX_DAILY_IDENTITY_COMPARISON' || !validDate(report.observed_on) || !validDate(report.issuer_effective_date) ||
       !Number.isFinite(Date.parse(report.retrieved_at)) || !Array.isArray(report.rows) || !Array.isArray(report.krx_rise_without_confirmed_issuer_code)) throw new Error('대조 형식 오류');
    const expected=[...master.products,...(master.pending_products || [])].map(p=>[p.detail_id,p.code,p.name,p.listed_on]).sort((a,b)=>a[0].localeCompare(b[0]));
    const actual=report.rows.map(p=>[p.detail_id,p.issuer_code,p.issuer_name,p.issuer_listed_on]).sort((a,b)=>a[0].localeCompare(b[0]));
    if(JSON.stringify(expected)!==JSON.stringify(actual) || report.issuer_product_count!==expected.length) throw new Error('현재 운용사 목록과 달라 재대조 대기');
    const counts={};
    for(const row of report.rows) {
      if(!labels[row.status] || !Array.isArray(row.candidate_codes)) throw new Error('판정 오류');
      counts[row.status]=(counts[row.status] || 0)+1;
    }
    if(Object.keys(report.counts || {}).length!==Object.keys(counts).length || Object.entries(counts).some(([key,n])=>report.counts[key]!==n)) throw new Error('대조 집계 오류');
    const age=Math.floor((Date.now()-Date.parse(report.retrieved_at))/86400000);
    const observationLag=Math.floor((Date.now()-Date.parse(report.observed_on))/86400000);
    el('krxStatus').textContent=`KRX 기준 ${report.issuer_product_count}개 상품 대조 · 코드·명칭 일치 ${counts.MATCHED_CODE_NAME || 0}개${age>2 || observationLag>4?' · 자료 지연 확인 필요':''}`;
    el('krxDates').textContent=`거래소 관측일 ${report.observed_on} · 대조 당시 운용사 기준일 ${report.issuer_effective_date} · KRX 수집 ${localTime(report.retrieved_at)}`;
    el('krxCounts').replaceChildren(); el('krxIssues').replaceChildren();
    for(const [key,n] of Object.entries(counts)) {
      const item=document.createElement('p');item.textContent=`${labels[key]} ${n}개`;el('krxCounts').append(item);
    }
    for(const row of report.rows.filter(r=>r.status!=='MATCHED_CODE_NAME')) {
      const item=document.createElement('li');item.textContent=`${row.issuer_name}: ${labels[row.status]}${row.krx_code?` · KRX ${row.krx_code} ${row.krx_name}`:''}${row.candidate_codes.length?` · 후보 ${row.candidate_codes.join(', ')}`:''}`;el('krxIssues').append(item);
    }
    for(const row of report.krx_rise_without_confirmed_issuer_code) {
      const item=document.createElement('li');item.textContent=`KRX ${row.code} ${row.name}: 운용사 확정 코드와 미연결 · 신규 상장 확정 아님`;el('krxIssues').append(item);
    }
  } catch(error) {
    el('krxCounts').replaceChildren();el('krxIssues').replaceChildren();el('krxDates').textContent='';
    el('krxStatus').textContent=`KRX 대조 결과 확인 대기 · ${error.message}`;
    if(!kindLoaded)renderKindNotices(null);
  }
  try {
    const attempt=await readJSON('data/krx_collection_status.json');
    if(!['SUCCESS','FAILED'].includes(attempt.status)) throw new Error('상태 오류');
    el('krxAttempt').textContent=`최근 KRX 대조 시도 ${localTime(attempt.attempted_at)} · ${attempt.status==='SUCCESS'?'성공':'실패 · 마지막 성공 대조 유지'}`;
  } catch(_) {el('krxAttempt').textContent='KRX 최근 시도 이력 확인 대기';}
}
function renderKindNotices(data) {
  const kinds={LISTING_NOTICE:'신규상장 공시',DELISTING_NOTICE:'상장폐지 공시',DELISTING_REVIEW:'폐지 관련 검토',REVISION_REVIEW:'정정·철회 검토'};
  const states={NOTICE_CODE_DATE_VERIFIED:'본문 코드·날짜 확인',BODY_IDENTITY_REVIEW:'본문 식별 검토',NOTICE_REVIEW_REQUIRED:'공시 검토 필요',EFFECTIVE_DATE_REVIEW:'효력일 확인 필요',DOCUMENT_HISTORY_REVIEW:'문서 이력 검토'};
  el('kindRows').replaceChildren();el('kindWindow').textContent='';
  try {
    if(!data || !['SUCCESS','FAILED'].includes(data.status) || !Array.isArray(data.events)) throw new Error('수집 결과 대기');
    const rows=document.createDocumentFragment();
    for(const event of data.events.slice(0,50)) {
      if(!kinds[event.kind] || !states[event.verification] || !/^[0-9A-Z]{6}$/.test(event.code) ||
         !/^\d{14}$/.test(event.receipt_id) || event.viewer_url!==`https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=${event.receipt_id}` ||
         (event.effective_date!==null && !validDate(event.effective_date)) ||
         (event.verification==='NOTICE_CODE_DATE_VERIFIED' && !event.effective_date)) throw new Error('공시 형식 확인 필요');
      const row=document.createElement('tr');
      for(const value of [`${event.name} (${event.code})`,kinds[event.kind],localTime(event.published_at),event.effective_date || '미확인',`${states[event.verification]}${event.in_latest_search===false?' · 이번 검색에 없음':''} · 확인 ${localTime(event.last_checked_at)}`]) {
        const td=document.createElement('td');td.textContent=value;row.append(td);
      }
      const td=document.createElement('td'),link=document.createElement('a');link.href=event.viewer_url;link.textContent='KIND 원문 ↗';link.target='_blank';link.rel='noopener noreferrer';td.append(link);row.append(td);rows.append(row);
    }
    el('kindRows').append(rows);
    el('kindStatus').textContent=`KIND 수집 ${data.status==='SUCCESS'?'성공':'실패 · 마지막 성공 공시 유지'} · 누적 ${data.events.length}건 · 최근 ${Math.min(data.events.length,50)}건 표시 · 최근 시도 ${localTime(data.attempted_at)}`;
    if(data.window_start && data.window_end)el('kindWindow').textContent=`마지막 성공 검색 구간 ${data.window_start}~${data.window_end} · 본문 미지원·정정 공시는 검토 필요로 표시합니다.`;
  } catch(error) {el('kindRows').replaceChildren();el('kindStatus').textContent=`KIND 공시 확인 대기 · ${error.message}`;}
}
async function loadMasterChanges(master) {
  try {
    const changes=await readJSON('data/master/changes.json');
    if(changes.source_sha256!==master.source_sha256 || changes.instrument_count!==master.instrument_count || !Array.isArray(changes.events)) throw new Error('변동 내역 기준 불일치');
    el('masterChanges').replaceChildren();
    const labels={ADDED_TO_OFFICIAL_LIST:'공식 목록 추가',REMOVED_FROM_OFFICIAL_LIST:'공식 목록 제외 · 상장폐지 확정 아님',NAME_CHANGED:'명칭 변경',CODE_UPDATED:'공식 코드 갱신'};
    const events=[...changes.events].reverse().slice(0,20);
    el('masterChangesStatus').textContent=events.length?`저장된 변동 ${changes.events.length}건 · 최근 ${events.length}건 표시`:'비교 이력에서 종목 추가·제외·명칭 변경이 없습니다.';
    for(const item of events) {
      if(!labels[item.kind]) continue;
      const li=document.createElement('li');
      li.textContent=`${labels[item.kind]}: ${item.name} (${item.code || '공식 코드 확인 중'})${item.listed_on?` · 공식 상장일 ${item.listed_on}`:''}${item.previous_name?` · 이전 ${item.previous_name}`:''} · 발견 ${localTime(item.detected_at)}`;
      el('masterChanges').append(li);
    }
  } catch (_) {
    el('masterChanges').replaceChildren();el('masterChangesStatus').textContent='현재 목록과 일치하는 변동 이력을 불러오지 못했습니다.';
  }
}
async function loadCapture() {
  try {
    const data = await readJSON('data/collection_status.json');
    el('captureState').textContent = data.status === 'FAILED' ? '최근 수집 실패' : data.status === 'CAPTURED_UNVERIFIED' ? '수집됨 · 검증 대기' : '상태 확인 필요';
    el('captureTime').textContent = `최근 시도 ${localTime(data.retrieved_at)} · 시장 기준일 ${data.observation_date || '미확인'}`;
  } catch (_) { el('captureState').textContent = '상태 자료 없음'; el('captureTime').textContent = '수집 상태를 불러오지 못했습니다.'; }
}
async function loadMasterAttempt() {
  try {
    const data = await readJSON('data/master_collection_status.json');
    const label = data.status === 'SUCCESS' ? '성공' : data.status === 'FAILED' ? '실패 · 마지막 성공 자료 유지' : '상태 확인 필요';
    el('masterAttempt').textContent = `최근 마스터 수집 시도 ${localTime(data.attempted_at)} · ${label}`;
  } catch (_) { el('masterAttempt').textContent = '마스터 수집 시도 이력이 없습니다.'; }
}
async function loadQuality() {
  try {
    const data = await readJSON('data/quality/official_master_reconciliation.json');
    const labels = {IDENTITY_MATCH:'코드·명칭 일치', OFFICIAL_NAME_MISMATCH:'명칭 불일치', NOT_IN_OFFICIAL_CURRENT_MASTER:'공식 수집본에 코드 없음'};
    if (!validDate(data.official_effective_date) || !Number.isInteger(data.legacy_count) || data.legacy_count <= 0 ||
        Object.keys(labels).some(key => !Number.isInteger(data.counts?.[key]) || data.counts[key] < 0) ||
        Object.keys(labels).reduce((sum,key)=>sum+data.counts[key],0) !== data.legacy_count) throw new Error('대조 집계 오류');
    el('qualityStatus').textContent = `${data.official_effective_date} 공식 목록과 기존 ${data.legacy_count}개 행 대조`;
    for (const [key,label] of Object.entries(labels)) {
      const box=document.createElement('div'), value=document.createElement('strong'), text=document.createElement('span');
      value.textContent=data.counts[key]; text.textContent=label; box.append(value,text); el('qualityCounts').append(box);
    }
  } catch (_) { el('qualityStatus').textContent = '대조 보고서를 표시할 수 없습니다.'; }
}
el('search').addEventListener('input', renderProducts);
async function loadSeries() {
  try {
    const data = await readJSON('data/series/status.json');
    if (!Array.isArray(data.series) || data.rs_status !== 'BLOCKED' || data.ranking !== null ||
        data.series.some(row => row.rs_eligible !== false || !Number.isInteger(row.observations) || row.observations < 0)) throw new Error('시계열 검증 상태 오류');
    el('seriesStatus').textContent = `가격·환율 수집 이력 ${data.capture_count}건 · RS 계산 보류 · 집계 ${localTime(data.built_at)}`;
    for (const row of data.series) {
      const tr=document.createElement('tr');
      const state=row.last_attempt_status==='CAPTURED' ? '수집됨 · 검증 대기' : row.last_attempt_status==='FAILED' ? '실패' : '미수집';
      const audit=row.adjustment_audit;
      const adjustment=audit ? `제공처 수정종가 · 현금분배 ${audit.cash_event_count}건 / 분할 ${audit.split_count}건 · 독립 검증 대기` : '배당·분할 조정 미확인';
      for (const value of [`${row.name} (${row.currency || '통화 미확인'})`, row.observations, row.first_date && row.last_date ? `${row.first_date} ~ ${row.last_date}` : '자료 없음', `${state} / ${localTime(row.retrieved_at)}`, adjustment, '보류']) {
        const td=document.createElement('td');td.textContent=value;tr.append(td);
      }
      el('seriesRows').append(tr);
    }
    const fx=data.fx;
    el('fxCoverage').textContent=`원/달러 참고환율: ${fx.observations}개 관측일 · ${fx.first_date || '—'} ~ ${fx.last_date || '—'} · 최근 시도 ${fx.last_attempt_status==='CAPTURED' ? '수집 성공' : '수집 실패 또는 미수집'} (${localTime(fx.retrieved_at)})`;
  } catch (_) {
    el('seriesRows').replaceChildren();el('seriesStatus').textContent='시계열 현황을 표시할 수 없습니다. RS 계산은 보류합니다.';
  }
}
el('category').addEventListener('change', renderProducts);
async function loadIssuerChecks() {
  try {
    const data=await readJSON('data/quality/apple_issuer_validation.json');
    if(data.status!=='PARTIAL_ISSUER_RECONCILIATION' || data.rs_eligible!==false || !validDate(data.issuer_accessed_date)) throw new Error('검증 범위 오류');
    for(const key of ['current_cash','historical_cash']) {
      const group=data[key];
      if(!Array.isArray(group.checks) || group.matched_amount_count!==group.checks.filter(row=>row.status==='AMOUNT_MATCH_ONLY').length || group.checks.some(row=>row.ex_date_verified!==false)) throw new Error('배당 대조 집계 오류');
    }
    el('issuerStatus').textContent=`공식 배당금액 대조: 최근 구간 ${data.current_cash.matched_amount_count}건 / 2020년 검증 구간 ${data.historical_cash.matched_amount_count}건 일치 · 배당락일 확인 대기`;
    const split=data.historical_split;
    el('issuerSplit').textContent=split.status==='SPLIT_EVENT_DATE_AND_RATIO_MATCH' ? `${split.first_trading_date} 분할조정 거래 시작일·${split.ratio}:1 비율 일치. 제공처 가격에 분할을 다시 적용하지 않습니다.` : '실제 분할 사례: 불일치 또는 추가 확인 필요';
    el('issuerScope').textContent=`공식 사실 확인일 ${data.issuer_accessed_date} · 최근 대조 구간 ${data.current_window.first_date} ~ ${data.current_window.last_date} · 2020년 자료는 검증 사례로만 보관하며 현재 적재 기간에 합산하지 않습니다.`;
  } catch (_) {
    el('issuerStatus').textContent='발행사 대조 결과를 표시할 수 없습니다. 검증 완료로 간주하지 않습니다.';
    el('issuerSplit').textContent='';el('issuerScope').textContent='';
  }
}
el('reset').addEventListener('click', () => {el('search').value='';el('category').value='';renderProducts();});
async function loadUniverse() {
  try {
    const data=await readJSON('data/universe/status.json');
    if(data.status!=='CANDIDATE_GROUPS_ONLY' || data.rs_status!=='BLOCKED' || data.ranking!==null || data.selected_count!==0 || !Array.isArray(data.groups)) throw new Error('후보 상태 오류');
    const seen=new Set();
    for(const group of data.groups) {
      if(group.selected_instrument_id!==null || group.overview_votes!==0 || !Array.isArray(group.candidates) || !['MARKET','SECTOR','COMPANY','THEME'].includes(group.scope)) throw new Error('선정 상태 오류');
      const groupSeen=new Set();
      for(const candidate of group.candidates) {
        if(candidate.rs_eligible!==false || groupSeen.has(candidate.instrument_id)) throw new Error('그룹 내 중복 후보');
        groupSeen.add(candidate.instrument_id);
        seen.add(candidate.instrument_id);
      }
    }
    if(seen.size!==data.candidate_count) throw new Error('후보 집계 오류');
    el('universeStatus').textContent=`고유 후보 ${data.candidate_count}개 · 노출 설계 ${data.groups.length}개 · 후보 미확보 ${data.gap_group_count}개 · 대표자산 확정 0개 · RS 보류`;
    for(const group of data.groups) {
      const tr=document.createElement('tr');
      for(const value of [group.label,group.scope==='COMPANY'?'기업 관찰':group.scope==='THEME'?'테마 탐색':group.scope==='SECTOR'?'섹터 비교':'시장 비교',group.candidates.map(c=>`${c.name} (${c.currency})`).join(' / ') || '관측수단 조사 필요',group.selection_status==='DATA_GAP'?'후보·데이터 미확보':'노출 관계·근거 검토 중']) {
        const td=document.createElement('td');td.textContent=value;tr.append(td);
      }
      el('universeRows').append(tr);
      for(const candidate of group.candidates) {
        for(const evidence of candidate.issuer_evidence || []) {
          const note=document.createElement('p');note.className='muted';
          note.textContent=`${candidate.instrument_id}: ${evidence.summary_ko} 공식 자료 조회 ${evidence.accessed_date} · 부분 확인, 대표 선정 미완료`;
          try {
            const url=new URL(evidence.source_url);
            if(url.protocol==='https:' && !url.username && !url.password && ['riseetf.co.kr','www.ssga.com','www.ishares.com'].includes(url.hostname)) {
              const link=document.createElement('a');
              link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';
              link.textContent='공식 근거 원문';
              note.append(' · ',link);
            }
          } catch (_) { /* Keep the evidence text when its source URL is invalid. */ }
          tr.lastChild.append(note);
        }
      }
    }
  } catch (_) {
    el('universeRows').replaceChildren();el('universeStatus').textContent='후보 자료를 표시할 수 없습니다. 대표 선정·RS 계산은 보류합니다.';
  }
}
async function loadResearchRS() {
  try {
    const data=await readJSON('data/research/rs.json');
    if(data.status!=='EXPLORATORY_PRICE_RS' || data.production_eligible!==false || data.fx_basis!=='ECB_REFERENCE_NOT_CLOSE' || !Array.isArray(data.windows)) throw new Error('연구용 RS 형식 오류');
    const selector=el('researchHorizon');
    const basisSelector=el('researchBasis');
    const pct=value=>`${value>=0?'+':''}${value.toFixed(2)}%`;
    const sources=el('researchSources');sources.replaceChildren();
    for(const source of data.sources || []) {
      const li=document.createElement('li');
      li.textContent=`${source.name}: 최근 가격 ${source.latest_price_date || '없음'} · 수집 ${localTime(source.capture?.retrieved_at)}`;
      sources.append(li);
    }
    const fxLine=document.createElement('li');
    fxLine.textContent=`ECB 기준환율 수집 ${localTime(data.fx_capture?.retrieved_at)} · 종가 환율 아님`;
    sources.append(fxLine);
    const render=()=>{
      el('researchRows').replaceChildren();
      el('researchSummary').textContent='';
      const basis=basisSelector.value;
      if(!['krw','local'].includes(basis)) throw new Error('통화 기준 오류');
      const label=basis==='krw'?'원화':'현지통화';
      el('researchRankHeading').textContent=`${label} 순위`;
      el('researchRSHeading').textContent=`SPY 대비 RS · ${label}`;
      const w=data.windows.find(item=>item.calendar_days===Number(selector.value));
      const todayKST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
      const age=validDate(data.latest_common_date) ? Math.floor((Date.parse(todayKST)-Date.parse(data.latest_common_date))/86400000) : null;
      if(age!==null && age<0) throw new Error('미래 관측일');
      el('researchFreshness').hidden=age===null || age<7;
      el('researchFreshness').textContent=age!==null && age>=7 ? `공통 관측일이 한국 날짜 기준 ${age}일 전입니다. 과거 비교값이며 오늘 시장 상황으로 해석하지 마세요. 7일은 달력일 기준 안내로, 휴장일·수집 장애 판정은 아닙니다.` : '';
      el('researchDates').textContent=`계산 시각 ${localTime(data.decision_time_utc)} · 공통 가격·환율 관측일 ${data.latest_common_date || '없음'}${age!==null?` · 오늘 기준 ${age}일 전`:''}`;
      if(!w || w.status!=='CALCULATED_RESEARCH_ONLY') {
        el('researchStatus').textContent=w?.status==='KNOWN_SPLIT_IN_WINDOW'?'구간 내 주식분할이 있어 종가 비교를 보류합니다.':'공통 가격·환율 기간이 부족해 계산하지 못했습니다.';
        return;
      }
      if(!validDate(w.start_date) || !validDate(w.end_date) || !Array.isArray(w.rows) || w.rows.some(r=>['krw_rank','local_rank','local_return_pct','krw_return_pct','fx_return_pct','krw_rs_vs_spy_pct','local_rs_vs_spy_pct'].some(k=>!Number.isFinite(r[k])))) throw new Error('계산값 오류');
      el('researchStatus').textContent=`연구용 ${w.rows.length}종목 · ${w.start_date} → ${w.end_date} (${w.actual_calendar_days}일) · ECB 기준환율`;
      const rows=[...w.rows].sort((a,b)=>a[basis+'_rank']-b[basis+'_rank'] || a.instrument_id.localeCompare(b.instrument_id));
      const positive=rows.filter(r=>r[basis+'_return_pct']>0).length;
      const changed=rows.filter(r=>r.krw_rank!==r.local_rank).length;
      el('researchSummary').textContent=`이 시범 풀의 ${label} 수익률 양수 ${positive}/${rows.length}종목 · 통화 기준에 따라 순위가 다른 종목 ${changed}개 (시간에 따른 순위 변화 아님)`;
      for(const row of rows) {
        const tr=document.createElement('tr');
        tr.dataset.instrument=row.instrument_id;
        const delta=row.krw_return_pct-row.local_return_pct;
        for(const value of [row[basis+'_rank'],`${row.name} (${row.currency})`,pct(row.local_return_pct),pct(row.krw_return_pct),row.currency==='KRW'?'별도 환산 없음':pct(row.fx_return_pct),row.currency==='KRW'?'별도 환산 없음':`${delta>=0?'+':''}${delta.toFixed(2)}%p`,pct(row[basis+'_rs_vs_spy_pct']),`${row.local_rank} → ${row.krw_rank}`]) {
          const td=document.createElement('td');td.textContent=value;tr.append(td);
        }
        el('researchRows').append(tr);
      }
    };
    const safeRender=()=>{try{render();}catch(_){el('researchRows').replaceChildren();el('researchSummary').textContent='';el('researchStatus').textContent='연구용 계산값을 표시할 수 없습니다.';}};
    selector.disabled=false;basisSelector.disabled=false;
    selector.addEventListener('change',safeRender);basisSelector.addEventListener('change',safeRender);safeRender();
  } catch (_) {
    el('researchRows').replaceChildren();el('researchStatus').textContent='연구용 RS 자료를 표시할 수 없습니다.';
  }
}
Promise.allSettled([loadMaster(), loadCapture(), loadQuality(), loadMasterAttempt(), loadSeries(), loadIssuerChecks(), loadUniverse(), loadResearchRS()]);
