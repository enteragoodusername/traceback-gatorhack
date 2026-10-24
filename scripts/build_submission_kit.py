"""Package reviewable handoff artifacts without credentials, dependencies or weights."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/submission-kit/traceback-submission-kit.zip",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output name to preserve an earlier release kit.")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip():
        parser.error("Commit the reviewed source before packaging a release kit.")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    files = {
        "START_HERE.txt": f"""TRACEBACK - SUBMISSION KIT

Project source revision: {commit}
Public demo: https://enteragoodusername.github.io/traceback-gatorhack/
Source: https://github.com/enteragoodusername/traceback-gatorhack
Captioned walkthrough: https://enteragoodusername.github.io/traceback-gatorhack/demo/

This is a prepared project, not a submitted Devpost entry.

1. Open the judge brief and watch the 2:15 MP4.
2. Open Verify a packet in the demo, choose traceback-evidence.zip, then compare
   sample-query.mp4 with the recorded query hash. Both checks stay in the browser.
   Use SUBMISSION.md for the project description and PITCH.md to rehearse.
3. Supply the real eligible registered team and actual contributions.
4. Upload the MP4 to YouTube or Vimeo and use that URL in Devpost's video field.
5. Submit before Sunday, October 25, 2026, 5:00 PM Eastern.
6. Arrange the required eligible teammate's presence at the Monday, October 26,
   10:15 AM Eastern finals at the Reitz Union. Confirm the official rules.

Rules: https://gatorhack2026.devpost.com/rules
Submission: https://gatorhack2026.devpost.com/

The hosted app uses clearly labeled saved results. Run ./setup.sh and ./start.sh
from the source repository for new local inference. Model weights are separate.

SHA256SUMS.json records the exact included artifact bytes. These are integrity
checksums, not signatures or proof of authorship.
""".encode(),
    }
    mapping = {
        "traceback-brief.pdf": "public/downloads/traceback-brief.pdf",
        "traceback-demo.mp4": "public/demo/traceback-demo.mp4",
        "traceback-demo.srt": "public/demo/traceback-demo.srt",
        "traceback-demo.vtt": "public/demo/traceback-demo.vtt",
        "traceback-evidence.zip": "public/downloads/traceback-evidence.zip",
        "sample-query.mp4": "public/media/query-vertical.mp4",
        "SUBMISSION.md": "docs/SUBMISSION.md",
        "HANDOFF.md": "docs/HANDOFF.md",
        "PITCH.md": "docs/PITCH.md",
        "TEST_REPORT.md": "docs/TEST_REPORT.md",
        "DEMO_VIDEO.md": "docs/DEMO_VIDEO.md",
        "EVIDENCE_FORMAT.md": "docs/EVIDENCE_FORMAT.md",
        "EXTENDED_VALIDATION.md": "docs/EXTENDED_VALIDATION.md",
        "NOTICE.md": "NOTICE.md",
        "LICENSE": "LICENSE",
        "font-licenses/dmsans-OFL.txt": "public/fonts/dmsans-OFL.txt",
        "font-licenses/manrope-OFL.txt": "public/fonts/manrope-OFL.txt",
        "media/evidence.png": "docs/media/evidence.png",
        "media/evaluation-timing.png": "docs/media/evaluation-timing.png",
        "media/cross-work-failure.png": "docs/media/cross-work-failure.png",
        "media/search-diagnostic.png": "docs/media/search-diagnostic.png",
        "evaluation.json": "public/evaluation.json",
    }
    for target, source in mapping.items():
        data = (ROOT / source).read_bytes()
        if target.endswith(".md"):
            data = (
                data.decode()
                .replace("](../public/validation/", "](validation/")
                .encode()
            )
        files[target] = data
    for path in (ROOT / "public/validation").glob("*.json"):
        files["validation/" + path.name] = path.read_bytes()
    files["SHA256SUMS.json"] = json.dumps(
        {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(files.items())
        },
        indent=2,
    ).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(args.output) as archive:
        checksums = json.loads(archive.read("SHA256SUMS.json"))
        assert archive.testzip() is None
        assert all(
            hashlib.sha256(archive.read(name)).hexdigest() == expected
            for name, expected in checksums.items()
        )
    if args.output.stat().st_size >= 35 * 1024 * 1024:
        raise ValueError(
            "Submission kit exceeds Devpost's documented attachment limit."
        )
    print(
        json.dumps(
            {
                "path": str(args.output.resolve()),
                "sourceCommit": commit,
                "files": len(files),
                "bytes": args.output.stat().st_size,
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
