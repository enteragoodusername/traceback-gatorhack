#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/originals
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess

for item in json.loads(Path('docs/original-media.json').read_text()):
    target=Path('data/originals')/item['file']
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256']:
        print('Already verified:',target)
        continue
    temporary=target.with_suffix(target.suffix+'.download')
    subprocess.run(['curl','--fail','--location','--retry','2','--output',str(temporary),item['url']],check=True)
    if hashlib.sha256(temporary.read_bytes()).hexdigest()!=item['sha256']:
        raise SystemExit(f'Checksum differs from the evaluated source: {temporary}. Existing originals were preserved.')
    temporary.replace(target)
    print('Downloaded and verified:',target)
PY
echo 'Attribution and transformations are documented in NOTICE.md.'
