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

const topics={
 'SIG-RATE-001':{title:'미국 장기금리',question:'금리 변화가 채권형 ETF에 어떤 의미인가요?',terms:['미국국채','국고채'],check:'듀레이션·만기·환헤지와 같은 기간의 ETF 가격을 함께 확인합니다.'},
 'SIG-RATE-002':{title:'장단기 금리차',question:'장단기 금리차만으로 경기 방향을 판단할 수 있나요?',terms:['단기','장기국채'],check:'금리차와 2년·10년 금리의 움직임을 구분하고 만기별 노출을 비교합니다.'},
 'SIG-CREDIT-001':{title:'회사채 신용 여건',question:'회사채 상품을 설명할 때 무엇을 확인해야 하나요?',terms:['회사채','종합채권'],check:'신용등급·듀레이션·편입채권과 스프레드 기준일을 확인합니다.'},
 'SIG-LIQ-001':{title:'단기금리와 유동성',question:'현금성 ETF는 어떤 기준으로 비교하나요?',terms:['머니마켓','SOFR','CD금리'],check:'추종금리·통화·환헤지·보수 및 편입자산을 비교합니다.'},
 'SIG-ENERGY-001':{title:'에너지 가격',question:'유가 움직임을 관련 ETF에 바로 적용할 수 있나요?',terms:['원유','에너지'],check:'원유선물과 에너지기업 주식은 노출이 다릅니다. 추종지수·선물 만기·환헤지를 확인합니다.'},
 'SIG-MKT-001':{title:'미국 주식 변동성',question:'변동성이 높아지면 고객에게 무엇을 설명해야 하나요?',terms:['커버드콜','S&P500'],check:'변동성 지표만으로 수익을 단정하지 않고 기초자산·옵션 매도 비중·상승 참여 제한을 확인합니다.'}
};
const seriesNames={DGS10:'미국 10년 금리',DGS2:'미국 2년 금리',T10Y2Y:'미국 장단기 금리차',BAMLC0A0CM:'투자등급 신용스프레드',BAMLH0A0HYM2:'하이일드 신용스프레드',SOFR:'SOFR',WRESBAL:'연준 지급준비금',DCOILBRENTEU:'브렌트유',DCOILWTICO:'WTI',VIXCLS:'VIX'};
function briefCard(signal,report,target){
 const topic=topics[signal.signal_id]||{title:signal.signal_id,question:'이 관측값은 어떻게 활용하나요?',terms:[],check:'실제 상품의 투자대상과 같은 기준일의 자료를 확인합니다.'};
 const card=text('section','');card.className='issue-card';
 const labels={NORMAL:'일반 관찰',WATCH:'주의 관찰',ACTIVE_CANDIDATE:'집중 관찰 후보'};
 const head=text('div','');head.className='issue-heading';head.append(text('h4',topic.title),text('span',labels[signal.status]||'상태 미확인'));card.append(head);
 const facts=(report.observations||[]).filter(r=>(signal.series_ids||[]).includes(r.series_id));
 const readings=facts.map(r=>(seriesNames[r.series_id]||r.name||r.series_id)+' '+(Number.isFinite(r.value)?r.value.toLocaleString('ko-KR',{maximumFractionDigits:3}):'미확인')+' '+({Percent:'%',Index:'지수','USD/bbl':'USD/배럴','Millions USD':'백만 USD'}[r.unit]||r.unit||'')+' ('+(r.observation_date||'기준일 미확인')+')'+(r.fresh_for_report===false?' · 과거 기준일 자료':''));
 const evidence=text('div','');evidence.className='issue-evidence';evidence.append(text('strong','관측 사실'),text('p',readings.join(' / ')||'연결된 관측값 없음'));
 for(const r of facts){try{const url=new URL(r.source_url);if(url.protocol==='https:'){const a=text('a',(seriesNames[r.series_id]||r.series_id)+' 출처');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';evidence.append(a);}}catch{}}
 card.append(evidence);
 const columns=text('div','');columns.className='issue-columns';
 const analysis=text('div','');analysis.append(text('strong','해석과 확인할 점'),text('p',signal.transmission||'해석 미제공'),text('p',topic.check));
 const counter=text('details','');counter.append(text('summary','반대 근거·다음 확인'),text('p',signal.counterargument||'반대 근거 미제공'),text('p',signal.falsification||'추가 확인 필요'));analysis.append(counter);
 const product=text('div','');product.append(text('strong','RISE 상품 조사'),text('p','아래는 상품명 검색입니다. 관련성·편입·수혜가 확인된 상품 목록이 아닙니다.'));
 const links=text('div','');links.className='issue-links';for(const term of topic.terms){const a=text('a',term+' 검색');a.href='etf.html?q='+encodeURIComponent(term);links.append(a);}product.append(links);
 columns.append(analysis,product);card.append(columns);
 const draft='[내부 검토용 응대 초안 · 보고서 '+(report.asof_date||'기준일 미확인')+']\n질문: '+topic.question+'\n'+(readings.length?'확인된 관측값은 '+readings.join(', ')+'입니다.':'연결된 관측값이 없어 수치 설명을 보류합니다.')+' 자료별 관측일이 다를 수 있으며 오늘 시세를 뜻하지 않습니다. '+topic.check+' 개별 상품의 영향과 투자 방향은 이 자료만으로 확정할 수 없습니다.';
 const response=text('div','');response.className='response-draft';response.append(text('strong',topic.question),text('p',draft));
 const button=text('button','응대 초안 복사');button.type='button';
 const status=text('span','');status.setAttribute('role','status');
 button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(draft);status.textContent='초안을 복사했습니다.';}catch{status.textContent='자동 복사를 사용할 수 없습니다. 위 문구를 선택해 복사하세요.';}});
 response.append(button,status);card.append(response);
 const detail=text('details','');detail.append(text('summary','원시 신호·계산 근거'),text('p',signal.signal_id+' · '+(signal.what_changed||'변화량 미제공')),text('p',signal.confidence||'신뢰 수준 미제공'));card.append(detail);target.append(card);
}

