const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('legacy.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
const el = id => { if (!elements.has(id)) elements.set(id, {textContent:'',hidden:false}); return elements.get(id); };
const context = vm.createContext({console, clearInterval, document: {
  readyState:'loading', addEventListener(){}, getElementById:el, querySelector:el
}});
vm.runInContext(script, context);
vm.runInContext('updateBriefing=renderNews=render=updateTickerDisplay=startTickerRolling=()=>{}', context);
(async () => {
  context.fetch = async () => ({ok:true,json:async()=>({date:'2026-09-10',items:[]})});
  await vm.runInContext("loadData('2026-09-10')", context);
  assert.equal(el('main').hidden,false);
  let calls=0;
  context.fetch=async()=>{calls++;return {ok:false};};
  await vm.runInContext("loadData('2020-01-01')", context);
  assert.equal(calls,1,'No fallback request allowed');
  assert.equal(el('main').hidden,true,'Stale content must be hidden');
  assert.match(el('dataStatus').textContent,/저장 자료가 없습니다/);
  context.fetch=async()=>({ok:true,json:async()=>({date:'2020-01-02',items:[]})});
  await vm.runInContext("loadData('2020-01-01')",context);
  assert.equal(el('main').hidden,true);
  console.log('PASS: matching date, missing date without fallback, mismatched date');
})().catch(error=>{console.error(error);process.exitCode=1;});
