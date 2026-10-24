"""Audit the public demo's files, licenses, recorded evidence and core fingerprint."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    manifest = json.loads((PUBLIC / "manifest.json").read_text())
    fingerprint = hashlib.sha256(
        b"".join(
            (ROOT / "server" / name).read_bytes()
            for name in ("media.py", "temporal.py", "embedding.py", "engine.py")
        )
    ).hexdigest()
    checked = 0
    for source in manifest["sources"]:
        assert digest(PUBLIC / source["url"].lstrip("/")) == source["sha256"], source[
            "id"
        ]
        assert (PUBLIC / source["thumbnail"].lstrip("/")).is_file()
        assert source["creator"] and source["license"] and source["licenseUrl"]
    for demo in manifest["demos"]:
        assert digest(PUBLIC / demo["url"].lstrip("/")) == demo["sha256"], demo["id"]
        assert (PUBLIC / demo["thumbnail"].lstrip("/")).is_file()
        folder = PUBLIC / "evidence" / demo["id"]
        report = json.loads((folder / "report.json").read_text())
        assert report["recorded"] is True
        assert report["query"]["sha256"] == demo["sha256"]
        assert report["engineFingerprint"] == fingerprint, f"Stale engine: {demo['id']}"
        assert report["retrieval"]["engine"] == "Qwen/Qwen3-VL-Embedding-2B"
        assert (
            report["retrieval"]["revision"]
            == "9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda"
        )
        expected = {s["source"] for s in demo.get("segments", [])} or (
            {demo["source"]} if demo["source"] else set()
        )
        assert {m["source"]["id"] for m in report["results"]} == expected, (
            f"Unexpected fixture result: {demo['id']}"
        )
        referenced = {
            e[k]
            for match in report["results"]
            for e in match["evidence"]
            for k in ("queryImage", "sourceImage")
        }
        assert {a["file"] for a in report["evidenceAssets"]} == referenced
        for asset in report["evidenceAssets"]:
            assert re.fullmatch(r"[-a-zA-Z0-9]+\.jpg", asset["file"])
            assert digest(folder / asset["file"]) == asset["sha256"], asset["file"]
            checked += 1
    saved = json.loads((PUBLIC / "semantic-searches.json").read_text())
    for query in saved["searches"]:
        for hit in query["results"]:
            assert (
                PUBLIC / "semantic-frames" / f"{hit['sourceId']}-{int(hit['time'])}.jpg"
            ).is_file()
    evaluation = json.loads((PUBLIC / "evaluation.json").read_text())
    assert evaluation["complete"] is True
    assert evaluation["engineFingerprint"] == fingerprint
    assert evaluation["singleEngineFingerprint"] is True
    assert evaluation["total"] == len(evaluation["cases"])
    return dict(
        sources=len(manifest["sources"]),
        recordedRuns=len(manifest["demos"]),
        evidenceImages=checked,
        semanticQueries=len(saved["searches"]),
        evaluationCases=evaluation["total"],
        engineFingerprint=fingerprint,
    )


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
