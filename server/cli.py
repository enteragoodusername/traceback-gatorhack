"""Traceback's local engine, without a browser: python -m server.cli --help."""

import argparse
import json
from pathlib import Path
import sys

from .engine import analyze, semantic_search, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    trace = commands.add_parser(
        "analyze", help="Analyze a new edited clip against the indexed library"
    )
    trace.add_argument("video", type=Path)
    trace.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory for measured report and evidence images",
    )
    trace.add_argument(
        "--visual-only",
        action="store_true",
        help="Skip semantic inference; clearly labeled in the report",
    )
    search = commands.add_parser(
        "search", help="Search source pixels with a text description"
    )
    search.add_argument("query")
    commands.add_parser("library", help="List source IDs, rights metadata and hashes")
    args = parser.parse_args()
    try:
        if args.command == "library":
            print(json.dumps(sources(), indent=2))
        elif args.command == "search":
            print(json.dumps(semantic_search(args.query), indent=2))
        else:
            if not args.video.is_file():
                raise ValueError("The query video does not exist.")
            if args.output.exists() and any(args.output.iterdir()):
                raise ValueError(
                    "Choose an empty output directory to preserve prior evidence."
                )
            report = analyze(
                args.video,
                args.output,
                lambda stage, message: print(
                    f"[{stage}] {message}", file=sys.stderr, flush=True
                ),
                use_semantic=not args.visual_only,
            )
            print(
                json.dumps(
                    {
                        "report": str(args.output / "report.json"),
                        "sources": [
                            {
                                "id": m["source"]["id"],
                                "queryStart": m["alignment"]["queryStart"],
                                "queryEnd": m["alignment"]["queryEnd"],
                                "sourceStart": m["alignment"]["sourceStart"],
                                "sourceEnd": m["alignment"]["sourceEnd"],
                                "speed": m["alignment"]["speed"],
                                "speedReliable": m["alignment"]["speedReliable"],
                            }
                            for m in report["results"]
                        ],
                    },
                    indent=2,
                )
            )
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Traceback: {exc}\n")


if __name__ == "__main__":
    main()
