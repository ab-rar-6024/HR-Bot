STYLE = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#e8eef8;--fg:#0f172a;
  --glass:rgba(255,255,255,.58);--glass2:rgba(255,255,255,.38);--bd:rgba(255,255,255,.65);
  --bd2:rgba(15,23,42,.08);
  --pri:#2563eb;--pri-h:#1d4ed8;--red:#dc2626;--grn:#16a34a;--amb:#d97706;--mut:#475569;
  --sh:0 8px 32px rgba(15,23,42,.10),inset 0 1px 0 rgba(255,255,255,.75);
}
@media (prefers-color-scheme:dark){:root{
  --bg:#060b16;--fg:#f1f5f9;
  --glass:rgba(17,25,40,.62);--glass2:rgba(30,41,59,.45);--bd:rgba(255,255,255,.14);
  --bd2:rgba(255,255,255,.08);
  --pri:#3b82f6;--pri-h:#2563eb;--mut:#94a3b8;
  --sh:0 12px 40px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.12);
}}
*{box-sizing:border-box}
body{
  margin:0;min-height:100vh;background:var(--bg);color:var(--fg);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,sans-serif;
  -webkit-font-smoothing:antialiased;position:relative;overflow-x:hidden;
}
body::before,body::after{
  content:"";position:fixed;z-index:-1;border-radius:50%;filter:blur(80px);pointer-events:none;
  animation:floatOrb 16s ease-in-out infinite alternate;
}
body::before{
  width:520px;height:520px;top:-140px;left:-120px;
  background:radial-gradient(circle,rgba(59,130,246,.38),rgba(16,185,129,.22) 60%,transparent 75%);
}
body::after{
  width:560px;height:560px;bottom:-160px;right:-140px;animation-delay:-8s;
  background:radial-gradient(circle,rgba(139,92,246,.32),rgba(14,165,233,.22) 60%,transparent 75%);
}
@keyframes floatOrb{0%{transform:translate(0,0) scale(1)}100%{transform:translate(40px,30px) scale(1.08)}}
a{color:inherit;text-decoration:none}
.wrap{max-width:1120px;margin:0 auto;padding:24px 20px}
.nav{
  background:var(--glass);backdrop-filter:blur(22px) saturate(180%);-webkit-backdrop-filter:blur(22px) saturate(180%);
  border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:20;
  box-shadow:0 4px 20px rgba(15,23,42,.06);
}
.nav-in{max-width:1120px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:15px;letter-spacing:-.01em;margin-right:auto}
.brand-dot{width:11px;height:11px;border-radius:4px;background:linear-gradient(135deg,#3b82f6,#10b981);display:inline-block;box-shadow:0 0 12px rgba(59,130,246,.6)}
.nav-links{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.nav-link{padding:6px 11px;border-radius:10px;font-size:13px;color:var(--mut);font-weight:500;transition:background .15s,color .15s}
.nav-link:hover{background:var(--glass2);color:var(--fg)}
.card{
  background:var(--glass);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);
  border:1px solid var(--bd);border-radius:18px;padding:24px;margin-bottom:18px;box-shadow:var(--sh);
}
h1{font-size:22px;font-weight:700;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:16px;font-weight:600;margin:0 0 14px;letter-spacing:-.01em}
label{display:block;font-size:11.5px;font-weight:600;color:var(--mut);margin:12px 0 5px;text-transform:uppercase;letter-spacing:.04em}
input,select{
  width:100%;padding:10px 13px;border:1px solid var(--bd);border-radius:11px;
  background:var(--glass2);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  color:var(--fg);font:inherit;transition:border-color .15s,box-shadow .15s,background .15s;
}
input:focus,select:focus{outline:none;border-color:var(--pri);box-shadow:0 0 0 3px rgba(59,130,246,.22);background:var(--glass)}
button{
  padding:10px 18px;border:0;border-radius:11px;
  background:linear-gradient(135deg,var(--pri),#4f46e5);color:#fff;font:inherit;font-weight:600;cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;gap:6px;
  box-shadow:0 4px 14px rgba(37,99,235,.28);transition:transform .12s,box-shadow .15s,opacity .15s;
}
button:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 6px 20px rgba(37,99,235,.38)}
button:active:not(:disabled){transform:translateY(0)}
button.sec{
  background:var(--glass2);color:var(--fg);border:1px solid var(--bd);box-shadow:none;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
}
button.sec:hover:not(:disabled){background:var(--glass);box-shadow:0 4px 12px rgba(15,23,42,.08)}
button.red{background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff;box-shadow:0 4px 14px rgba(220,38,38,.28)}
button.red:hover:not(:disabled){opacity:.95}
button.sm{padding:6px 12px;font-size:12.5px;border-radius:9px}
button:disabled{opacity:.5;cursor:not-allowed;transform:none}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:680px){.row{grid-template-columns:1fr}}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}@media(max-width:680px){.kpis{grid-template-columns:1fr}}
.kpi{
  background:var(--glass);backdrop-filter:blur(20px) saturate(180%);-webkit-backdrop-filter:blur(20px) saturate(180%);
  border:1px solid var(--bd);border-radius:16px;padding:16px 18px;box-shadow:var(--sh);
}
.kpi .v{font-size:24px;font-weight:700;margin-top:4px;letter-spacing:-.02em}
.mut{color:var(--mut);font-size:13px}
.err{color:var(--red);font-size:13.5px;margin:10px 0 0;font-weight:500}
.ok{color:var(--grn);font-size:13.5px;margin:10px 0 0}
.notice{
  background:var(--glass2);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border:1px solid var(--bd);border-left:4px solid var(--pri);border-radius:12px;padding:13px 15px;margin-top:14px;font-size:13.5px;
}
.pill{
  display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600;
  background:var(--glass2);border:1px solid var(--bd);color:var(--fg);white-space:nowrap;
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
}
.pill.g{background:rgba(22,163,74,.16);color:var(--grn);border-color:rgba(22,163,74,.35)}
.pill.r{background:rgba(220,38,38,.16);color:var(--red);border-color:rgba(220,38,38,.35)}
.pill.a{background:rgba(217,119,6,.16);color:var(--amb);border-color:rgba(217,119,6,.35)}
.pill.b{background:rgba(59,130,246,.16);color:var(--pri);border-color:rgba(59,130,246,.35)}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:12px 10px;border-bottom:1px solid var(--bd2);font-size:13.5px;vertical-align:middle}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);font-weight:600}
tr:last-child td{border-bottom:0}
code{background:var(--glass2);border:1px solid var(--bd);padding:2px 7px;border-radius:7px;word-break:break-all;font-size:12.5px}
.actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
</style>"""

JS_COMMON = """
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,opt={}){
  const o={credentials:'same-origin',...opt,headers:{...(opt.body?{'Content-Type':'application/json'}:{}),...(opt.headers||{})}};
  if(opt.body&&typeof opt.body!=='string')o.body=JSON.stringify(opt.body);
  const r=await fetch(path,o);let d=null;try{d=await r.json()}catch(e){}
  if(!r.ok){const m=d&&d.detail?(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail)):('Error '+r.status);const e=new Error(m);e.status=r.status;throw e}
  return d}
