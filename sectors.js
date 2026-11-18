'use strict';
let sectorData;
const renderSectors=()=>{
 const target=document.getElementById('sectorRows');target.replaceChildren();
 const key=document.getElementById('sectorSort').value;
 const rows=[...sectorData.rows].sort((a,b)=>key==='sector'?a.sector.localeCompare(b.sector):((b[key]??-Infinity)-(a[key]??-Infinity))||a.code.localeCompare(b.code));
 const fmt=(v,d=2)=>Number.isFinite(v)?v.toLocaleString('ko-KR',{maximumFractionDigits:d}):'미계산';
 for(const row of rows){
 const card=document.createElement('article');
 for(const [tag,value] of [['h3',row.sector+' · '+row.code],['p','30일 구간 종가 수익률 '+fmt(row.return_pct)+(row.return_pct===null?'':'%')],['p','SPY 대비 RS '+fmt(row.rs_vs_spy_pct)+(row.rs_vs_spy_pct===null?'':'%')],['p','20개 공통 관측일 거래대금 근사치 중앙값: '+fmt(row.median_close_times_volume_usd,0)+' USD'],['p','최근 관측 '+(row.last_date||'없음')+' · 수집 '+row.status]]){
 const e=document.createElement(tag);e.textContent=value;card.append(e);}
 target.append(card);
 }
};
document.getElementById('sectorSort').addEventListener('change',()=>{if(sectorData)renderSectors();});
fetch('data/sector_series/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{
 if(!Array.isArray(d.rows))throw Error('rows');
 sectorData=d;document.getElementById('sectorStatus').textContent='수집 '+d.captured_count+'/'+d.requested_count+' (SPY 포함) · 공통 구간 '+(d.start_date||'미확보')+' → '+(d.end_date||'미확보');
 document.getElementById('sectorNote').textContent=d.note;renderSectors();
}).catch(()=>{document.getElementById('sectorStatus').textContent='첫 수집 대기 또는 자료 불러오기 실패. 수익률은 아직 표시하지 않습니다.';});
