'use strict';
(()=>{
const el=id=>document.getElementById(id), state={};
const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e;};
function item(target,title,body,detail){
 const box=document.createElement('div');box.className='work-item';
 box.append(text('strong',title),text('p',body));
 if(detail){const d=document.createElement('details');d.append(text('summary','근거·다음 조사'),text('p',detail));box.append(d);}
 target.append(box);
 return box;
}
function render(){
 const q=el('workSearch').value.trim().toLowerCase();
 const match=x=>JSON.stringify(x).toLowerCase().includes(q);
 for(const [key,id] of [['report','workSignals'],['report','workMatches'],['rs','workRS'],['discovery','workProduct']]){
  const t=el(id);t.replaceChildren();if(!state[key]){t.textContent=state[key]===null?'자료를 불러오지 못했습니다. 상세 페이지에서 확인하세요.':'불러오는 중';}
 }
 const d=state.report;
 if(d){
 el('workAsOf').textContent='보고서 '+d.asof_date+' · 자료별 관측일은 아래 근거에서 확인';
 for(const s of d.decision_board||[])if(match(s)) item(el('workSignals'),s.signal_id,s.what_changed,'전달 경로: '+s.transmission+' / 반대 근거: '+s.counterargument+' / 다음 확인: '+s.falsification);
 const codes=new Map();
 for(const r of d.top_rise_matches||[]){const k=r.code||r.name;if(!codes.has(k))codes.set(k,[]);codes.get(k).push(r);}
 for(const rows of codes.values())if(match(rows)){
 const r=rows[0];const card=item(el('workMatches'),r.name+' · '+r.code,[...new Set(rows.map(x=>x.angle))].join(' / '),'상품명 기반 조사 후보 · 노출 미확정. 원장 '+r.inventory_asof+' / 신호 '+[...new Set(rows.map(x=>x.signal_id))].join(', ')+' / '+[...new Set(rows.map(x=>x.counter))].join(' / '));
 const link=text('a','이 ETF 가격·NAV·수익률 보기 →');link.href='etf.html?q='+encodeURIComponent(r.code);card.append(link);
 }
 for(const id of ['workSignals','workMatches'])if(!el(id).children.length)el(id).textContent=q?'검색 결과 없음':'이번 보고서에 등록된 항목 없음';
 }
 const rs=state.rs;
 if(rs){
 const t=el('workRS'),w=(rs.windows||[]).find(x=>x.calendar_days===30);
 t.append(text('p','30일 구간 · 원화 기준 · 공통 관측 '+(rs.latest_common_date||'미확인')));
 if(w?.status==='CALCULATED_RESEARCH_ONLY'){
 t.append(text('p',w.start_date+' → '+w.end_date+' · 배당 미반영 연구용 가격 비교'));
 for(const r of [...w.rows].sort((a,b)=>a.krw_rank-b.krw_rank).filter(match)){
 const value=Number.isFinite(r.krw_return_pct)?r.krw_return_pct.toFixed(2)+'%':'미확인';
 item(t,r.krw_rank+'. '+r.name,value+' · 원화 수익률','동일 지수 ETF와 개별주를 포함한 시범 표본입니다. 대표자산 선정·투자 신호와 구분합니다.');
 }
 }else t.append(text('p','공통 기간이 부족하거나 가격 비교가 보류된 구간입니다.'));
 }
 if(state.discovery){
 const t=el('workProduct');t.append(text('p','관찰 대상 목록 · 상품 공백이나 출시 추천을 뜻하지 않습니다.'));
 for(const [key,rows] of Object.entries(state.discovery.groups||{}))for(const r of rows)if(match(r)){
 const card=item(t,r.name,r.primary?'비교 후보 '+r.primary+' / '+r.peer:r.note,'다음 조사: 국내 경쟁상품 중복 → 투자자 수요 → 편입 가능성 → RISE 기존 상품과 차별성');
 if(r.primary){const link=text('a','이 섹터 실제 수익률·거래량 비교 →');link.href='sectors.html?q='+encodeURIComponent(r.name);card.append(link);}
 }
 if(d?.product_assessment)t.append(text('p',d.product_assessment));
 }
}
el('workSearch').addEventListener('input',render);
for(const [key,path] of [['report','intelligence/data/latest.json'],['rs','data/research/rs.json'],['discovery','data/universe/discovery.json']]){
 fetch(path,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{state[key]=d;render();}).catch(()=>{state[key]=null;render();});
}
})();