async function logout(){try{await api('/api/auth/logout',{method:'POST'})}catch(e){}location='/login'}
const fmt=iso=>new Date(iso).toLocaleString([], {dateStyle:'medium',timeStyle:'short'});
async function copyText(txt,btn){
  try{await navigator.clipboard.writeText(txt);if(btn){const old=btn.textContent;btn.textContent='Copied!';setTimeout(()=>btn.textContent=old,1500)}}
  catch(e){prompt('Copy this:',txt)}
}
function statusBadge(m){
  if(m.cancelled) return '<span class="pill r">Cancelled</span>';
  const now=Date.now(), st=new Date(m.start_utc).getTime(), en=st+(m.duration_min+60)*60000, early=st-15*60000;
  if(m.active_roles&&m.active_roles.length) return '<span class="pill g">&#9679; Live ('+esc(m.active_roles.join(', '))+')</span>';
  if(now>=early && now<=en) return '<span class="pill b">Ready to join</span>';
  if(now<early) return '<span class="pill a">Upcoming</span>';
  return '<span class="pill">Ended</span>';
}
"""

LOGIN = f"""<!doctype html><html lang="en"><head><title>Sign in - ProofyX VerifyOps</title>{STYLE}</head><body>
<div class="wrap" style="max-width:440px;margin-top:8vh">
 <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:18px;font-weight:700;font-size:17px">
  <span class="brand-dot"></span> ProofyX VerifyOps
 </div>
 <div class="card">
  <h1>Interview portal</h1>
  <p class="mut" id="sub">HR and candidates sign in here.</p>
  <div id="joinHint" class="notice" hidden>You are signing in to join a live interview room.</div>
  <form id="f">
   <label for="e">Email</label><input id="e" type="email" autocomplete="username" placeholder="you@company.com" required>
   <label for="p">Password</label><input id="p" type="password" autocomplete="current-password" placeholder="Enter your password" required>
   <div id="np" hidden><label for="n">Choose a new password (10+ characters)</label><input id="n" type="password" autocomplete="new-password" minlength="10" placeholder="At least 10 characters"></div>
   <p id="m" class="err" role="alert"></p>
   <button id="b" style="width:100%;margin-top:14px">Sign in</button>
  </form>
 </div>
