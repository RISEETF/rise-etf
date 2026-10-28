'use strict';
(async()=>{
 const status=document.getElementById('investigationStatus'), root=document.getElementById('investigationRows');
 const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
 try{
  const r=await fetch('data/etf_investigations/latest.json',{cache:'no-store'});if(!r.ok)throw Error('목록 미확보');
  const d=await r.json();if(d.schema!=='ETF_INVESTIGATION_QUEUE_V1'||!Array.isArray(d.items)||d.items.length>5||!/^\d{4}-\d{2}-\d{2}$/.test(d.observation_date))throw Error('목록 형식 오류');
  status.textContent=`${d.observation_date} 관측 기준 · ${d.screened_count}종목 확인 · 조사 후보 ${d.candidate_count}개 중 ${d.items.length}개 표시 · 미보정 연구 기준`;
  const table=node('table',''),head=node('tr','');['ETF','탐지 근거','진행 상태'].forEach(t=>head.append(node('th',t)));table.append(head);
  const labels={PRICE_MOVE:'가격 변동',NAV_GAP:'NAV 괴리',VOLUME_SPIKE:'20관측일 평균 대비 거래량'};
  for(const item of d.items){if(item.state!=='PDF_PENDING'||item.holdings_verified!==false||!Array.isArray(item.signals))throw Error('조사 상태 오류');const row=node('tr','');row.append(node('td',`${item.name} (${item.ticker})`),node('td',item.signals.map(s=>`${labels[s.kind]||s.kind} ${s.value}${s.unit}`).join(' · ')),node('td','PDF 확보 대기'));table.append(row);}
  if(d.items.length)root.append(table);else root.append(node('p','이번 관측일의 기준 초과 후보 없음.'));
  root.append(node('p',`가격 비교 가능 ${d.metric_coverage.price}개 · NAV 비교 가능 ${d.metric_coverage.nav_gap}개 · 20일 거래량 비교 가능 ${d.metric_coverage.volume}개. 이력 부족은 정상 판정이 아닙니다.`));
  const [attempt,collection]=await Promise.all(['data/etf_investigations/status.json','data/krx_collection_status.json'].map(async url=>{const x=await fetch(url,{cache:'no-store'});if(!x.ok)throw Error('실행 상태 미확인');return x.json();}));
  if(attempt.status!=='SUCCESS'||collection.status!=='SUCCESS')status.textContent+=' · 최근 수집/선별 실패: 마지막 정상 목록 표시';
 }catch(e){status.textContent+=` · ${e.message}. 최신 갱신 여부를 확인할 수 없습니다.`;}
})();
