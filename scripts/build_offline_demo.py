"""Package the root-base production build with a Python-only localhost launcher."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/submission-kit/traceback-offline-demo.zip",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Internal preview only; records that the source includes uncommitted changes.",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output name to preserve earlier artifacts.")
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
    )
    if dirty and not args.allow_dirty:
        parser.error("Commit the reviewed source before packaging a release.")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_static_build.py"),
            str(args.directory),
        ],
        check=True,
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    extra = {
        "START_DEMO.py": (ROOT / "scripts/offline_launcher.py").read_bytes(),
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
        "NOTICE.md": (ROOT / "NOTICE.md").read_bytes(),
        "BUILD.json": json.dumps(
            {
                "sourceCommit": commit,
                "uncommittedChanges": dirty,
                "mode": "recorded-demo",
                "repository": "https://github.com/enteragoodusername/traceback-gatorhack",
            },
            indent=2,
        ).encode(),
        "START_HERE.txt": b"""TRACEBACK - OFFLINE RECORDED DEMO

1. Extract this entire ZIP into a folder.
2. Open a terminal in that folder and run:

   python3 START_DEMO.py

   On Windows, the command may be: python START_DEMO.py
3. Open the localhost URL printed in the terminal.
4. Press Ctrl+C in the terminal to stop the server.

Python 3.8+ is sufficient. No Node.js, model weights, or internet connection are
needed to inspect the bundled runs, watch the video, or verify local packets.
Use --port 8001 if port 8000 is already occupied.

This package presents recorded outputs from actual pipeline runs. It has no
new-inference backend. For new queries and sources, use the full project:
https://github.com/enteragoodusername/traceback-gatorhack

Do not open index.html by double-clicking it: browser module restrictions can
prevent the app from loading over file://. Use the included localhost launcher.

Film excerpts and fonts retain their licenses. See NOTICE.md, fonts/, and
THIRD_PARTY_LICENSES.txt. No ownership or infringement conclusion is implied by
a visual match. Packet checksums are integrity checks, not digital signatures.
""",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path in sorted(args.directory.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    "traceback-offline/" + path.relative_to(args.directory).as_posix(),
                )
        for name, data in extra.items():
            archive.writestr("traceback-offline/" + name, data)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
    print(
        json.dumps(
            {
                "path": str(args.output.resolve()),
                "sourceCommit": commit,
                "uncommittedChanges": dirty,
                "bytes": args.output.stat().st_size,
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
