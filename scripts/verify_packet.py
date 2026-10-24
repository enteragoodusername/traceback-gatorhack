"""Verify checksums in an exported Traceback ZIP without extracting its files."""

import argparse
import hashlib
import json
import re
import sys
import zipfile


def verify(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError("Packet contains duplicate ZIP entries.")
        if sum(i.file_size for i in entries) > 100 * 1024 * 1024:
            raise ValueError("Packet exceeds the 100 MB verification limit.")
        raw = archive.read("report.json")
        report = json.loads(raw)
        checksum = archive.read("report.sha256").decode().strip().split()
        if not checksum or hashlib.sha256(raw).hexdigest() != checksum[0]:
            raise ValueError("Report checksum does not match.")
        assets = report.get("evidenceAssets")
        if not isinstance(assets, list) or not isinstance(report.get("results"), list):
            raise ValueError("Report is missing its evidence inventory.")
        referenced = {
            evidence[key]
            for result in report["results"]
            for evidence in result["evidence"]
            for key in ("queryImage", "sourceImage")
        }
        inventory = [item["file"] for item in assets]
        if len(inventory) != len(set(inventory)) or set(inventory) != referenced:
            raise ValueError("Evidence inventory does not match inspected frames.")
        for item in assets:
            if not re.fullmatch(r"[-a-zA-Z0-9]+\.jpg", item["file"]):
                raise ValueError("Unexpected evidence filename.")
            actual = hashlib.sha256(archive.read("frames/" + item["file"])).hexdigest()
            if actual != item["sha256"]:
                raise ValueError(f"Checksum mismatch: {item['file']}")
        return len(assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet")
    args = parser.parse_args()
    try:
        checked = verify(args.packet)
        print(
            f"Checksums verified: report and {checked} evidence images. This verifies file integrity, not authorship or ownership."
        )
    except (ValueError, KeyError, TypeError, UnicodeError, zipfile.BadZipFile) as exc:
        print(f"Packet verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