function render(){
 const q=el('workSearch').value.trim().toLowerCase();
 const match=x=>JSON.stringify(x).toLowerCase().includes(q);
 for(const [key,id] of [['report','workSignals'],['report','workMatches'],['rs','workRS'],['discovery','workProduct'],['investigations','workInvestigations']]){
  const t=el(id);t.replaceChildren();if(!state[key]){t.textContent=state[key]===null?'자료를 불러오지 못했습니다. 상세 페이지에서 확인하세요.':'불러오는 중';}
 }
 const d=state.report;
 if(d){
 el('workAsOf').textContent='보고서 '+d.asof_date+' · 자료별 관측일은 아래 근거에서 확인';
 const priority={ACTIVE_CANDIDATE:0,WATCH:1,NORMAL:2};
 for(const s of [...(d.decision_board||[])].sort((a,b)=>(priority[a.status]??3)-(priority[b.status]??3)))if(match([s,topics[s.signal_id],(d.observations||[]).filter(r=>(s.series_ids||[]).includes(r.series_id))]))briefCard(s,d,el('workSignals'));
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
 const inv=state.investigations;
 if(inv){
 const target=el('workInvestigations');
 target.append(text('p',inv.observation_date+' · 전체 '+inv.screened_count+'개 관찰 · 조건 충족 '+inv.candidate_count+'개 · 우선 조사 '+inv.items.length+'개 · 후순위 '+inv.deferred_count+'개'));
 target.append(text('p','가격 급변·NAV 괴리·거래량 급증 기준의 조사 목록입니다. 투자 추천이나 보유종목 분석 완료를 뜻하지 않습니다.'));
 const labels={PRICE_MOVE:'가격 변화',NAV_GAP:'NAV 괴리',VOLUME_SPIKE:'거래량 배수'};
 const rows=inv.items.filter(match);
 if(!rows.length)target.append(text('p',q?'검색 결과 없음':'우선 조사 항목 없음'));
 for(const row of rows){
 const signals=(row.signals||[]).map(s=>(labels[s.kind]||s.kind)+' '+(Number.isFinite(s.value)?s.value.toLocaleString('ko-KR',{maximumFractionDigits:2}):'미확인')+s.unit).join(' / ');
 const card=item(target,row.name+' · '+row.ticker,signals,(row.pdf_request?.instruction||'동일 기준일 구성내역 확보 필요')+' · 보유종목 확인: '+(row.holdings_verified?'확인됨':'미확인'));
 if(row.name.startsWith('RISE ')){const link=text('a','RISE 가격·NAV 확인 →');link.href='etf.html?q='+encodeURIComponent(row.ticker);card.append(link);}
 }
 }

}
el('workSearch').addEventListener('input',render);
for(const [key,path] of [['report','intelligence/data/latest.json'],['rs','data/research/rs.json'],['discovery','data/universe/discovery.json'],['investigations','data/etf_investigations/latest.json']]){
 fetch(path,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{state[key]=d;render();}).catch(()=>{state[key]=null;render();});
}
})();
