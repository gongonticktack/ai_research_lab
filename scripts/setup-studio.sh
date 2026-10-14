#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv-studio
.venv-studio/bin/python -m pip install -r requirements-studio.txt
printf '%s\n' 'Ready. Run bash scripts/start-studio.sh'
