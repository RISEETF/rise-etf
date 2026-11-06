// A session entry screen for public Pages content, not server-side authentication.
(() => {
  const key='rise-etf:entry:v1';
  function unlock(){document.documentElement.removeAttribute('data-rise-entry');}
  try { if(sessionStorage.getItem(key)==='open'){unlock();return;} } catch {}
  const gate=document.createElement('section');gate.id='rise-entry';
  gate.setAttribute('aria-labelledby','rise-entry-title');
  gate.innerHTML='<form><small>RISE Intelligence</small><h1 id="rise-entry-title">포털 입장</h1><label for="rise-entry-password">비밀번호</label><input id="rise-entry-password" type="password" autocomplete="current-password" required><p role="alert"></p><button type="submit">입장하기</button></form>';
  document.body.append(gate);
  const input=gate.querySelector('input'),error=gate.querySelector('[role=alert]');
  input.focus();
  gate.querySelector('form').addEventListener('submit',async event=>{
    event.preventDefault();
    try {
      const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(input.value));
      const digest=Array.from(new Uint8Array(bytes),n=>n.toString(16).padStart(2,'0')).join('');
      if(digest!=='dbfbe1cd2ee1f49a02efb08eea36506d5d46e8a66d7175f118589f212ebcf897'){
        error.textContent='비밀번호를 다시 확인해 주세요.';input.select();return;
      }
      try {sessionStorage.setItem(key,'open');} catch {}
      gate.remove();unlock();
    } catch {error.textContent='입장 확인이 되지 않았습니다. HTTPS로 다시 열어 주세요.';}
  });
})();