</div>
<script>{JS_COMMON}
const next=new URLSearchParams(location.search).get('next');
const safeNext=next&&next.startsWith('/')&&!next.startsWith('//')?next:null;
if(safeNext&&safeNext.startsWith('/meet/')){{$('joinHint').hidden=false}}
let stage='login';
$('f').addEventListener('submit',async ev=>{{ev.preventDefault();$('m').textContent='';$('b').disabled=true;
 try{{
  if(stage==='login'){{
   const r=await api('/api/auth/login',{{method:'POST',body:{{email:$('e').value,password:$('p').value}}}});
   if(r.must_change){{stage='change';$('np').hidden=false;$('n').required=true;$('b').textContent='Set password & continue';$('m').className='mut';$('m').textContent='First sign-in: please set your own password to continue.';$('n').focus();return}}
   location=safeNext||(r.role==='hr'?'/hr':'/my')
  }}else{{
   await api('/api/auth/change-password',{{method:'POST',body:{{new_password:$('n').value}}}});
   const me=await api('/api/me');location=safeNext||(me.role==='hr'?'/hr':'/my')
  }}
 }}catch(e){{$('m').className='err';$('m').textContent=e.message}}finally{{$('b').disabled=false}}}});
</script></body></html>"""

HR = f"""<!doctype html><html lang="en"><head><title>HR Dashboard - ProofyX VerifyOps</title>{STYLE}</head><body>
<div class="nav"><div class="nav-in">
 <div class="brand"><span class="brand-dot"></span> ProofyX VerifyOps <span class="pill b">HR</span></div>
 <div class="nav-links">
  <a class="nav-link" href="/verify">ML Gate</a>
  <a class="nav-link" href="/review">Review Queue</a>
  <a class="nav-link" href="/docs" target="_blank">API Docs</a>
  <span class="mut" id="meName"></span>
  <button class="sec sm" onclick="logout()">Sign out</button>
 </div>
</div></div>
<div class="wrap">
 <div style="margin-bottom:18px"><h1>Interview Operations</h1><p class="mut">Schedule interviews or launch an instant real-time session.</p></div>
 <div class="kpis">
  <div class="kpi"><div class="mut">Active / Live Now</div><div class="v" id="kLive">0</div></div>
  <div class="kpi"><div class="mut">Upcoming</div><div class="v" id="kUp">0</div></div>
  <div class="kpi"><div class="mut">Total Scheduled</div><div class="v" id="kTot">0</div></div>
 </div>
 <div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:6px">
   <h2 style="margin:0">Create Meeting</h2>
   <label style="display:inline-flex;align-items:center;gap:8px;margin:0;text-transform:none;font-size:13px;color:var(--fg);cursor:pointer">
    <input id="nowToggle" type="checkbox" checked style="width:auto"> Start immediately (real-time)
   </label>
  </div>
  <form id="f">
   <div class="row">
    <div><label for="t">Interview Title</label><input id="t" required maxlength="120" placeholder="Backend Engineer — Round 1"></div>
    <div><label for="dt">Date &amp; Time (local)</label><input id="dt" type="datetime-local" required></div>
   </div>
   <div class="row">
    <div><label for="cn">Candidate Name</label><input id="cn" required maxlength="120" placeholder="Ravi Kumar"></div>
    <div><label for="ce">Candidate Email</label><input id="ce" type="email" required placeholder="ravi@example.com"></div>
   </div>
   <div class="row" style="align-items:end">
    <div><label for="du">Duration</label><select id="du"><option value="30">30 minutes</option><option value="45">45 minutes</option><option value="60">60 minutes</option><option value="90">90 minutes</option></select></div>
    <div><button id="createBtn" style="width:100%">Create meeting &amp; invite link</button></div>
   </div>
   <div id="m" role="alert"></div>
  </form>
 </div>
 <div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
   <h2 style="margin:0">Meetings</h2>
   <span class="mut">Auto-updates every 10s</span>
  </div>
  <div style="overflow-x:auto">
   <table><thead><tr><th>When</th><th>Candidate</th><th>Title</th><th>Status</th><th style="text-align:right">Actions</th></tr></thead><tbody id="l"></tbody></table>
  </div>
 </div>
</div>
<script>{JS_COMMON}
function setLocalNow(){{
  const d=new Date(Date.now()-new Date().getTimezoneOffset()*60000);
  $('dt').value=d.toISOString().slice(0,16);
}}
setLocalNow();
$('nowToggle').addEventListener('change',()=>{{if($('nowToggle').checked)setLocalNow()}});
(async()=>{{try{{const u=await api('/api/me');$('meName').textContent=u.name}}catch(e){{}}}})();

async function load(){{
 try{{
  const ms=await api('/api/meetings');
  const now=Date.now();
  let live=0,up=0;
  ms.forEach(m=>{{
   if(m.cancelled)return;
   const st=new Date(m.start_utc).getTime(),en=st+(m.duration_min+60)*60000,early=st-15*60000;
   if((m.active_roles&&m.active_roles.length)||(now>=early&&now<=en))live++;
   else if(now<early)up++;
  }});
  $('kLive').textContent=live;$('kUp').textContent=up;$('kTot').textContent=ms.length;
  $('l').innerHTML=ms.map(m=>`<tr>
   <td><strong>${{esc(fmt(m.start_utc))}}</strong><div class="mut">${{m.duration_min}} min</div></td>
   <td><strong>${{esc(m.candidate_name)}}</strong><div class="mut">${{esc(m.candidate_email)}}</div></td>
   <td>${{esc(m.title)}}</td>
   <td>${{statusBadge(m)}}</td>
   <td><div class="actions">${{m.cancelled?'':`<button class="sm" data-join="${{esc(m.id)}}">Join Room</button><button class="sec sm" data-copy="${{esc(m.link)}}">Copy Link</button><button class="sec sm red" data-cancel="${{esc(m.id)}}" style="border-color:transparent">Cancel</button>`}}</div></td>
  </tr>`).join('')||'<tr><td colspan=5 class="mut">No meetings yet. Create one above.</td></tr>';
 }}catch(e){{if(e.status===401)location='/login';else $('l').innerHTML='<tr><td colspan=5 class="err">'+esc(e.message)+'</td></tr>'}}}}

