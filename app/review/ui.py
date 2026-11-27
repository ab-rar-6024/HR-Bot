PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProofyX Review Queue</title>
<style>
:root{--bg:#f6f7f9;--fg:#14171a;--card:#fff;--bd:#d9dde3;--red:#b42318;--amb:#b26a00;--grn:#1a7f37}
@media (prefers-color-scheme:dark){:root{--bg:#0f1216;--fg:#e8eaed;--card:#181c22;--bd:#2c323b}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px system-ui,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--bd);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0;flex:1}input{padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--card);color:var(--fg)}
main{padding:16px 20px;display:grid;gap:14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.card{grid-template-columns:1fr}}
img{max-width:100%;border-radius:6px;border:1px solid var(--bd)}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600;color:#fff}
.BLOCK{background:var(--red)}.REVIEW{background:var(--amb)}
.flag{margin:4px 0;font-size:13px}.high{color:var(--red)}.medium{color:var(--amb)}
button{padding:8px 14px;border-radius:6px;border:0;color:#fff;font-weight:600;cursor:pointer;margin-right:8px}
.f{background:var(--red)}.a{background:var(--grn)}
.cap{font-size:12px;opacity:.7}
</style></head><body>
<header><h1>Review queue</h1><input id="key" type="password" placeholder="API key"><input id="who" placeholder="Reviewer name"><button style="background:#2a5bd7" onclick="load()">Load</button><span id="n" class="cap"></span></header>
<main id="list"></main>
<script>
const $=id=>document.getElementById(id);
const H=()=>({'X-API-Key':$('key').value});
try{$('key').value=sessionStorage.getItem('k')||'';$('who').value=sessionStorage.getItem('w')||''}catch(e){}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function img(url,el){const r=await fetch(url,{headers:H()});if(r.ok)el.src=URL.createObjectURL(await r.blob())}
async function load(){
  try{sessionStorage.setItem('k',$('key').value);sessionStorage.setItem('w',$('who').value)}catch(e){}
  const r=await fetch('/api/v1/review/queue',{headers:H()});
  if(!r.ok){$('list').textContent='Error '+r.status;return}
  const items=await r.json();$('n').textContent=items.length+' pending';$('list').innerHTML='';
  for(const v of items){
    const d=document.createElement('div');d.className='card';
    const flags=v.forensic_flags.map(f=>`<div class="flag ${esc(f.severity)}"><b>${esc(f.code)}</b> &mdash; ${esc(f.detail)}</div>`).join('')||'<div class="flag">No flags</div>';
    d.innerHTML=`<div><span class="tag ${esc(v.recommended_action)}">${esc(v.recommended_action)}</span>
      <b> trust ${esc(v.trust_score)}</b> <span class="cap">(${esc(v.confidence_band)} confidence)</span>
      <div class="cap">${esc(v.filename)} &middot; entity ${esc(v.context.entity_id)} &middot; dealer ${esc(v.context.dealer_id)}</div>
      <div style="margin:10px 0">${flags}</div>
      <button class="f" data-id="${esc(v.id)}" data-d="fraud">Confirm fraud</button><button class="a" data-id="${esc(v.id)}" data-d="authentic">Mark authentic</button></div>
      <div>${v.gradcam_heatmap_url?`<img alt="forensic heatmap overlay"><div class="cap">Forensic heatmap (${esc(v.heatmap_kind)}) &mdash; a cue, not proof</div>`:'<div class="cap">Document: no image heatmap</div>'}
      ${v.certificate_url?`<div class="cap">Certificate ${esc(v.certificate_sha256).slice(0,16)}&hellip;</div>`:''}</div>`;
    $('list').appendChild(d);
    const im=d.querySelector('img');if(im)img(v.gradcam_heatmap_url,im);
  }
}
$('list').addEventListener('click',async e=>{
  const b=e.target.closest('button[data-id]');if(!b)return;
  const fd=new FormData();fd.set('decision',b.dataset.d);fd.set('reviewer',$('who').value||'unknown');
  const r=await fetch('/api/v1/review/'+b.dataset.id,{method:'POST',headers:H(),body:fd});
  if(r.ok)b.closest('.card').remove();else alert('Failed: '+r.status);
});
</script></body></html>"""
