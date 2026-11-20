'use strict';
(()=>{
const root=document.getElementById('dataFreshness'), state={};
const configs=[
 ['krx','KRX RISE 원장','data/quality/krx_rise_inventory.json','observed_on','etf.html'],
 ['rs','통합 RS','data/research/rs.json','latest_common_date','research.html#researchTitle'],
 ['sectors','미국 섹터','data/sector_series/latest.json','end_date','sectors.html'],
 ['report','시장 보고서','intelligence/data/latest.json','asof_date','intelligence/index.html#daily'],
 ['corporate','기업 재무','data/corporate/latest.json','period','corporate.html']
];
const append=(parent,tag,value)=>{const e=document.createElement(tag);e.textContent=value;parent.append(e);return e;};
function age(value){
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value)))return '기준일 미확인';
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const n=Math.floor((Date.parse(today)-Date.parse(value))/86400000);
 return n<0?value+' · 미래 기준일 확인 필요':value+' · '+n+'일 전';
}
function render(){
 root.replaceChildren();
 for(const [key,label,path,field,href] of configs){
 const row=document.createElement('div');row.className='work-item';root.append(row);
 append(row,'a',label+' →').href=href;
 const d=state[key];
 append(row,'p',d===undefined?'불러오는 중':d===null?'자료 연결 실패':age(d[field]));
 if(key==='corporate'&&d)append(row,'small','분기 재무 기준 · 수집시각과 구분');
 if(key==='sectors'&&d)append(row,'small',state.status===undefined?'갱신 상태 확인 중':state.status===null?'최근 갱신 상태 확인 불가':state.status.status==='SUCCESS'?'최근 갱신 성공':'최근 갱신 실패 · 마지막 완전 수집본 표시');
 }
 const target=document.getElementById('sectorOverview');target.replaceChildren();
 const heat=document.getElementById('sectorHeatmap');heat.replaceChildren();
 const days=Number(document.getElementById('sectorOverviewPeriod').value);
 const source=state.sectors;
 const d=source?(source.windows||[]).find(w=>w.calendar_days===days)||(days===30?source:null):source,status=document.getElementById('sectorOverviewStatus');
 if(!d){status.textContent=source===undefined?'자료 확인 중':source===null?'섹터 자료 연결 실패':'선택 기간 자료 미확보';return;}
 status.textContent=(d.start_date||'미확보')+' → '+(d.end_date||'미확보')+' · USD · 종가 수익률, 분배금 미반영'+(state.status&&state.status.status!=='SUCCESS'?' · 최근 갱신 실패, 과거 자료':'');
 const key=document.getElementById('sectorOverviewSort').value;
 for(const r of (d.rows||[]).filter(r=>r.role==='primary').sort((a,b)=>(Number.isFinite(b[key])?b[key]:-Infinity)-(Number.isFinite(a[key])?a[key]:-Infinity))){
 const a=append(heat,'a',r.sector);a.href='sectors.html?q='+encodeURIComponent(r.code)+'&days='+days;
 const v=r.rs_vs_spy_pct;a.className='sector-tile'+(Number.isFinite(v)?v>0?' positive':v<0?' negative':'':'');
 append(a,'strong',Number.isFinite(v)?(v>0?'+':'')+v.toFixed(2)+'%':'미확보');
 append(a,'small',r.code+' · SPY 대비');
}
if(!heat.children.length)append(heat,'p','선택 기간의 섹터 비교 자료가 없습니다.');
const rows=(d.rows||[]).filter(r=>Number.isFinite(r[key])).sort((a,b)=>b[key]-a[key]||a.code.localeCompare(b.code)).slice(0,5);
 if(!rows.length)append(target,'p','계산 가능한 자료 없음');
 for(const r of rows){
 const row=document.createElement('div');row.className='work-item';target.append(row);
 append(row,'a',r.sector+' · '+r.code+' →').href='sectors.html?q='+encodeURIComponent(r.code)+'&days='+days;
 append(row,'p',key==='rs_vs_spy_pct'?'SPY 대비 '+r[key].toFixed(2)+'%':'종가×거래량 중앙값 '+Math.round(r[key]).toLocaleString('ko-KR')+' USD');
 }
 append(target,'small','ETF 상위 5개입니다. 같은 섹터가 중복될 수 있으며 거래대금은 자금 유입액이 아닙니다.');
}
document.getElementById('sectorOverviewPeriod').addEventListener('change',render);
document.getElementById('sectorOverviewSort').addEventListener('change',render);
for(const [key,label,path] of [...configs,['status','섹터 갱신','data/sector_series/status.json']]){
 fetch(path,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{state[key]=d;render();}).catch(()=>{state[key]=null;render();});
}
render();
})();