$('l').addEventListener('click',async ev=>{{const b=ev.target.closest('button');if(!b)return;
 if(b.dataset.join)location='/meet/'+b.dataset.join;
 if(b.dataset.copy)copyText(b.dataset.copy,b);
 if(b.dataset.cancel&&confirm('Cancel this meeting?')){{await api('/api/meetings/'+b.dataset.cancel,{{method:'DELETE'}});load()}}}});

$('f').addEventListener('submit',async ev=>{{ev.preventDefault();const m=$('m');m.className='';m.innerHTML='';$('createBtn').disabled=true;
 if($('nowToggle').checked)setLocalNow();
 try{{
  const ce=$('ce').value,cn=$('cn').value,ti=$('t').value;
  const r=await api('/api/meetings',{{method:'POST',body:{{title:ti,candidate_name:cn,candidate_email:ce,start_utc:new Date($('dt').value).toISOString(),duration_min:+$('du').value}}}});
  const inviteText=`Interview: ${{ti}}\\nLink: ${{r.link}}\\nEmail: ${{ce}}`+(r.temp_password?`\\nTemporary Password: ${{r.temp_password}}`:'');
  m.className='notice';
  m.innerHTML=`<div><strong>Meeting ready!</strong> ${{r.emailed?'Invitation emailed to candidate.':esc(r.note||'')}}</div>
   <div style="margin-top:8px">Link: <code>${{esc(r.link)}}</code></div>`
   +(r.temp_password?`<div style="margin-top:4px">Temp password (shown once): <code>${{esc(r.temp_password)}}</code></div>`:'')
   +`<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
    <button type="button" class="sm" onclick="location='/meet/${{esc(r.id)}}'">Open Room Now</button>
    <button type="button" class="sec sm" id="cpLinkBtn">Copy Link</button>
    <button type="button" class="sec sm" id="cpInvBtn">Copy Full Invite</button>
   </div>`;
  $('cpLinkBtn').onclick=()=>copyText(r.link,$('cpLinkBtn'));
  $('cpInvBtn').onclick=()=>copyText(inviteText,$('cpInvBtn'));
  ev.target.reset();$('nowToggle').checked=true;setLocalNow();load();
 }}catch(e){{m.className='err';m.textContent=e.message}}finally{{$('createBtn').disabled=false}}}});
load();setInterval(load,10000);
</script></body></html>"""

MY = f"""<!doctype html><html lang="en"><head><title>My Interviews - ProofyX VerifyOps</title>{STYLE}</head><body>
<div class="nav"><div class="nav-in">
 <div class="brand"><span class="brand-dot"></span> ProofyX VerifyOps <span class="pill">Candidate</span></div>
 <div class="nav-links">
  <span class="mut" id="meName"></span>
  <button class="sec sm" onclick="logout()">Sign out</button>
 </div>
</div></div>
<div class="wrap" style="max-width:820px">
 <div style="margin-bottom:18px"><h1>My interviews</h1><p class="mut">Your scheduled and live interview sessions.</p></div>
 <div id="list"></div>
