#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -x .venv-sam/bin/python ]; then
  SAM_PYTHON="$PWD/.venv-sam/bin/python"
elif [ -x "$HOME/miniconda3/envs/sam3d-blackwell/bin/python" ]; then
  SAM_PYTHON="$HOME/miniconda3/envs/sam3d-blackwell/bin/python"
else
  echo 'SAM environment not found. Follow README setup instructions.' >&2
  exit 2
fi
export MPLCONFIGDIR="$PWD/vendor/.mplcache"
"$SAM_PYTHON" -m lab.benchmark --config experiments/sam3d.local.json
