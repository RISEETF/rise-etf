'use strict';
let companies=[],period='',sortKey='total',direction=-1;
const money=v=>v==null?'미확인':(v/1e8).toLocaleString('ko-KR',{maximumFractionDigits:0});
function value(c,key){const d=c.periods[period]||{};return ({name:c.name,industry:c.industry||'미분류',cash:d.cash?.value,short:d.short?.value,total:d.cash_plus_short,change:c.change,ratio:d.ratio,pension:c.pension?.plan_assets_krw,evidence:c.note_review?.label||(d.clues?.length?'계정 단서 · 주석 미검토':'주석 미검토')})[key];}
function compare(a,b){const x=value(a,sortKey),y=value(b,sortKey);if(x==null)return y==null?0:1;if(y==null)return -1;return direction*(typeof x==='string'?x.localeCompare(y,'ko'):x-y);}
function render(){
 const query=document.querySelector('#query').value.trim().toLowerCase();
 const industry=document.querySelector('#industry').value,review=document.querySelector('#review').value,minimum=Number(document.querySelector('#minimum').value)*1e8;
 const filtered=companies.filter(c=>{const d=c.periods[period]||{};return (!industry||c.industry===industry)&&(!minimum||(d.cash_plus_short!=null&&d.cash_plus_short>=minimum))&&(!review||(review==='reviewed'&&!!c.note_review)||(review==='pending'&&!c.note_review)||(review==='clue'&&!!d.clues?.length)||(review==='pension'&&c.pension?.plan_assets_krw!=null)||(review==='missing'&&d.cash_plus_short==null));});
 const items=filtered.filter(c=>(c.name+c.code+(c.industry||'')+' '+JSON.stringify(c.marketing||{})+' '+JSON.stringify(c.pension||{})+' '+JSON.stringify(c.note_review||{})+' '+JSON.stringify(c.periods[period]?.clues||[])).toLowerCase().includes(query)).sort(compare);
 document.querySelectorAll('th[data-key]').forEach(th=>{const active=th.dataset.key===sortKey;th.setAttribute('aria-sort',active?(direction===1?'ascending':'descending'):'none');th.querySelector('span').textContent=active?(direction===1?' ▲':' ▼'):' ↕';});
 const body=document.querySelector('#rows');body.replaceChildren();
 for(const c of items){
  const d=c.periods[period]||{},row=document.createElement('tr');
  const fields=[c.name+' ('+c.code+')',c.industry||'미분류',money(d.cash?.value),money(d.short?.value),money(d.cash_plus_short),money(c.change),d.ratio==null?'미확인':(100*d.ratio).toFixed(1)+'%',money(c.pension?.plan_assets_krw)];
  for(const v of fields){const cell=document.createElement('td');cell.textContent=v;row.append(cell);}
  const cell=document.createElement('td'),details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=value(c,'evidence');details.append(summary);
  if(d.cash_plus_short==null){const missing=document.createElement('p');missing.textContent='합계 미확인: '+[['현금',d.cash],['단기금융상품',d.short]].filter(([name,v])=>v?.value==null).map(([name,v])=>name+' '+(v?.status==='ambiguous'?'복수 계정 확인 필요':'계정 식별 필요')).join(' / ')+'. 미확인은 잔액 0원을 의미하지 않습니다.';details.append(missing);}
  const p=document.createElement('p');p.textContent=(d.clues||[]).join(' / ')||'식별된 금융자산 계정 없음';details.append(p);
  if(c.note_review){const note=document.createElement('p');note.textContent=c.note_review.summary+" 검토범위: "+c.note_review.coverage;details.append(note);}
  for(const [date,f] of Object.entries(c.periods)){if(!/^\d{14}$/.test(f.receipt||''))continue;const a=document.createElement('a');a.href='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+f.receipt;a.target='_blank';a.rel='noopener';a.textContent=date+' 공시 ↗';details.append(a,document.createElement('br'));}
  if(!c.marketing){const lead=document.createElement('p');lead.className='marketing-lead';lead.textContent=d.clues?.length?'금융자산 관련 계정 단서가 있습니다. 상품·펀드명과 DB 적립금은 주석 확인 전입니다.':'재무제표 관측 대상입니다. 펀드 보유 및 DB 관련 주석은 아직 검토하지 않았습니다.';cell.append(lead);}
  if(c.marketing){
   const lead=document.createElement('p');lead.className='marketing-lead';lead.textContent=c.marketing.angle;cell.append(lead);
   const badge=document.createElement('small');badge.textContent=c.marketing.status;cell.append(badge);
   for(const e of c.marketing.evidence){const box=document.createElement('p');box.textContent=`[${e.type}] ${e.date} · ${e.scope} — ${e.fact} `;const a=document.createElement('a');a.href=e.url;a.target='_blank';a.rel='noopener';a.textContent=e.source+' 원문';box.append(a);details.append(box);if(e.excerpt){const quote=document.createElement('blockquote');quote.textContent=e.excerpt;details.append(quote);}}
  }
  if(c.pension){const n=c.pension,box=document.createElement('p');box.textContent=`DB 사외적립자산 ${money(n.plan_assets_krw)}억원 / 확정급여채무 ${money(n.obligation_krw)}억원. ${n.as_of} ${n.scope} · ${n.section}. ${n.provider_status}. ${n.selection_status}. ${n.composition_clue||''}`;details.append(box);const quote=document.createElement('blockquote');quote.textContent=n.excerpt;details.append(quote);const q=document.createElement('p');q.textContent='회계상 사외적립자산으로, 회사 현금 합계에서 제외. 법정 적립비율이나 신규 투자 여력을 의미하지 않음.';details.append(q);}
  cell.append(details);row.append(cell);body.append(row);
 }
 if(!items.length){const row=body.insertRow(),cell=row.insertCell();cell.colSpan=9;cell.textContent='검색 결과가 없습니다.';}
 document.querySelector('#count').textContent=`${items.length} / ${companies.length}개사`;
}
Promise.all([fetch('data/corporate/latest.json').then(r=>{if(!r.ok)throw Error();return r.json();}),fetch('data/corporate/profiles.json').then(r=>{if(!r.ok)throw Error();return r.json();})]).then(([d,profiles])=>{if(d.schema_version!==1||!Array.isArray(d.companies))throw Error();period=d.period;companies=d.companies.map(c=>({...c,...profiles[c.code]}));const industries=[...new Set(companies.map(c=>c.industry||'미분류'))].sort((a,b)=>a.localeCompare(b,'ko'));for(const name of industries){const o=document.createElement('option');o.value=name;o.textContent=name;document.querySelector('#industry').append(o);}
 document.querySelector('#status').textContent=`기준 ${d.period} / 비교 ${d.comparison_period} · 별도 · ${companies.length}개사 · 주석 검토 ${companies.filter(c=>c.note_review).length}개사 / 미검토 ${companies.filter(c=>!c.note_review).length}개사`;render();}).catch(()=>{document.querySelector('#status').textContent='자료를 불러오지 못했습니다. 수집 상태를 확인해주세요.';});
document.querySelector('#query').addEventListener('input',render);
document.querySelectorAll('th[data-key] button').forEach(button=>button.addEventListener('click',()=>{const key=button.parentElement.dataset.key;direction=key===sortKey?-direction:(['name','industry','evidence'].includes(key)?1:-1);sortKey=key;render();}));

for(const id of ['industry','review','minimum'])document.querySelector('#'+id).addEventListener('change',render);
