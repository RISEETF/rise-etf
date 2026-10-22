'use strict';
let companies=[];
const money=v=>v==null?'미확인':(v/1e8).toLocaleString('ko-KR',{maximumFractionDigits:0});
function render(){
 const query=document.querySelector('#query').value.trim().toLowerCase(),sort=document.querySelector('#sort').value;
 const value=c=>sort==='change'?c.change:c.periods['2026-06-30'].cash_plus_short;
 const items=companies.filter(c=>(c.name+c.code).toLowerCase().includes(query)).sort((a,b)=>(value(b)??-Infinity)-(value(a)??-Infinity));
 const body=document.querySelector('#rows');body.replaceChildren();
 for(const c of items){
  const d=c.periods['2026-06-30'],row=document.createElement('tr');
  const fields=[c.name+' ('+c.code+')',money(d.cash?.value),money(d.short?.value),money(d.cash_plus_short),money(c.change),d.ratio==null?'미확인':(100*d.ratio).toFixed(1)+'%'];
  for(const v of fields){const cell=document.createElement('td');cell.textContent=v;row.append(cell);}
  const cell=document.createElement('td'),details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=d.clues?.length?'관련 계정 있음 · 유형 미확인':'투자 흔적 미확인';details.append(summary);
  const p=document.createElement('p');p.textContent=(d.clues||[]).join(' / ')||'식별된 계정 없음';details.append(p);
  for(const [period,f] of Object.entries(c.periods)){if(!/^\d{14}$/.test(f.receipt||''))continue;const a=document.createElement('a');a.href='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+f.receipt;a.target='_blank';a.rel='noopener';a.textContent=period+' 공시 ↗';details.append(a,document.createElement('br'));}
  cell.append(details);row.append(cell);body.append(row);
 }
 if(!items.length){const row=body.insertRow(),cell=row.insertCell();cell.colSpan=7;cell.textContent='검색 결과가 없습니다.';}
}
fetch('data/corporate/latest.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(d.schema_version!==1||!Array.isArray(d.companies))throw Error();companies=d.companies;document.querySelector('#status').textContent=`기준 ${d.period} / 비교 ${d.comparison_period} · 별도 · ${companies.length}개사 · 수집 ${d.collected_at} (UTC)`;render();}).catch(()=>{document.querySelector('#status').textContent='자료를 불러오지 못했습니다. 수집 상태를 확인해주세요.';});
document.querySelector('#query').addEventListener('input',render);document.querySelector('#sort').addEventListener('change',render);
