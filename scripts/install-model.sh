#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
model="${1:-}"
case "$model" in
triposr) repo='https://github.com/VAST-AI-Research/TripoSR.git'; target='TripoSR';;
sf3d) repo='https://github.com/Stability-AI/stable-fast-3d.git'; target='stable-fast-3d';;
*) printf '%s\n' 'Unknown model'; exit 2;;
esac
# Isolated environments: SAM and each generator can have incompatible dependencies.
mkdir -p vendor
rm -f "vendor/$model.installed"
python3 -m venv ".venv-$model"
python="$(pwd)/.venv-$model/bin/python"
"$python" -m pip install --upgrade pip setuptools wheel
"$python" -m pip install 'torch==2.5.1' 'torchvision==0.20.1' --index-url https://download.pytorch.org/whl/cu124
if [ ! -d "vendor/$target/.git" ]; then git clone "$repo" "vendor/$target"; fi
git -C "vendor/$target" rev-parse HEAD > "vendor/$model.commit"
cd "vendor/$target"
"$python" -m pip install -r requirements.txt
if [ "$model" = triposr ]; then "$python" -c 'from tsr.system import TSR'; else "$python" -c 'from sf3d.system import SF3D'; fi
"$python" -c 'import torch; assert torch.cuda.is_available(), "CUDA GPU is unavailable; check WSL/NVIDIA drivers"'
cd ../..
touch "vendor/$model.installed"
printf '%s\n' 'Environment installed. Weights are downloaded on first inference. SF3D requires approved Hugging Face access.'
