#!/usr/bin/env bash
set -euo pipefail
# Linux/WSL2 with NVIDIA support. No model downloads or cloud provisioning.
cd "$(dirname "$0")/.."
python3.11 -m venv .venv-sam
source .venv-sam/bin/activate
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
python -m pip install pytorch-lightning pyrender opencv-python yacs scikit-image einops timm dill pandas rich hydra-core hydra-submitit-launcher hydra-colorlog pyrootutils webdataset chump networkx==3.2.1 roma joblib seaborn wandb appdirs appnope ffmpeg cython jsonlines pytest xtcocotools loguru optree fvcore black pycocotools tensorboard huggingface_hub
python -m pip install 'git+https://github.com/facebookresearch/detectron2.git@a1ce2f9' --no-build-isolation --no-deps
mkdir -p vendor
if [ ! -d vendor/sam-3d-body/.git ]; then git clone https://github.com/facebookresearch/sam-3d-body.git vendor/sam-3d-body; fi
git -C vendor/sam-3d-body rev-parse HEAD > vendor/sam-3d-body.commit
python -c 'import torch; assert torch.cuda.is_available(), "CUDA unavailable"; print(torch.cuda.get_device_name(0))'
echo 'Environment prepared. Request model access and download checkpoints using the documented commands.'
