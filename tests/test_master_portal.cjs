const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const master = JSON.parse(fs.readFileSync(path.join(root, 'data/master/latest.json')));
const displayedProducts=[...master.products,...(master.pending_products || [])];
const server = http.createServer((req,res) => {
  const file = path.join(root, req.url === '/' ? 'index.html' : req.url.split('?')[0]);
  if (!file.startsWith(root + path.sep)) {res.writeHead(403).end(); return;}
  fs.readFile(file, (error, data) => {
    if(error) {res.writeHead(404).end();return;}
    res.setHeader('Content-Type', ({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'})[path.extname(file)] || 'text/plain');
    res.end(data);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const errors=[]; page.on('pageerror', e=>errors.push(e.message));
    const url=`http://127.0.0.1:${server.address().port}`;
    await page.goto(url);
    await page.waitForFunction(()=>!document.getElementById('search').disabled);
    assert.equal(await page.locator('#products tr').count(),displayedProducts.length);
    assert.equal(await page.locator('#total').textContent(),displayedProducts.length.toLocaleString('ko-KR'));
    if(master.pending_products?.length) assert.match(await page.locator('#products').textContent(),/공식 코드 확인 중/);
    const changes=JSON.parse(fs.readFileSync(path.join(root,'data/master/changes.json')));
    await page.waitForFunction(()=>!document.getElementById('masterChangesStatus').textContent.includes('확인 중'));
    assert.equal(await page.locator('#masterChanges li').count(),Math.min(changes.events.length,20));
    // Synthetic comparison exercises delayed KRX publication without claiming live verification.
    const krxFixture={status:'KRX_DAILY_IDENTITY_COMPARISON',observed_on:'2026-09-22',issuer_effective_date:master.effective_date,
      retrieved_at:'2026-09-23T00:00:00+00:00',issuer_product_count:displayedProducts.length,
      rows:displayedProducts.map((p,i)=>({detail_id:p.detail_id,issuer_code:p.code,issuer_name:p.name,issuer_listed_on:p.listed_on,
        status:i===0?'NOT_OBSERVED':'MATCHED_CODE_NAME',candidate_codes:[],krx_code:null,krx_name:null})),
      counts:{NOT_OBSERVED:1,MATCHED_CODE_NAME:displayedProducts.length-1},krx_rise_without_confirmed_issuer_code:[],
      lifecycle_notices:{status:'SUCCESS',attempted_at:'2026-09-24T01:00:00+00:00',window_start:'2026-08-25',window_end:'2026-09-24',events:[
        {receipt_id:'20260918000210',name:'RISE synthetic fixture',code:'123456',kind:'LISTING_NOTICE',published_at:'2026-09-18T16:13:00+09:00',effective_date:'2026-09-22',verification:'NOTICE_CODE_DATE_VERIFIED',in_latest_search:true,last_checked_at:'2026-09-24T01:00:00+00:00',viewer_url:'https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20260918000210'}]}};
    await page.route('**/data/quality/krx_master_reconciliation.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(krxFixture)}));
    await page.route('**/data/krx_collection_status.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({status:'FAILED',attempted_at:'2026-09-23T00:00:00+00:00'})}));
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('krxStatus').textContent.includes('KRX 기준'));
    assert.equal(await page.locator('#krxIssues li').count(),1);
    assert.match(await page.locator('#krxIssues').textContent(),/폐지 확정 아님/);
    assert.equal(await page.locator('#kindRows tr').count(),1);
    assert.match(await page.locator('#kindRows').textContent(),/본문 코드·날짜 확인/);
    assert.match(await page.locator('#kindRows').textContent(),/2026-09-22/);
    await page.waitForFunction(()=>document.getElementById('krxAttempt').textContent.includes('실패'));
    krxFixture.rows[0].issuer_name='RISE changed fixture';
    krxFixture.lifecycle_notices.status='FAILED';
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('krxStatus').textContent.includes('재대조 대기'));
    assert.equal(await page.locator('#krxIssues li').count(),0);
    assert.equal(await page.locator('#kindRows tr').count(),1);
    assert.match(await page.locator('#kindStatus').textContent(),/실패 · 마지막 성공 공시 유지/);
    krxFixture.lifecycle_notices.events[0].viewer_url='javascript:alert(1)';
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('kindStatus').textContent.includes('공시 형식 확인 필요'));
    assert.equal(await page.locator('#kindRows tr').count(),0);
    await page.unroute('**/data/quality/krx_master_reconciliation.json');
    await page.unroute('**/data/krx_collection_status.json');
    await page.reload();
    const research=JSON.parse(fs.readFileSync(path.join(root,'data/research/rs.json')));
    await page.waitForFunction(()=>!document.getElementById('researchHorizon').disabled);
    for(const days of [30,7,60]) {
      await page.locator('#researchHorizon').selectOption(String(days));
      const window=research.windows.find(w=>w.calendar_days===days);
      assert.equal(await page.locator('#researchRows tr').count(),window.rows.length);
      if(window.rows.length) assert.match(await page.locator('#researchStatus').textContent(),new RegExp(window.start_date));
    }
    await page.locator('#researchHorizon').selectOption('30');
    const currentWindow=research.windows.find(w=>w.calendar_days===30);
    await page.locator('#researchBasis').selectOption('local');
    const localOrder=[...currentWindow.rows].sort((a,b)=>a.local_rank-b.local_rank || a.instrument_id.localeCompare(b.instrument_id)).map(r=>r.instrument_id);
    assert.deepEqual(await page.locator('#researchRows tr').evaluateAll(rows=>rows.map(r=>r.dataset.instrument)),localOrder);
    assert.match(await page.locator('#researchRSHeading').textContent(),/현지통화/);
    await page.locator('#researchBasis').selectOption('krw');
    assert.equal(await page.locator('#researchSources li').count(),research.sources.length+1);
    const coverage=JSON.parse(fs.readFileSync(path.join(root,'data/series/status.json')));
    await page.waitForFunction(count=>document.querySelectorAll('#seriesRows tr').length===count,coverage.series.length);
    assert.match(await page.locator('#seriesStatus').textContent(),/RS 계산 보류/);
    const universe=JSON.parse(fs.readFileSync(path.join(root,'data/universe/status.json')));
    await page.waitForFunction(count=>document.querySelectorAll('#universeRows tr').length===count,universe.groups.length);
    assert.match(await page.locator('#universeStatus').textContent(),/대표자산 확정 0개/);
    assert.match(await page.locator('#universeRows').textContent(),/SPY/);
    assert.match(await page.locator('#universeRows').textContent(),/미국 국채 잔존만기 7~10년/);
    assert.match(await page.locator('#universeRows').textContent(),/2026-06-30 팩트시트/);
    assert.match(await page.locator('#universeRows').textContent(),/S&P 500 Index \(KRW\)\(T-1\)/);
    assert.match(await page.locator('#universeRows').textContent(),/서로 다른 수익률 기준/);
    assert.equal(await page.locator('#universeRows a[href="https://riseetf.co.kr/upload/cdn/2026/09/08/20260908bbf1937eb74144b.pdf"]').count(),1);
    await page.waitForFunction(()=>document.getElementById('issuerStatus').textContent.includes('최근 구간 8건'));
    assert.match(await page.locator('#issuerStatus').textContent(),/배당락일 확인 대기/);
    assert.match(await page.locator('#issuerSplit').textContent(),/2020-08-31/);
    await page.locator('#search').fill(master.products[0].code);
    assert.equal(await page.locator('#products tr').count(),1);
    await page.locator('#search').fill('NO_MATCH_999');
    assert.equal(await page.locator('#products tr').count(),0);
    assert.equal(await page.locator('#empty').isVisible(),true);
    await page.locator('#reset').click();
    const category=master.products[0].primary_category;
    await page.locator('#category').selectOption(category);
    assert.equal(await page.locator('#products tr').count(),displayedProducts.filter(p=>p.primary_category===category).length);
    await page.locator('#reset').click();
    await page.screenshot({path:'/tmp/rise-master-desktop.png'});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'/tmp/rise-master-mobile.png'});
    let legacyRequests=0;
    const synthetic={...research,latest_common_date:'2000-01-08',windows:[{calendar_days:30,start_date:'1999-12-09',end_date:'2000-01-08',actual_calendar_days:30,status:'CALCULATED_RESEARCH_ONLY',rows:[
      {instrument_id:'US_LISTED:SPY',name:'Test USD',currency:'USD',local_rank:2,krw_rank:1,local_return_pct:5,krw_return_pct:15.5,fx_return_pct:10,local_rs_vs_spy_pct:0,krw_rs_vs_spy_pct:0},
      {instrument_id:'XKRX:TEST',name:'Test KRW',currency:'KRW',local_rank:1,krw_rank:2,local_return_pct:10,krw_return_pct:10,fx_return_pct:0,local_rs_vs_spy_pct:100*(1.1/1.05-1),krw_rs_vs_spy_pct:100*(1.1/1.155-1)}
    ]}]};
    await page.route('**/data/research/rs.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(synthetic)}));
    await page.reload();
    await page.waitForFunction(()=>document.querySelectorAll('#researchRows tr').length===2);
    assert.equal(await page.locator('#researchFreshness').isVisible(),true);
    assert.match(await page.locator('#researchRows tr').first().textContent(),/\+10\.50%p/);
    assert.match(await page.locator('#researchSummary').textContent(),/다른 종목 2개/);
    await page.locator('#researchBasis').selectOption('local');
    assert.equal(await page.locator('#researchRows tr').first().getAttribute('data-instrument'),'XKRX:TEST');
    assert.equal(await page.locator('#researchRows tr').first().locator('td').nth(6).textContent(),'+4.76%');
    await page.locator('#researchHorizon').selectOption('60');
    assert.equal(await page.locator('#researchRows tr').count(),0);
    assert.equal(await page.locator('#researchSummary').textContent(),'');
    await page.unroute('**/data/research/rs.json');
    await page.route('**/data/research/rs.json',route=>route.fulfill({status:404,body:'missing'}));
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('researchStatus').textContent.includes('표시할 수 없습니다'));
    assert.equal(await page.locator('#researchRows tr').count(),0);
    await page.unroute('**/data/research/rs.json');
    page.on('request', r=>{if(r.url().endsWith('/data/latest.json'))legacyRequests++;});
    await page.route('**/data/master/latest.json', route=>route.fulfill({status:404,body:'missing'}));
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('masterStatus').textContent.includes('표시할 수 없습니다'));
    assert.equal(await page.locator('#products tr').count(),0);
    assert.equal(await page.locator('#search').isDisabled(),true);
    assert.equal(legacyRequests,0);
    await page.unroute('**/data/master/latest.json');
    await page.route('**/data/master/latest.json', route=>route.fulfill({contentType:'application/json',body:JSON.stringify({...master,products:[master.products[0],master.products[0]],instrument_count:2})}));
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('masterStatus').textContent.includes('종목 식별 정보 오류'));
    assert.equal(await page.locator('#products tr').count(),0);
    assert.deepEqual(errors,[]);
    console.log('PASS: official count, search, category, empty state, mobile overflow, missing master, duplicate rejection, no legacy fallback');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>server.close());
