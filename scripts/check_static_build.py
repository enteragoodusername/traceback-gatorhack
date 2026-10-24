"""Check HTML and CSS references, including nested demo pages, beneath a hosting base."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("--base", default="/")
args = parser.parse_args()
root = args.directory.resolve()
assert (root / "index.html").is_file(), "Build is missing index.html"
references = []


def css_references(owner, text):
    references.extend(
        (owner, m.strip("\"' ")) for m in re.findall(r"url\(([^)]+)\)", text)
    )


class References(HTMLParser):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True
        for key, value in attrs:
            if key in ("src", "href", "poster") and value:
                references.append((self.owner, value))
            if key == "style" and value:
                css_references(self.owner, value)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            css_references(self.owner, data)


for path in root.rglob("*.html"):
    References(path).feed(path.read_text())
for path in root.rglob("*.css"):
    css_references(path, path.read_text())
checked = 0
for owner, ref in references:
    parsed = urlsplit(ref)
    if parsed.scheme or parsed.netloc or not parsed.path:
        continue
    path = unquote(parsed.path)
    if path.startswith("/"):
        assert path.startswith(args.base), f"Incorrect deployment base: {ref}"
        target = root / path[len(args.base) :]
    else:
        target = owner.parent / path
    target = target.resolve()
    assert target.is_relative_to(root), f"Reference escapes the build: {ref}"
    if target.is_dir():
        target /= "index.html"
    assert target.is_file(), f"Missing build asset from {owner.name}: {target}"
    checked += 1
print(f"All {checked} HTML/CSS/media references resolve beneath {args.base}")