</div>
<script>{JS_COMMON}
(async()=>{{try{{const u=await api('/api/me');$('meName').textContent=u.name}}catch(e){{}}}})();
async function load(){{
 try{{
  const ms=(await api('/api/meetings')).filter(m=>!m.cancelled);
  $('list').innerHTML=ms.length?ms.map(m=>`<div class="card" style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
   <div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
     <strong style="font-size:16px">${{esc(m.title)}}</strong>${{statusBadge(m)}}
    </div>
    <div class="mut">${{esc(fmt(m.start_utc))}} &middot; ${{m.duration_min}} min &middot; with ${{esc(m.hr_name)}}</div>
   </div>
   <a href="/meet/${{esc(m.id)}}"><button>Join Interview</button></a>
  </div>`).join(''):'<div class="card mut">No interviews scheduled yet.</div>';
 }}catch(e){{if(e.status===401)location='/login'}}
}}
load();setInterval(load,10000);
</script></body></html>"""

ROOM = f"""<!doctype html><html lang="en"><head><title>Interview Room - ProofyX VerifyOps</title>{STYLE}
<style>
.room-grid{{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}}
@media(max-width:960px){{.room-grid{{grid-template-columns:1fr}}}}
.stage{{background:rgba(2,6,23,.85);border-radius:18px;overflow:hidden;border:1px solid var(--bd);position:relative;box-shadow:var(--sh)}}
video{{width:100%;background:transparent;display:block;aspect-ratio:16/9;object-fit:contain}}
.cam-box{{border-radius:14px;overflow:hidden;border:1px solid var(--bd);background:rgba(2,6,23,.85);margin-bottom:10px;box-shadow:var(--sh)}}
.cam-box video{{aspect-ratio:16/10;object-fit:cover}}
.lbl{{font-size:12px;font-weight:600;color:var(--mut);margin-bottom:4px;display:flex;justify-content:space-between}}
.banner{{position:sticky;top:0;z-index:30;padding:10px 16px;background:rgba(220,38,38,.9);backdrop-filter:blur(12px);color:#fff;font-weight:600;text-align:center;display:none;font-size:13.5px}}
.controls{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;padding:14px;background:var(--glass);backdrop-filter:blur(22px) saturate(180%);-webkit-backdrop-filter:blur(22px) saturate(180%);border:1px solid var(--bd);border-radius:16px;margin-top:14px;box-shadow:var(--sh)}}
.feed{{height:220px;overflow-y:auto;background:var(--glass2);border:1px solid var(--bd);border-radius:12px;padding:10px;font-size:12.5px;display:flex;flex-direction:column;gap:6px}}
.msg-sys{{color:var(--mut)}}
.msg-alert{{color:var(--red);font-weight:600}}
.msg-chat{{background:var(--glass);border:1px solid var(--bd);padding:7px 10px;border-radius:10px}}
.chat-row{{display:flex;gap:6px;margin-top:8px}}
ul.consent li{{margin:8px 0}}
</style></head><body>
<div id="banner" class="banner" role="status">&#9679; Your entire screen is being shared live with the interviewer</div>
<div class="nav"><div class="nav-in">
 <div class="brand"><span class="brand-dot"></span> <span id="title">Interview Room</span></div>
 <div class="nav-links">
  <span id="st" class="pill">connecting</span>
  <button class="sec sm" onclick="leave()">Leave</button>
 </div>
</div></div>
<div class="wrap">
 <div id="err" class="err" role="alert" style="margin-bottom:12px"></div>

 <div id="desktopOnly" class="card" style="max-width:560px;margin:28px auto;text-align:center" hidden>
  <div style="font-size:38px;margin-bottom:8px">&#128187;</div>
  <h1>Laptop or Desktop Required</h1>
  <p class="mut" style="font-size:14px;margin:10px 0 18px">
   This interview requires live camera, microphone, and <b>entire-screen sharing</b>, which are not supported on mobile phones or in-app browsers.
   Please open this interview link on a <b>laptop or desktop computer</b> (Chrome, Edge, or Firefox).
  </p>
  <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
   <button type="button" id="copyDeskBtn">Copy Interview Link</button>
   <a href="/my"><button type="button" class="sec">Back to My Interviews</button></a>
  </div>
 </div>

 <div id="consent" class="card" style="max-width:680px;margin:20px auto" hidden>
  <h2>Before you join</h2>
  <p>This interview is conducted with the following, and nothing else:</p>
  <ul class="consent">
   <li><b>Camera and microphone</b>, seen and heard live by <span id="who"></span>.</li>
   <li><b>Your entire screen</b> (all windows and notifications), shown live to the interviewer so they can see how you work.</li>
   <li>The session is <b>not recorded by this page</b>. Connection events (joined, screen sharing started/stopped) are logged for the interviewer.</li>
  </ul>
  <p class="mut">Close anything private (messages, email, banking) before you start. You can stop sharing and leave at any time; the interviewer will be told sharing has stopped.</p>
  <label style="display:flex;gap:10px;align-items:flex-start;color:var(--fg);text-transform:none;font-size:14px;font-weight:500;cursor:pointer">
   <input id="agree" type="checkbox" style="width:auto;margin-top:3px">I understand and agree to share my camera, microphone and entire screen for this interview.
  </label>
  <div style="margin-top:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
   <button id="join" disabled>Agree &amp; join</button>
   <span class="mut">When asked what to share, choose <b>Entire screen</b>.</span>
  </div>
 </div>

 <div id="room" hidden>
  <div class="room-grid">
   <div>
    <div class="lbl"><span id="mainlbl">Main Stage</span><span class="mut" id="mainHint"></span></div>
    <div class="stage"><video id="main" autoplay playsinline></video></div>
    <div class="controls">
     <button id="micBtn" class="sec">Mic: On</button>
     <button id="camBtn" class="sec">Camera: On</button>
     <button id="shareBtn" class="sec" hidden>Re-share Entire Screen</button>
     <button id="mlBtn" class="sec" hidden>Check Face (ML)</button>
     <button id="permBtn" class="sec" hidden>Search: Locked</button>
     <button class="red" onclick="leave()">End Call</button>
    </div>
    <div id="searchCard" class="card" style="margin-top:14px;padding:16px" hidden>
     <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:8px">
      <h2 style="margin:0;font-size:15px">In-App Web Search</h2>
      <span id="searchLockPill" class="pill a">Locked by interviewer</span>
     </div>
     <form id="searchForm" class="chat-row" style="margin-top:0">
      <input id="searchIn" placeholder="Ask interviewer for search permission first..." disabled maxlength="200">
      <button id="searchGo" class="sm" type="submit" disabled>Search</button>
     </form>
     <div id="searchRes" style="margin-top:10px;max-height:260px;overflow-y:auto;display:flex;flex-direction:column;gap:8px"></div>
    </div>
   </div>
   <div>
    <div id="remoteCamWrap" hidden>
     <div class="lbl"><span>Candidate Camera</span></div>
     <div class="cam-box"><video id="cam" autoplay playsinline></video></div>
    </div>
    <div class="lbl"><span>You (Local Preview)</span></div>
    <div class="cam-box"><video id="self" autoplay playsinline muted style="transform:scaleX(-1)"></video></div>
    <div class="card" style="padding:14px;margin-bottom:0">
     <h2 style="font-size:14px;margin-bottom:8px">Live Chat &amp; Activity</h2>
     <div id="log" class="feed"></div>
     <form id="chatForm" class="chat-row">
      <input id="chatIn" placeholder="Send a message..." maxlength="500" autocomplete="off">
      <button class="sm" type="submit">Send</button>
     </form>
    </div>
   </div>
  </div>
 </div>
</div>

<script>{JS_COMMON}
const mid=location.pathname.split('/').pop();
let info,ws,pc,local={{}},screenStream=null,leaving=false,micOn=true,camOn=true,searchAllowed=false;
const setSt=(t,c)=>{{$('st').textContent=t;$('st').className='pill '+(c||'')}};
function addFeed(txt,cls='msg-sys',ts=null){{
  const d=document.createElement('div');d.className=cls;
  const t=ts?new Date(ts).toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}}):new Date().toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}});
  d.textContent=t+'  '+txt;$('log').appendChild(d);$('log').scrollTop=$('log').scrollHeight;
}}
function fail(m){{$('err').textContent=m;setSt('stopped','r')}}

