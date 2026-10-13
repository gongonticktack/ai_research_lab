/* Data rendering stays available even if the optional 3D CDN is unavailable. */
const el=id=>document.getElementById(id);
const number=value=>value==null?'—':value.toFixed(1);
let data, viewer;
function render(){
  const runs=data.runs.filter(r=>el('filter').value==='all'||r.kind===el('filter').value);
  el('runs').replaceChildren();el('empty').hidden=runs.length>0;
  for(const r of runs){
    const tr=document.createElement('tr');
    for(const text of [r.run_id,r.kind==='sample'?'サンプル':'実測',r.status,number(r.metrics.latency_p50_ms),number(r.metrics.mpjpe_mm)]){
      const td=document.createElement('td');td.textContent=text;tr.append(td);
    }
    const small=document.createElement('small');small.textContent=r.dataset;tr.children[0].append(small);
    tr.children[1].className=r.kind==='sample'?'badge':'measured';
    if(r.artifacts.length){const b=document.createElement('button');b.textContent='3Dを表示';b.addEventListener('click',()=>loadMesh(r).catch(error=>{el('error').hidden=false;el('error').textContent='メッシュを読み込めません: '+error.message;}));tr.children[0].append(b);}
    el('runs').append(tr);
  }
}
async function loadMesh(run){
  if(!viewer)return;
  const path=run.artifacts[0];
  if(!/^meshes\/[A-Za-z0-9_-]+\.json$/.test(path))throw Error('Invalid mesh path');
  const response=await fetch(path);if(!response.ok)throw Error('Mesh HTTP '+response.status);
  const mesh=await response.json();viewer.show(mesh);
  el('mesh-label').textContent=run.kind==='sample'?'合成サンプル · 人体推定結果ではありません':'実測メッシュ · '+run.run_id;
}
async function start(){
  try{
    const response=await fetch('data/index.json');if(!response.ok)throw Error('HTTP '+response.status);
    data=await response.json();el('measured').textContent=data.measured_count;el('samples').textContent=data.sample_count;
    el('updated').textContent=new Date(data.generated_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo'});
    el('filter').addEventListener('change',render);render();
    el('analysis').textContent=data.measured_count===0?'実測結果はまだありません。モデルと単一人物画像を用意し、手元のGPUで最初のベンチマークを実行してください。サンプルの数値から性能を判断することはできません。':
      data.comparisons.length?data.comparisons.map(c=>`${c.latest}: p50変化 ${c.latency_change_percent}%${c.regression?' / 要確認':''}`).join('\n'):'比較可能な実測ペアはまだありません。';
    try{viewer=await import('./viewer.js');await viewer.init(el('viewport'));el('reset').addEventListener('click',()=>viewer.reset());const run=[...data.runs].reverse().find(r=>r.kind==='measured'&&r.status==='completed'&&r.artifacts.length)||data.runs.find(r=>r.artifacts.length);if(run)await loadMesh(run);}
    catch(error){el('viewport').textContent='3D表示を読み込めません。インターネット/WebGLを確認してください。';el('reset').disabled=true;}
  }catch(error){el('error').hidden=false;el('error').textContent='データを読み込めません: '+error.message;}
}
start();
