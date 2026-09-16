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
        !/^https:\/\/riseetf\.co\.kr\/prod\/finderDetail\/[a-zA-Z0-9]+$/.test(row.detail_url)) throw new Error('종목 식별 정보 오류');
    codes.add(row.code);
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
    for (const value of [row.code, row.name, row.primary_category || '미분류', row.listed_on]) {
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
    products = data.products;
    el('total').textContent = data.instrument_count.toLocaleString('ko-KR');
    el('effective').textContent = data.effective_date;
    el('retrieved').textContent = `수집 ${localTime(data.retrieved_at)}`;
    const age = Math.floor((Date.now() - Date.parse(data.retrieved_at)) / 86400000);
    el('masterStatus').textContent = `공식 종목 식별 자료 · ${data.effective_date} 기준 · ${age >= 0 ? `수집 후 ${age}일 경과` : '수집 시각 확인 필요'}. 현재 상장 목록과 다를 수 있습니다. 가격·투자 신호는 검증 전입니다.`;
    for (const value of [...new Set(products.map(row => row.primary_category).filter(Boolean))].sort()) {
      const option = document.createElement('option'); option.value = value; option.textContent = value; el('category').append(option);
    }
    for (const id of ['search','category','reset']) el(id).disabled = false;
    renderProducts();
  } catch (error) {
    products = []; el('products').replaceChildren();
    el('masterStatus').textContent = `공식 마스터를 표시할 수 없습니다. ${error.message}.`;
    el('resultCount').textContent = '자료 없음 · 기존 자료로 대체하지 않습니다.';
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
Promise.allSettled([loadMaster(), loadCapture(), loadQuality(), loadMasterAttempt(), loadSeries(), loadIssuerChecks()]);
