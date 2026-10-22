'use strict';
let companies=[],period='',sortKey='total',direction=-1;
const money=v=>v==null?'미확인':(v/1e8).toLocaleString('ko-KR',{maximumFractionDigits:0});
function value(c,key){const d=c.periods[period]||{};return ({name:c.name,industry:c.industry||'미분류',cash:d.cash?.value,short:d.short?.value,total:d.cash_plus_short,change:c.change,ratio:d.ratio,evidence:c.note_review?.label||(d.clues?.length?'계정 단서':'미확인')})[key];}
function compare(a,b){const x=value(a,sortKey),y=value(b,sortKey);if(x==null)return y==null?0:1;if(y==null)return -1;return direction*(typeof x==='string'?x.localeCompare(y,'ko'):x-y);}
function render(){
 const query=document.querySelector('#query').value.trim().toLowerCase();
 const items=companies.filter(c=>(c.name+c.code+(c.industry||'')).toLowerCase().includes(query)).sort(compare);
 document.querySelectorAll('th[data-key]').forEach(th=>{const active=th.dataset.key===sortKey;th.setAttribute('aria-sort',active?(direction===1?'ascending':'descending'):'none');th.querySelector('span').textContent=active?(direction===1?' ▲':' ▼'):' ↕';});
 const body=document.querySelector('#rows');body.replaceChildren();
 for(const c of items){
  const d=c.periods[period]||{},row=document.createElement('tr');
  const fields=[c.name+' ('+c.code+')',c.industry||'미분류',money(d.cash?.value),money(d.short?.value),money(d.cash_plus_short),money(c.change),d.ratio==null?'미확인':(100*d.ratio).toFixed(1)+'%'];
  for(const v of fields){const cell=document.createElement('td');cell.textContent=v;row.append(cell);}
  const cell=document.createElement('td'),details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=value(c,'evidence');details.append(summary);
  const p=document.createElement('p');p.textContent=(d.clues||[]).join(' / ')||'식별된 금융자산 계정 없음';details.append(p);
  if(c.note_review){const note=document.createElement('p');note.textContent=c.note_review.summary+" 검토범위: "+c.note_review.coverage;details.append(note);}
  for(const [date,f] of Object.entries(c.periods)){if(!/^\d{14}$/.test(f.receipt||''))continue;const a=document.createElement('a');a.href='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+f.receipt;a.target='_blank';a.rel='noopener';a.textContent=date+' 공시 ↗';details.append(a,document.createElement('br'));}
  cell.append(details);row.append(cell);body.append(row);
 }
 if(!items.length){const row=body.insertRow(),cell=row.insertCell();cell.colSpan=8;cell.textContent='검색 결과가 없습니다.';}
 document.querySelector('#count').textContent=`${items.length} / ${companies.length}개사`;
}
Promise.all([fetch('data/corporate/latest.json').then(r=>{if(!r.ok)throw Error();return r.json();}),fetch('data/corporate/profiles.json').then(r=>{if(!r.ok)throw Error();return r.json();})]).then(([d,profiles])=>{if(d.schema_version!==1||!Array.isArray(d.companies))throw Error();period=d.period;companies=d.companies.map(c=>({...c,...profiles[c.code]}));document.querySelector('#status').textContent=`기준 ${d.period} / 비교 ${d.comparison_period} · 별도 · ${companies.length}개사`;render();}).catch(()=>{document.querySelector('#status').textContent='자료를 불러오지 못했습니다. 수집 상태를 확인해주세요.';});
document.querySelector('#query').addEventListener('input',render);
document.querySelectorAll('th[data-key] button').forEach(button=>button.addEventListener('click',()=>{const key=button.parentElement.dataset.key;direction=key===sortKey?-direction:(['name','industry','evidence'].includes(key)?1:-1);sortKey=key;render();}));
