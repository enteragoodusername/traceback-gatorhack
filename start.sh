#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run ./setup.sh first to install the local engine.' >&2
  exit 1
fi
if [[ ! -d dist ]]; then
  echo 'Building the interface…'
  npm run build
fi
if [[ -f .env ]]; then
  echo 'Loading configuration from .env'
  set -a
  source .env
  set +a
fi
echo "Traceback: http://127.0.0.1:${TRACEBACK_PORT:-8000}"
exec .venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port "${TRACEBACK_PORT:-8000}"
