#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for tool in python3 ffmpeg ffprobe node npm; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing $tool. Install Python 3.11+, FFmpeg and Node.js 22+ before continuing." >&2
    exit 1
  fi
done
if command -v uv >/dev/null 2>&1; then
  [[ -x .venv/bin/python ]] || uv venv .venv --python python3
  # Both indexes are official; hashes in the lock pin the exact accepted wheels.
  uv pip install --python .venv/bin/python --index-strategy unsafe-best-match -r requirements.lock
else
  [[ -x .venv/bin/python ]] || python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
fi
npm ci
npm run build
if [[ ! -f data/index/metadata.json ]]; then
  echo 'Building the source index. The first run downloads the 2B model (~4.4 GB).'
  .venv/bin/python -m server.index
fi
echo 'Ready. Run ./start.sh and open http://127.0.0.1:8000'
