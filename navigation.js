'use strict';
(()=>{
 const base=new URL('.',document.currentScript.src),nav=document.createElement('nav');
 nav.setAttribute('aria-label','전체 서비스');nav.style.cssText='display:flex;flex-wrap:wrap;gap:12px;padding:12px 20px;background:#eef3f7;border-bottom:1px solid #d5dfe5;font-size:13px;';
 for(const [label,path] of [['홈','index.html'],['시장 분석','intelligence/index.html#daily'],['금리·신용','intelligence/index.html#gclri'],['자금흐름','intelligence/index.html#flow'],['RISE ETF','etf.html'],['통합 RS','research.html#researchTitle'],['미국 섹터','sectors.html'],['기업 자금','corporate.html'],['상품 연구','intelligence/index.html#product'],['자료 운영','research.html#operationsTitle'],['보고서 보관함','intelligence/index.html#archive']]){
 const a=document.createElement('a');a.textContent=label;a.href=new URL(path,base).href;nav.append(a);
 }
 const header=document.querySelector('header');if(header)header.after(nav);else document.body.prepend(nav);
})();