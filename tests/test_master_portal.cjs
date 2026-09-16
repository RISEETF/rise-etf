const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const master = JSON.parse(fs.readFileSync(path.join(root, 'data/master/latest.json')));
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
    assert.equal(await page.locator('#products tr').count(),master.instrument_count);
    await page.waitForFunction(()=>document.querySelectorAll('#seriesRows tr').length===3);
    assert.match(await page.locator('#seriesStatus').textContent(),/RS 계산 보류/);
    await page.locator('#search').fill(master.products[0].code);
    assert.equal(await page.locator('#products tr').count(),1);
    await page.locator('#search').fill('NO_MATCH_999');
    assert.equal(await page.locator('#products tr').count(),0);
    assert.equal(await page.locator('#empty').isVisible(),true);
    await page.locator('#reset').click();
    const category=master.products[0].primary_category;
    await page.locator('#category').selectOption(category);
    assert.equal(await page.locator('#products tr').count(),master.products.filter(p=>p.primary_category===category).length);
    await page.locator('#reset').click();
    await page.screenshot({path:'/tmp/rise-master-desktop.png'});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'/tmp/rise-master-mobile.png'});
    let legacyRequests=0;
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
