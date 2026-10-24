"""Check that HTML/CSS build references resolve beneath a chosen hosting base."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("--base", default="/")
args = parser.parse_args()
references = []


class References(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("src", "href") and value:
                references.append(value)


References().feed((args.directory / "index.html").read_text())
for path in (args.directory / "assets").glob("*.css"):
    references.extend(
        m.strip("\"' ") for m in re.findall(r"url\(([^)]+)\)", path.read_text())
    )
checked = 0
for ref in references:
    if ref.startswith(("http:", "https:", "data:", "#")):
        continue
    assert ref.startswith(args.base), f"Incorrect deployment base: {ref}"
    target = args.directory / ref[len(args.base) :]
    assert target.is_file(), f"Missing build asset: {target}"
    checked += 1
print(f"All {checked} HTML/CSS asset references resolve beneath {args.base}")
