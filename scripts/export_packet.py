"""Export an existing measured report as a checksum-verifiable evidence ZIP."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile


def export(report_path: Path, destination: Path, attribution: str):
    if destination.exists():
        raise ValueError("Choose a new output path; existing packets are preserved.")
    report = json.loads(report_path.read_text())
    names = sorted(
        {
            e[key]
            for match in report["results"]
            for e in match["evidence"]
            for key in ("queryImage", "sourceImage")
        }
    )
    expected = {a["file"]: a["sha256"] for a in report.get("evidenceAssets", [])}
    files = {}
    assets = []
    for name in names:
        if not re.fullmatch(r"[-a-zA-Z0-9]+\.jpg", name):
            raise ValueError("Invalid evidence filename.")
        data = (report_path.parent / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if expected.get(name) != digest:
            raise ValueError(f"Evidence checksum mismatch or missing hash: {name}")
        files["frames/" + name] = data
        assets.append({"file": name, "sha256": digest})
    report.update(
        evidenceAssets=assets,
        attribution=attribution,
        exportedAt=datetime.now(timezone.utc).isoformat(),
    )
    raw = json.dumps(report, indent=2).encode()
    files["report.json"] = raw
    files["report.sha256"] = (
        hashlib.sha256(raw).hexdigest() + "  report.json\n"
    ).encode()
    files["README.txt"] = (
        "TRACEBACK EVIDENCE PACKET\n\nMeasured report and inspected frames. Verify with scripts/verify_packet.py.\n\nChecksums establish file integrity, not authorship, ownership, infringement, or first publication. They are not digital signatures. The original videos are identified by hash and are not included.\n\n"
        + attribution
        + "\n\n"
        + "\n".join(report.get("limitations", []))
    ).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return len(assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--attribution",
        default="Source rights metadata is included in report.json. Verify applicable permissions before reusing source media.",
    )
    args = parser.parse_args()
    try:
        count = export(args.report, args.output, args.attribution)
        print(f"Exported {args.output} with {count} inspected frames.")
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")
