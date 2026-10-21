'use strict';
const $=id=>document.getElementById(id),selected=new Set();let inventory=null,provider=null,us=null,page=0,current=[];
const date=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v;
const finite=v=>v===null||(typeof v==='number'&&Number.isFinite(v));
function requireValid(ok){if(!ok)throw Error('파일 형식 또는 값 검증 실패');}
function validate(d){
 if(d?.schema==='RISE_PRIVATE_PROVIDER_V1'){
  requireValid(d.metadata?.source==='funetf'&&d.metadata.market==='KR'&&Number.isFinite(Date.parse(d.metadata.retrieved_at_utc))&&(!d.metadata.observation_date||date(d.metadata.observation_date))&&(!d.metadata.screen_date||date(d.metadata.screen_date))&&Array.isArray(d.records)&&d.records.length>0&&d.records.length<=100000);
  const seen=new Set();for(const r of d.records){requireValid(/^[0-9A-Z]{6}$/.test(r.code)&&!seen.has(r.code)&&typeof r.name==='string'&&typeof r.category==='string'&&typeof r.provider==='string'&&r.metrics&&Object.values(r.metrics).every(finite)&&Array.isArray(r.holdings_top3)&&r.holdings_top3.length===3);for(const h of r.holdings_top3)requireValid((h.name===null||typeof h.name==='string')&&finite(h.weight_pct));seen.add(r.code);}return 'KR';
 }
 requireValid(d?.scope==='ETF_FLAGGED_DIRECTORY_SECURITIES'&&date(d.directory_date)&&Number.isFinite(Date.parse(d.retrieved_at_utc))&&Array.isArray(d.rows)&&d.rows.length===d.count&&d.count>0&&d.count<=100000);
 const seen=new Set();for(const r of d.rows){requireValid(typeof r.symbol==='string'&&r.symbol.length>0&&r.symbol.length<=20&&!seen.has(r.symbol)&&typeof r.name==='string'&&typeof r.exchange==='string'&&r.source_row?.ETF==='Y'&&r.source_row['Test Issue']==='N');seen.add(r.symbol);}return 'US';
}
function node(tag,value){const e=document.createElement(tag);e.textContent=value;return e;}
const fmt=v=>v===null||v===undefined?'미확인':new Intl.NumberFormat('ko-KR',{maximumFractionDigits:4}).format(v);
function records(){
 if($('market').value==='US')return(us?.rows||[]).map(r=>({...r,code:r.symbol,market:'US',state:'Nasdaq ETF 표시 · 구조 분류 전'}));
 const map=new Map((inventory?.products||[]).map(r=>[r.code,{...r,market:'KR',krx:true,state:'KRX 관측 · 보조자료 없음'}]));
 for(const r of provider?.records||[]){const base=map.get(r.code);map.set(r.code,{...r,market:'KR',krx:!!base,krxName:base?.name,state:base?'KRX 관측 + FunETF':'FunETF · KRX 전체시장 대조 전'});}return [...map.values()];
}
function draw(){
 const isUS=$('market').value==='US';$('rise').disabled=isUS;
 const needle=$('search').value.trim().toLowerCase();current=records().filter(r=>(isUS||!$('rise').checked||r.krx||r.name.startsWith('RISE '))&&`${r.code} ${r.name}`.toLowerCase().includes(needle));
 $('basis').textContent=isUS?(us?`Nasdaq Trader 목록 생성일 ${us.directory_date} · 입수 ${us.retrieved_at_utc} · 가격·수익률 자료 없음`:'미국 목록 파일을 연결하면 표시됩니다.'):`KRX ${inventory?.observed_on||'불러오기 실패'} 기준 · FunETF 수치 관측일 ${provider?.metadata.observation_date||'미확인'} · 화면 기준일 ${provider?.metadata.screen_date||'미확인'}`;
 const pages=Math.max(1,Math.ceil(current.length/30));page=Math.min(page,pages-1);$('rows').replaceChildren();
 for(const r of current.slice(page*30,page*30+30)){const tr=node('tr',''),cell=node('td',''),cb=document.createElement('input');cb.type='checkbox';cb.checked=selected.has(r.code);cb.setAttribute('aria-label',`${r.name} 비교`);cb.onchange=()=>{if(cb.checked&&selected.size>=4){cb.checked=false;$('fileStatus').textContent='한 번에 최대 4개를 비교할 수 있습니다.';return;}cb.checked?selected.add(r.code):selected.delete(r.code);updateCount();};cell.append(cb);tr.append(cell,node('td',r.code));const name=node('td',''),b=node('button',r.name);b.onclick=()=>details([r]);name.append(b);tr.append(name,node('td',r.state));$('rows').append(tr);}
 $('count').textContent=`${current.length}종목`;$('page').textContent=`${page+1} / ${pages}`;$('previous').disabled=page===0;$('next').disabled=page===pages-1;updateCount();
}
function updateCount(){$('compare').textContent=`선택 비교 (${selected.size}/4)`;}
function details(rs){$('detail').hidden=false;$('details').replaceChildren();$('detailTitle').textContent=rs.length===1?'ETF 상세':'ETF 비교';if(!rs.length){$('details').textContent='비교할 ETF를 선택하세요.';return;}
 const table=node('table',''),head=node('tr','');head.append(node('th','항목'));rs.forEach(r=>head.append(node('th',`${r.name} (${r.code})`)));table.append(head);
 const fields=['자료 상태','원천','자료 기준일','KRX 명칭','운용사','유형','상장시장','총보수(%)','합성총보수(TER)(%)','실부담비율(%)','순자산(억원)','1일(%)','1개월(%)','3개월(%)','6개월(%)','1년(%)','TOP1','TOP2','TOP3'];
 for(const k of fields){const tr=node('tr','');tr.append(node('th',k));for(const r of rs){let v='미확인';if(k==='자료 상태')v=r.state;else if(k==='원천')v=r.market==='US'?'Nasdaq Trader':r.metrics?'FunETF (보조자료)':'KRX';else if(k==='자료 기준일')v=r.market==='US'?us.directory_date:r.metrics?(provider.metadata.observation_date||'수치 관측일 미표기'):inventory.observed_on;else if(k==='KRX 명칭')v=r.krxName||(r.krx?r.name:'대조 범위 밖');else if(k==='운용사')v=r.provider||v;else if(k==='유형')v=r.category||v;else if(k==='상장시장')v=r.exchange||v;else if(k.startsWith('TOP')){const h=r.holdings_top3?.[Number(k.slice(3))-1];if(h)v=`${h.name||'미확인'} / ${fmt(h.weight_pct)}%`;}else v=fmt(r.metrics?.[k]);tr.append(node('td',v));}table.append(tr);}$('details').append(table);$('detail').focus();
}
function resetView(){selected.clear();page=0;$('detail').hidden=true;draw();}
$('file').onchange=async()=>{try{const f=$('file').files[0];if(!f)return;requireValid(f.size<=25*1024*1024);const d=JSON.parse(await f.text()),market=validate(d);if(market==='KR')provider=d;else us=d;$('market').value=market;$('fileStatus').textContent=`${market==='KR'?'FunETF':'미국 목록'} 연결 완료 · 브라우저 내부에서만 사용`;resetView();}catch(e){$('fileStatus').textContent=`연결 실패: ${e.message}. 이전 정상 자료를 유지합니다.`;}finally{$('file').value='';}};
$('clear').onclick=()=>{provider=us=null;$('fileStatus').textContent='개인용 자료를 해제했습니다.';resetView();};$('market').onchange=resetView;$('search').oninput=$('rise').onchange=()=>{page=0;draw();};$('compare').onclick=()=>details(records().filter(r=>selected.has(r.code)));$('previous').onclick=()=>{page--;draw();};$('next').onclick=()=>{page++;draw();};
(async()=>{try{const response=await fetch('data/quality/krx_rise_inventory.json',{cache:'no-store'});if(!response.ok)throw Error('KRX 응답 오류');const d=await response.json();requireValid(d.source_id==='KRX_OPEN_API_ETF_DAILY'&&date(d.observed_on)&&Array.isArray(d.products)&&d.products.length===d.observed_count&&new Set(d.products.map(r=>r.code)).size===d.observed_count&&d.products.every(r=>/^[0-9A-Z]{6}$/.test(r.code)&&typeof r.name==='string'));inventory=d;$('status').textContent=`KRX ${d.observed_on} 관측 RISE ${d.observed_count}개 · 현재 상장 여부는 최신 공시 확인 필요`;}catch(e){$('status').textContent=`KRX 목록 표시 실패: ${e.message}`;}draw();})();
