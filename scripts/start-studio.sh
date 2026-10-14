#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
printf '%s\n' 'Open http://127.0.0.1:8765/studio.html'
.venv-studio/bin/python -m uvicorn lab.server:app --host 127.0.0.1 --port 8765
