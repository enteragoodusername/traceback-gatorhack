"""Optional demo-video build dependency: pip install piper-tts (not needed by app)."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/video-build"
OUT.mkdir(parents=True, exist_ok=True)
chapters = json.loads((ROOT / "docs/DEMO_NARRATION.json").read_text())
for chapter in chapters:
    path = OUT / (chapter["id"] + ".wav")
    subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "piper",
            "--data-dir",
            str(ROOT / "artifacts/narration"),
            "-m",
            "en_US-ljspeech-medium",
            "-f",
            str(path),
            "--",
            chapter["text"],
        ],
        check=True,
    )
    data = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ]
        )
    )
    chapter["duration"] = round(float(data["format"]["duration"]) + 1.2, 3)
    print(chapter["id"], chapter["duration"], flush=True)
(OUT / "chapters.json").write_text(json.dumps(chapters, indent=2))
print("Total seconds:", sum(c["duration"] for c in chapters))
