"""Loopback-only GPU gateway. Images/results remain in private local directories."""
import io
import os
import subprocess
import threading
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'private-data' / 'studio'
MODELS = {'triposr': ('TripoSR', 'TripoSR'), 'sf3d': ('Stable Fast 3D', 'stable-fast-3d')}
app = FastAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])
ORIGINS = ['http://127.0.0.1:8765', 'http://localhost:8765', 'https://gongonticktack.github.io']
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
lock = threading.Lock()
jobs = {}

@app.middleware('http')
async def protect_mutations(request: Request, call_next):
    # Prevent cross-site form posts to the loopback installer/GPU service.
    if request.method == 'POST' and request.headers.get('origin') not in ORIGINS:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Open the local AI Studio to run this action.'}, status_code=403)
    return await call_next(request)

def model_paths(model):
    return ROOT / 'vendor' / MODELS[model][1], ROOT / ('.venv-' + model) / 'bin' / 'python'

def installed(model):
    upstream, python = model_paths(model)
    return (upstream / 'run.py').is_file() and python.is_file() and (ROOT / 'vendor' / (model + '.installed')).is_file()

def spawn(work):
    if not lock.acquire(blocking=False):
        raise HTTPException(409, '別の処理が実行中です。完了後に再実行してください。')
    jid = uuid.uuid4().hex
    jobs[jid] = {'id': jid, 'status': 'running'}
    def worker():
        try:
            work(jid)
            jobs[jid]['status'] = 'completed'
        except Exception as exc:
            jobs[jid].update(status='failed', message=str(exc)[-2000:])
        finally:
            lock.release()
    threading.Thread(target=worker, daemon=True).start()
    return {'id': jid, 'status': 'running'}

def command(args, cwd, log, timeout=3600):
    with log.open('w') as stream:
        result = subprocess.run(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError('処理に失敗しました。ローカルログ: ' + str(log) + '\n' + log.read_text(errors='replace')[-1500:])

@app.get('/api/models')
def models():
    return {'models': [{'id': key, 'name': value[0], 'status': 'environment_installed (重み・GPUは実行時確認)' if installed(key) else 'not_installed'} for key, value in MODELS.items()]}

@app.post('/api/install/{model}')
def install(model: str):
    if model not in MODELS:
        raise HTTPException(404, '未知のモデルです')
    def work(jid):
        PRIVATE.mkdir(parents=True, exist_ok=True)
        jobs[jid]['message'] = '環境をインストール中（数分以上かかる場合があります）'
        command(['bash', str(ROOT / 'scripts' / 'install-model.sh'), model], ROOT, PRIVATE / (jid + '.log'), timeout=7200)
        jobs[jid]['message'] = '環境導入完了。重みは初回生成時に取得します。SF3Dは認証が必要です。'
    return spawn(work)

@app.post('/api/generate/{model}')
async def generate(model: str, image: UploadFile):
    if model not in MODELS:
        raise HTTPException(404, '未知のモデルです')
    if not installed(model):
        raise HTTPException(409, '先にモデル環境をインストールしてください。')
    data = await image.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, '画像は10MBまでです。')
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ['PNG', 'JPEG'] or source.width * source.height > 25000000:
                raise ValueError('JPEG/PNG、2500万画素以下が必要です')
            source.load()
            clean = source.convert('RGBA')
    except Exception as exc:
        raise HTTPException(400, '画像を読み込めません: ' + str(exc))
    def work(jid):
        folder = PRIVATE / jid
        folder.mkdir(parents=True)
        input_path = folder / 'input.png'
        clean.save(input_path)
        upstream, python = model_paths(model)
        jobs[jid]['message'] = '重み読み込み / 3D生成中'
        command([str(python), '-c', 'import torch; assert torch.cuda.is_available(), "CUDA GPU is unavailable"'], upstream, folder / 'gpu-check.log', timeout=60)
        args = [str(python), str(upstream / 'run.py'), str(input_path), '--output-dir', str(folder / 'output'), '--device', 'cuda:0' if model == 'triposr' else 'cuda']
        if model == 'triposr':
            args += ['--model-save-format', 'glb']
        command(args, upstream, folder / 'inference.log')
        artifact = folder / 'output' / '0' / 'mesh.glb'
        if not artifact.is_file():
            raise RuntimeError('GLBが生成されませんでした。ローカルログを確認してください。')
        jobs[jid].update(artifact='/api/artifacts/' + jid, message='リグなし3Dメッシュ生成完了')
    return spawn(work)

@app.get('/api/jobs/{jid}')
def job(jid: str):
    if jid not in jobs:
        raise HTTPException(404, 'ジョブがありません（再起動すると履歴がクリアされます）。')
    return jobs[jid]

@app.get('/api/artifacts/{jid}')
def artifact(jid: str):
    if jid not in jobs or jobs[jid]['status'] != 'completed' or 'artifact' not in jobs[jid]:
        raise HTTPException(404, '生成結果がありません。')
    return FileResponse(PRIVATE / jid / 'output' / '0' / 'mesh.glb', media_type='model/gltf-binary', filename='mesh.glb')

app.mount('/', StaticFiles(directory=ROOT / 'docs', html=True), name='studio')
