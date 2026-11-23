'use strict';
(()=>{
const el=id=>document.getElementById(id),put=(p,t,v)=>{const x=document.createElement(t);x.textContent=v;p.append(x);return x;};
const names={VIXCLS:'미국 변동성 · VIX',T10Y2Y:'미국 10년−2년 금리차',DCOILWTICO:'WTI 원유',WRESBAL:'연준 지급준비금',DGS10:'미국 10년 금리',DGS2:'미국 2년 금리',BAMLC0A0CM:'미국 투자등급 신용스프레드',BAMLH0A0HYM2:'미국 하이일드 스프레드',DCOILBRENTEU:'브렌트유',DTWEXBGS:'달러 실효환율',SOFR:'SOFR'};
fetch('intelligence/data/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{
const root=el('macroBoard');root.replaceChildren();
const order=['VIXCLS','DGS10','DGS2','T10Y2Y','BAMLH0A0HYM2','BAMLC0A0CM','DCOILWTICO','DCOILBRENTEU','DTWEXBGS','SOFR','WRESBAL'];
const rows=[...(d.observations||[])].sort((a,b)=>(order.indexOf(a.series_id)<0?999:order.indexOf(a.series_id))-(order.indexOf(b.series_id)<0?999:order.indexOf(b.series_id)));
for(const r of rows){
 const card=put(root,'article','');card.className='macro-card';
 put(card,'h3',names[r.series_id]||r.name||r.series_id);
 const value=put(card,'div',Number.isFinite(r.value)?r.value.toLocaleString('ko-KR',{maximumFractionDigits:3}):'미확인');value.className='macro-value';
 const units={Percent:'%',Index:'지수','USD/bbl':'USD/배럴','Millions USD':'백만 USD'};
 put(value,'span',units[r.unit]||r.unit||'').className='macro-unit';
 const meta=put(card,'div','');meta.className='macro-meta';
 put(meta,'span',r.observation_date||'기준일 미확인');
 if(r.source_url){try{const url=new URL(r.source_url);if(url.protocol==='https:'){const a=put(meta,'a','출처');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';}}catch{}}
 if(r.fresh_for_report===false)put(card,'span','과거 기준일 자료').className='context-tag';
}
if(!root.children.length)root.textContent='보고서에 관측값 없음';
}).catch(()=>{el('macroBoard').textContent='시장 지표 연결 실패';});
let data;
function render(){
const root=el('moverBoard');root.replaceChildren();const horizon=el('moverPeriod').value,mode=el('moverSort').value;
const field=r=>mode==='value'?r.trading_value:r.returns?.[horizon]?.pct;
const rows=data.products.filter(r=>Number.isFinite(field(r))).sort((a,b)=>(mode==='down'?1:-1)*(field(a)-field(b))||a.code.localeCompare(b.code));
el('moverDate').textContent=data.observation_date+' · '+rows.length+'/'+data.products.length+'개 값 확보 · 분배금 미반영 가격 수익률 · 거래대금은 순유입 아님';
for(const [i,r] of rows.slice(0,8).entries()){
 const card=put(root,'div','');card.className='mover-row';
 put(card,'span',String(i+1).padStart(2,'0')).className='mover-rank';
 const link=put(card,'a',r.name);link.href='etf.html?q='+encodeURIComponent(r.code);link.className='mover-name';put(link,'small',r.code);
 const pct=r.returns?.[horizon]?.pct;
 const value=put(card,'div',mode==='value'?(r.trading_value/1e8).toFixed(1)+'억':Number.isFinite(pct)?(pct>0?'+':'')+pct.toFixed(2)+'%':'미확인');
 value.className='mover-value'+(mode!=='value'&&Number.isFinite(pct)?pct>0?' positive':pct<0?' negative':'':'');
 put(value,'small',mode==='value'?'거래대금':horizon+' 가격 수익률');
}
if(!rows.length)root.textContent='선택 기준으로 계산된 값 없음';
}
for(const id of ['moverPeriod','moverSort'])el(id).addEventListener('change',()=>{if(data)render();});
fetch('data/etf_market/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(!Array.isArray(d.products))throw Error();data=d;render();}).catch(()=>{el('moverBoard').textContent='RISE 가격 자료 연결 실패';});
})();
(()=>{
 const el=id=>document.getElementById(id),add=(p,t,v)=>{const n=document.createElement(t);n.textContent=v;p.append(n);return n;};let data,attempt;
 function render(){
 const root=el('naverFlows');root.replaceChildren();
 const dates=data.flows.map(r=>r.observation_date).sort(),day=dates.at(-1),field=el('naverInvestor').value;
 const rows=data.flows.filter(r=>r.observation_date===day&&Number.isFinite(r[field])).sort((a,b)=>b[field]-a[field]);
 el('naverStatus').textContent='수급 기준 '+(day||'미확인')+' · 해당일 '+rows.length+'개 · 수집 '+data.retrieved_at+(attempt?.status!=='SUCCESS'?' · 최근 수집 미완료, 이전 성공본':'');
 for(const r of rows.slice(0,10)){const card=add(root,'div','');card.className='work-item';const a=add(card,'a',r.name);a.href='etf.html?q='+encodeURIComponent(r.code);add(card,'p',(r[field]>0?'+':'')+r[field].toLocaleString('ko-KR')+'주');}
 if(!rows.length)add(root,'p','선택 투자자의 비교 가능한 수급 없음');
 }
 el('naverInvestor').addEventListener('change',()=>{if(data)render();});
 Promise.all(['data/naver_etf/latest.json','data/naver_etf/status.json'].map(async u=>{const r=await fetch(u,{cache:'no-store'});if(!r.ok)throw Error();return r.json();})).then(([d,s])=>{if(d.schema!=='NAVER_ETF_DAILY_V1'||!Array.isArray(d.flows))throw Error();data=d;attempt=s;render();}).catch(()=>{el('naverStatus').textContent='완전 수집본 미확보 또는 연결 실패 · 자동 수집 상태 확인 필요';});
})();