(async()=>{{
 try{{info=await api('/api/meetings/'+mid+'/info')}}catch(e){{if(e.status===401)location='/login?next=/meet/'+mid;else fail(e.status===404?'Meeting not found for your account.':e.message);return}}
 $('title').textContent=info.title;
 if(info.must_change){{location='/login?next=/meet/'+mid;return}}
 if(info.join_error){{fail(info.join_error);return}}
 if(info.role==='candidate'){{
  const isMobile=/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  const canScreen=Boolean(navigator.mediaDevices&&typeof navigator.mediaDevices.getDisplayMedia==='function');
  if(isMobile||!canScreen){{
   $('desktopOnly').hidden=false;
   $('copyDeskBtn').onclick=()=>copyText(location.href,$('copyDeskBtn'));
   setSt('laptop required','a');
   return;
  }}
  $('who').textContent=info.other;$('consent').hidden=false;setSt('waiting for consent','a');
 }}
 else{{
  $('room').hidden=false;$('mainlbl').textContent="Candidate's Screen";$('remoteCamWrap').hidden=false;
  $('mlBtn').hidden=false;$('permBtn').hidden=false;
  try{{const evs=await api('/api/meetings/'+mid+'/events');evs.slice(-15).forEach(e=>addFeed(e.name+(e.detail?' ('+e.detail+')':''),'msg-sys',e.created_utc))}}catch(e){{}}
  await start();
 }}
}})();

$('agree').addEventListener('change',()=>$('join').disabled=!$('agree').checked);
$('join').addEventListener('click',()=>start());

