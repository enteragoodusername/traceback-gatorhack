#!/usr/bin/env python3
"""Check that the deployed tool contains no prerecorded answers or demo footage."""

import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument("directory", nargs="?", default="dist")
parser.add_argument("--base", default="/")
args = parser.parse_args()
root = Path(args.directory)
assert (root / "index.html").is_file(), "Missing entry point"
for file in root.rglob("*"):
    if file.is_file():
        assert file.suffix not in {
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
            ".zip",
            ".pdf",
            ".json",
        }, f"Unexpected preloaded content: {file}"
        assert file.relative_to(root).parts[0] in {
            "assets",
            "fonts",
            "index.html",
            "favicon.svg",
        }, f"Unexpected asset: {file}"
references = []
for file in [root / "index.html", *root.glob("assets/*.css")]:
    content = file.read_text()
    references.extend(re.findall(r'(?:src|href)=["\']([^"\']+)["\']', content))
    references.extend(re.findall(r'url\(["\']?([^"\')]+)', content))
for reference in references:
    if reference.startswith(("http:", "https:", "data:", "#")):
        continue
    if reference.startswith(args.base):
        reference = reference[len(args.base) :]
    assert (root / reference.lstrip("/")).is_file(), (
        f"Broken built reference: {reference}"
    )
js = "\n".join(file.read_text() for file in root.glob("assets/*.js"))
assert "/api/search-video" in js, "Live upload endpoint missing"
for forbidden in [
    "/manifest.json",
    "/semantic-searches.json",
    "/evidence/vertical/",
    "RECORDED RUN",
    "Verify sample packet",
]:
    assert forbidden not in js, f"Recorded workflow remains in bundle: {forbidden}"
print(
    f"Live-only build verified: {len(references)} asset references; no bundled videos, reports, or prerecorded answers."
)
