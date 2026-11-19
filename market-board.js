'use strict';
(()=>{
const el=id=>document.getElementById(id),put=(p,t,v)=>{const x=document.createElement(t);x.textContent=v;p.append(x);return x;};
const names={DGS10:'미국 10년 금리',DGS2:'미국 2년 금리',BAMLC0A0CM:'미국 투자등급 신용스프레드',BAMLH0A0HYM2:'미국 하이일드 스프레드',DCOILBRENTEU:'브렌트유',DTWEXBGS:'달러 실효환율',SOFR:'SOFR'};
fetch('intelligence/data/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{
const root=el('macroBoard');root.replaceChildren();
for(const r of d.observations||[]){
 const card=put(root,'div','');card.className='work-item';
 put(card,'strong',names[r.series_id]||r.name||r.series_id);
 put(card,'p',(Number.isFinite(r.value)?r.value.toLocaleString('ko-KR',{maximumFractionDigits:3}):'미확인')+' '+r.unit+' · '+r.observation_date);
 if(r.source_url){try{const url=new URL(r.source_url);if(url.protocol==='https:'){const a=put(card,'a','출처 확인 →');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';}}catch{}}
}
if(!root.children.length)root.textContent='보고서에 관측값 없음';
}).catch(()=>{el('macroBoard').textContent='시장 지표 연결 실패';});
let data;
function render(){
const root=el('moverBoard');root.replaceChildren();const horizon=el('moverPeriod').value,mode=el('moverSort').value;
const field=r=>mode==='value'?r.trading_value:r.returns?.[horizon]?.pct;
const rows=data.products.filter(r=>Number.isFinite(field(r))).sort((a,b)=>(mode==='down'?1:-1)*(field(a)-field(b))||a.code.localeCompare(b.code));
el('moverDate').textContent=data.observation_date+' · '+rows.length+'/'+data.products.length+'개 값 확보 · 분배금 미반영 가격 수익률 · 거래대금은 순유입 아님';
for(const r of rows.slice(0,8)){const card=put(root,'div','');card.className='work-item';put(card,'a',r.name+' →').href='etf.html?q='+encodeURIComponent(r.code);
const pct=r.returns?.[horizon]?.pct;
put(card,'p',horizon+' '+(Number.isFinite(pct)?pct.toFixed(2)+'%':'미확인')+' · 거래대금 '+(Number.isFinite(r.trading_value)?(r.trading_value/1e8).toFixed(1)+'억원':'미확인'));
}
if(!rows.length)root.textContent='선택 기준으로 계산된 값 없음';
}
for(const id of ['moverPeriod','moverSort'])el(id).addEventListener('change',()=>{if(data)render();});
fetch('data/etf_market/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(!Array.isArray(d.products))throw Error();data=d;render();}).catch(()=>{el('moverBoard').textContent='RISE 가격 자료 연결 실패';});
})();