$('micBtn').addEventListener('click',()=>{{
  if(!local.cam)return;micOn=!micOn;
  local.cam.getAudioTracks().forEach(t=>t.enabled=micOn);
  $('micBtn').textContent=micOn?'Mic: On':'Mic: Muted';
  $('micBtn').className=micOn?'sec':'red';
}});
$('camBtn').addEventListener('click',()=>{{
  if(!local.cam)return;camOn=!camOn;
  local.cam.getVideoTracks().forEach(t=>t.enabled=camOn);
  $('camBtn').textContent=camOn?'Camera: On':'Camera: Off';
  $('camBtn').className=camOn?'sec':'red';
}});
$('shareBtn').addEventListener('click',async()=>{{
  try{{await acquireScreen();$('banner').textContent='● Your entire screen is being shared live with the interviewer';$('banner').style.background='var(--red)';sendEvent('screen_started');if(pc)await offer();}}
  catch(e){{$('err').textContent=e.message}}
}});
$('chatForm').addEventListener('submit',ev=>{{
  ev.preventDefault();const v=$('chatIn').value.trim();if(!v||!ws||ws.readyState!==1)return;
  ws.send(JSON.stringify({{type:'chat',text:v}}));
  addFeed('You: '+v,'msg-chat');$('chatIn').value='';
}});
$('permBtn').addEventListener('click',()=>{{
  if(!ws||ws.readyState!==1)return;
  searchAllowed=!searchAllowed;
  ws.send(JSON.stringify({{type:'permission',allow_search:searchAllowed}}));
  $('permBtn').textContent=searchAllowed?'Search: Allowed':'Search: Locked';
  $('permBtn').className=searchAllowed?'':'sec';
  addFeed(searchAllowed?'You unlocked in-app search for candidate':'You locked in-app search for candidate','msg-sys');
}});
$('mlBtn').addEventListener('click',async()=>{{
  const v=$('cam');if(!v||!v.videoWidth){{addFeed('Candidate camera not ready yet','msg-alert');return}}
  $('mlBtn').disabled=true;
  try{{
   const cv=document.createElement('canvas');cv.width=v.videoWidth;cv.height=v.videoHeight;
   cv.getContext('2d').drawImage(v,0,0);
   const blob=await new Promise(res=>cv.toBlob(res,'image/jpeg',0.9));
   const fd=new FormData();fd.set('file',blob,'snapshot.jpg');
   const r=await fetch('/api/meetings/'+mid+'/verify-snapshot',{{method:'POST',credentials:'same-origin',body:fd}});
   const d=await r.json();if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));
   const pct=d.fake_prob!==null?Math.round(d.fake_prob*1000)/10:null;
   const msg=pct!==null?`Face ML: ${{pct}}% fake (${{pct>=50?'SUSPICIOUS':'authentic'}}) · ELA ${{d.ela_score}}`:'No ML model loaded';
   addFeed(msg,pct!==null&&pct>=50?'msg-alert':'msg-sys');
  }}catch(e){{addFeed('ML check failed: '+e.message,'msg-alert')}}finally{{$('mlBtn').disabled=false}}
}});
$('searchForm').addEventListener('submit',async ev=>{{
  ev.preventDefault();const q=$('searchIn').value.trim();if(!q||!searchAllowed)return;
  $('searchGo').disabled=true;$('searchRes').innerHTML='<div class="mut">Searching...</div>';
  try{{
   const d=await api('/api/meet/search?q='+encodeURIComponent(q));
   $('searchRes').innerHTML=(d.results||[]).length?d.results.map(x=>`<div class="msg-chat"><div style="font-weight:600">${{esc(x.title)}}</div><div class="mut" style="font-size:11.5px;word-break:break-all">${{esc(x.url)}}</div><div style="margin-top:3px">${{esc(x.snippet)}}</div></div>`).join(''):'<div class="mut">No results found.</div>';
  }}catch(e){{$('searchRes').innerHTML='<div class="err">'+esc(e.message)+'</div>'}}finally{{$('searchGo').disabled=!searchAllowed}}
}});

async function acquireScreen(){{
 for(let attempt=0;attempt<3;attempt++){{
  let s;
  try{{s=await navigator.mediaDevices.getDisplayMedia({{video:{{displaySurface:'monitor'}},audio:false}})}}
  catch(e){{throw new Error('Screen sharing is required for this interview. '+e.message)}}
  const t=s.getVideoTracks()[0],surf=(t.getSettings()||{{}}).displaySurface;
  if(surf&&surf!=='monitor'){{s.getTracks().forEach(x=>x.stop());sendEvent('screen_not_entire',surf);$('err').textContent='Please choose "Entire screen", not a window or tab, then try again.';continue}}
  if(screenStream)screenStream.getTracks().forEach(x=>x.stop());
  $('err').textContent='';screenStream=s;
  t.addEventListener('ended',()=>{{sendEvent('screen_stopped');$('banner').textContent='Screen sharing stopped. Click "Re-share Entire Screen" to continue.';$('banner').style.display='block';setSt('screen stopped','r');$('shareBtn').hidden=false}});
  return;
 }}
 throw new Error('Entire-screen sharing is required to join.');
}}

async function getMedia(){{
 try{{local.cam=await navigator.mediaDevices.getUserMedia({{video:{{width:1280,height:720}},audio:{{echoCancellation:true}}}})}}
 catch(e){{throw new Error('Camera/microphone permission is required: '+e.message)}}
 $('self').srcObject=local.cam;
 if(info.role!=='candidate')return;
 await acquireScreen();
}}

function sendEvent(name,detail){{if(ws&&ws.readyState===1)ws.send(JSON.stringify({{type:'event',name,detail:detail||''}}))}}

async function start(){{
 $('err').textContent='';$('join').disabled=true;
 try{{await getMedia()}}catch(e){{$('err').textContent=e.message;$('join').disabled=false;return}}
 if(info.role==='candidate'){{
  $('consent').hidden=true;$('room').hidden=false;$('mainlbl').textContent=info.other;
  $('banner').style.display='block';$('shareBtn').hidden=false;$('searchCard').hidden=false;
  document.addEventListener('visibilitychange',()=>{{if(!leaving)sendEvent(document.hidden?'tab_left':'tab_returned')}});
 }}
 connect()
}}

