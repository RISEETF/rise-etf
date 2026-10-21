const {chromium} = require('playwright');
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const assert = require('node:assert/strict');
(async()=>{
const root=fs.mkdtempSync(path.join(os.tmpdir(),'provider-ui-'));
const code=`import sys\nsys.path.insert(0,'tests')\nfrom test_provider_inbox import InboxTests\nfrom pathlib import Path\nt=InboxTests();t.setUp();t.sample();t.run_inbox();Path(sys.argv[1]).write_bytes((t.out/'index.html').read_bytes())\nt.doCleanups()\n`;
const result=spawnSync('python',['-c',code,path.join(root,'index.html')],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
const browser=await chromium.launch({headless:true});try{
const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto('file://'+path.join(root,'index.html'));
assert.equal(await page.locator('#rows tr').count(),1);
await page.getByRole('button',{name:'RISE 테스트',exact:true}).click();
assert.equal(await page.locator('#detail-title').textContent(),'ETF 상세');
assert.ok((await page.locator('#details').textContent()).includes('실부담비율'));
await page.getByRole('checkbox',{name:'RISE 테스트 비교',exact:true}).check();
await page.locator('#compare').click();assert.equal(await page.locator('#details table').count(),1);
await page.locator('#search').fill('no-match');assert.equal(await page.locator('#rows tr').count(),0);
assert.deepEqual(errors,[]);console.log('Private ETF UI interactions PASS');
}finally{await browser.close();fs.rmSync(root,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
