"""Run the actual pipeline and publish its reproducible evidence, not mock results."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.engine import analyze

manifest = json.loads((ROOT / "public/manifest.json").read_text())
for demo in manifest["demos"]:
    print("Analyzing", demo["id"], flush=True)
    report = analyze(
        ROOT / "public" / demo["url"].lstrip("/"),
        ROOT / "public/evidence" / demo["id"],
        lambda stage, msg: print(stage, msg, flush=True),
    )
    report["recorded"] = True
    report["fixtureId"] = demo["id"]
    (ROOT / "public/evidence" / demo["id"] / "report.json").write_text(
        json.dumps(report, indent=2)
    )
    print(
        [
            (
                r["source"]["id"],
                r["alignment"]["offset"],
                r["alignment"]["speed"],
                r["coverage"],
            )
            for r in report["results"]
        ],
        flush=True,
    )