function connect(){{
 ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/meet/'+mid);
 ws.onopen=()=>{{setSt('waiting for '+info.other,'a');if(info.role==='candidate'){{sendEvent('consent_given');sendEvent('screen_started')}}}};
 ws.onclose=ev=>{{if(!leaving){{
  if(ev.code===4000)fail('Opened in another tab.');
  else if(ev.code===4401||ev.code===4403)fail('Not allowed to join this meeting.');
  else{{setSt('reconnecting...','a');setTimeout(()=>{{if(!leaving)connect()}},2000)}}
 }}}};
 ws.onmessage=async ev=>{{const m=JSON.parse(ev.data);
  if(m.type==='peers'&&m.present.includes('hr')&&info.role==='candidate')offer();
  else if(m.type==='peer_joined'&&m.role==='hr'&&info.role==='candidate')offer();
  else if(m.type==='peer_joined'){{addFeed(info.other+' joined the room','msg-sys')}}
  else if(m.type==='peer_left'){{setSt('waiting for '+info.other,'a');addFeed(info.other+' left the room','msg-alert')}}
  else if(m.type==='offer'&&info.role==='hr')answer(m);
  else if(m.type==='answer'&&pc)await pc.setRemoteDescription(m.sdp);
  else if(m.type==='ice'&&pc&&m.candidate)try{{await pc.addIceCandidate(m.candidate)}}catch(e){{}}
  else if(m.type==='chat'){{addFeed(m.sender+': '+m.text,'msg-chat',m.at)}}
  else if(m.type==='permission'&&info.role==='candidate'){{
   searchAllowed=!!m.allow_search;
   $('searchIn').disabled=!searchAllowed;$('searchGo').disabled=!searchAllowed;
   $('searchIn').placeholder=searchAllowed?'Search web inside this interview room...':'Ask interviewer for search permission first...';
   $('searchLockPill').textContent=searchAllowed?'Allowed by interviewer':'Locked by interviewer';
   $('searchLockPill').className='pill '+(searchAllowed?'g':'a');
   addFeed(searchAllowed?'Interviewer enabled in-app search':'Interviewer locked in-app search','msg-sys');
  }}
  else if(m.type==='event'&&info.role==='hr'){{
   const map={{consent_given:'Candidate gave consent',screen_started:'Screen sharing started',screen_stopped:'Screen sharing STOPPED',screen_not_entire:'Candidate tried to share a window/tab, not the entire screen',camera_stopped:'Camera stopped',tab_left:'Candidate switched away from interview tab!',tab_returned:'Candidate returned to interview tab'}};
   addFeed(map[m.name]||m.name,(m.name==='screen_stopped'||m.name==='screen_not_entire'||m.name==='tab_left')?'msg-alert':'msg-sys',m.at);
  }}
 }};
}}

function newPc(){{
 if(pc)pc.close();
 pc=new RTCPeerConnection({{iceServers:info.iceServers}});
 pc.onicecandidate=e=>{{if(e.candidate&&ws&&ws.readyState===1)ws.send(JSON.stringify({{type:'ice',candidate:e.candidate}}))}};
 pc.onconnectionstatechange=()=>{{const s=pc.connectionState;if(s==='connected')setSt('live','g');else if(s==='failed')setSt('connection failed','r')}};
 return pc}}

async function offer(){{
 newPc();
 local.cam.getTracks().forEach(t=>pc.addTrack(t,local.cam));
 if(screenStream)screenStream.getTracks().forEach(t=>pc.addTrack(t,screenStream));
 pc.ontrack=e=>{{$('main').srcObject=e.streams[0]}};
 const o=await pc.createOffer();await pc.setLocalDescription(o);
 ws.send(JSON.stringify({{type:'offer',sdp:pc.localDescription,screenStreamId:screenStream?screenStream.id:null}}))
}}

async function answer(m){{
 newPc();
 pc.ontrack=e=>{{const s=e.streams[0];if(!s)return;
  if(s.id===m.screenStreamId){{$('main').srcObject=s}}else{{$('cam').srcObject=s}}}};
 await pc.setRemoteDescription(m.sdp);
 local.cam.getTracks().forEach(t=>pc.addTrack(t,local.cam));
 const a=await pc.createAnswer();await pc.setLocalDescription(a);
 ws.send(JSON.stringify({{type:'answer',sdp:pc.localDescription}}))
}}

function leave(){{leaving=true;try{{ws&&ws.send(JSON.stringify({{type:'bye'}}))}}catch(e){{}}
 [local.cam,screenStream].forEach(s=>s&&s.getTracks().forEach(t=>t.stop()));if(pc)pc.close();if(ws)ws.close();
 location=info&&info.role==='hr'?'/hr':'/my'}}
window.addEventListener('beforeunload',()=>{{[local.cam,screenStream].forEach(s=>s&&s.getTracks().forEach(t=>t.stop()))}});
</script></body></html>"""
