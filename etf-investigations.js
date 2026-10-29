'use strict';
(async()=>{
 const status=document.getElementById('investigationStatus'), root=document.getElementById('investigationRows');
 const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
 const review=(item,day)=>{
  const box=node('details','');box.append(node('summary','구성내역 확인 · 기록'));
  const links=node('p','');
  const link=(label,url)=>{const a=node('a',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';links.append(a,document.createTextNode(' · '));};
  link('① 네이버 구성종목',`https://navercomp.wisereport.co.kr/v2/ETF/index.aspx?cmp_cd=${encodeURIComponent(item.ticker)}`);
  if(item.name.startsWith('RISE '))link('② RISE 운용사','https://www.riseetf.co.kr/');
  link('자료 부족 시 KRX PDF','https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201030108');
  box.append(links,node('p',`조사 기준일 ${day}. 먼저 화면의 자료 기준일·전체/상위 종목 여부·비중을 확인하세요. 자료가 부족하거나 날짜가 다르면 운용사 또는 KRX에서 보완하세요.`));
  const field=(title,control)=>{control.setAttribute('aria-label',title);const label=node('label',title+' ');label.append(control);box.append(label);return control;};
  const select=values=>{const s=node('select','');for(const [value,label] of values){const o=node('option',label);o.value=value;s.append(o);}return s;};
  const source=field('확인 출처',select([['NAVER','네이버 화면'],['ISSUER','운용사'],['KRX','KRX']]));
  const date=field('자료 기준일',node('input',''));date.type='date';
  const scope=field('확인 범위',select([['UNKNOWN','미확인'],['TOP_ONLY','상위 일부'],['FULL','전체 구성내역']]));
  const weights=field('비중 제공',node('input',''));weights.type='checkbox';
  const note=field('판단·추가 확인',node('textarea',''));note.maxLength=2000;note.rows=3;
  const save=node('button','이 브라우저에 기록'),message=node('p','');save.type='button';message.setAttribute('role','status');
  box.append(node('p','개인 검토 메모만 이 브라우저에 저장합니다. 원천 구성종목 표를 자동 수집하거나 서버로 전송하지 않습니다. 메모는 공식 PDF 검증 상태를 변경하지 않습니다.'),save,message);
  const key=`rise-holdings-review-v1:${item.ticker}:${day}`;
  const describe=r=>`개인 검토 기록 · ${r.date} 기준 · ${r.scope==='FULL'?'전체':r.scope==='TOP_ONLY'?'상위 일부':'범위 미확인'} · ${r.weights?'비중 제공':'비중 없음: 기여도 계산 보류'}${r.date!==day?' · 조사일과 자료 기준일 다름':''} · 원인 확정 아님`;
  try{const r=JSON.parse(localStorage.getItem(key));if(r&&['NAVER','ISSUER','KRX'].includes(r.source)&&['UNKNOWN','TOP_ONLY','FULL'].includes(r.scope)&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&typeof r.weights==='boolean'&&typeof r.note==='string'){source.value=r.source;date.value=r.date;scope.value=r.scope;weights.checked=r.weights;note.value=r.note.slice(0,2000);message.textContent=describe(r);}}catch{message.textContent='저장한 검토 기록을 읽을 수 없습니다.';}
  save.addEventListener('click',()=>{if(!date.value||date.value>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Seoul'})){message.textContent='유효한 과거 또는 오늘의 자료 기준일을 입력하세요.';return;}const r={source:source.value,date:date.value,scope:scope.value,weights:weights.checked,note:note.value,recorded_at:new Date().toISOString()};try{localStorage.setItem(key,JSON.stringify(r));message.textContent=describe(r);}catch{message.textContent='브라우저 저장에 실패했습니다. 메모를 별도로 보관하세요.';}});
  return box;
 };
 try{
  const r=await fetch('data/etf_investigations/latest.json',{cache:'no-store'});if(!r.ok)throw Error('목록 미확보');
  const d=await r.json();if(d.schema!=='ETF_INVESTIGATION_QUEUE_V1'||!Array.isArray(d.items)||d.items.length>5||!/^\d{4}-\d{2}-\d{2}$/.test(d.observation_date))throw Error('목록 형식 오류');
  status.textContent=`${d.observation_date} 관측 기준 · ${d.screened_count}종목 확인 · 조사 후보 ${d.candidate_count}개 중 ${d.items.length}개 표시 · 미보정 연구 기준`;
  const table=node('table',''),head=node('tr','');['ETF','탐지 근거','진행 상태'].forEach(t=>head.append(node('th',t)));table.append(head);
  const labels={PRICE_MOVE:'가격 변동',NAV_GAP:'NAV 괴리',VOLUME_SPIKE:'20관측일 평균 대비 거래량'};
  let receipts=[];
  try{const f=await fetch('data/etf_investigations/pdf_receipts.json',{cache:'no-store'});if(f.ok){const p=await f.json();if(p.schema!=='KRX_PDF_RECEIPTS_V1'||!Array.isArray(p.items))throw Error();receipts=p.items;}else if(f.status!==404)throw Error();}catch{status.textContent+=' · PDF 확보 상태 조회 실패';}
  for(const item of d.items){if(!/^[0-9A-Z]{6}$/.test(item.ticker)||typeof item.name!=='string'||item.state!=='PDF_PENDING'||item.holdings_verified!==false||!Array.isArray(item.signals))throw Error('조사 상태 오류');const row=node('tr','');const pdf=receipts.find(p=>p.ticker===item.ticker&&p.observation_date===d.observation_date&&p.source==='KRX_PDF'&&['PDF_ACQUIRED','PDF_ACQUIRED_PARTIAL'].includes(p.state)&&p.attribution_verified===false&&Number.isInteger(p.row_count)&&p.row_count>0);const detail=pdf?`${pdf.observation_date} PDF 확보 · ${pdf.row_count}행 · ${pdf.limitation}`:'화면 확인 우선 · 공식 PDF 미확보';const state=node('td',detail);state.append(review(item,d.observation_date));row.append(node('td',`${item.name} (${item.ticker})`),node('td',item.signals.map(s=>`${labels[s.kind]||s.kind} ${s.value}${s.unit}`).join(' · ')),state);table.append(row);}
  if(d.items.length)root.append(table);else root.append(node('p','이번 관측일의 기준 초과 후보 없음.'));
  root.append(node('p',`가격 비교 가능 ${d.metric_coverage.price}개 · NAV 비교 가능 ${d.metric_coverage.nav_gap}개 · 20일 거래량 비교 가능 ${d.metric_coverage.volume}개. 이력 부족은 정상 판정이 아닙니다.`));
  const [attempt,collection]=await Promise.all(['data/etf_investigations/status.json','data/krx_collection_status.json'].map(async url=>{const x=await fetch(url,{cache:'no-store'});if(!x.ok)throw Error('실행 상태 미확인');return x.json();}));
  if(attempt.status!=='SUCCESS'||collection.status!=='SUCCESS')status.textContent+=' · 최근 수집/선별 실패: 마지막 정상 목록 표시';
 }catch(e){status.textContent+=` · ${e.message}. 최신 갱신 여부를 확인할 수 없습니다.`;}
})();
