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
    validation = PUBLIC / "validation"
    for name in (
        "live-ingestion",
        "reproducibility",
        "cross-work",
        "cross-work-diagnosis",
        "retrieval-scale",
        "verification-scale",
    ):
        path = validation / (name + ".json")
        if path.exists():
            record = json.loads(path.read_text())
            assert record["engineFingerprint"] == fingerprint, (
                f"Stale validation: {name}"
            )
    stress = json.loads((validation / "stress-cases.json").read_text())
    assert stress["complete"] and all(
        row["engineFingerprint"] == fingerprint for row in stress["cases"]
    )
    cross = json.loads((validation / "cross-work.json").read_text())
    assert cross["complete"] and len(cross["observations"]) == len(cross["cases"])
    assert cross["recovered"] == sum(
        bool(row["expectedSourceId"]) and row["correct"]
        for row in cross["observations"]
    )
    assert cross["rejected"] == sum(
        not row["expectedSourceId"] and row["correct"] for row in cross["observations"]
    )
    for row in cross["observations"]:
        expected = [row["expectedSourceId"]] if row["expectedSourceId"] else []
        assert row["correct"] == (row["returnedSourceIds"] == expected)
    scale_path = validation / "retrieval-scale.json"
    if scale_path.exists():
        scale = json.loads(scale_path.read_text())
        assert scale["complete"] and scale["total"] == len(scale["observations"])
        assert scale["sourceCount"] == len(scale["bundledSources"]) + len(
            scale["distractors"]
        )
        assert scale["top1"] == sum(row["rank"] == 1 for row in scale["observations"])
        assert scale["top5"] == sum(row["rank"] <= 5 for row in scale["observations"])
    verification_path = validation / "verification-scale.json"
    if verification_path.exists():
        verification = json.loads(verification_path.read_text())
        assert digest(scale_path) == verification["retrievalSummarySha256"]
        assert verification["complete"] and verification["total"] == len(
            verification["observations"]
        )
        assert verification["correct"] == sum(
            row["correct"] for row in verification["observations"]
        )
    return dict(
        sources=len(manifest["sources"]),
        recordedRuns=len(manifest["demos"]),
        evidenceImages=checked,
        semanticQueries=len(saved["searches"]),
        evaluationCases=evaluation["total"],
        additionalFilmCases=len(cross["cases"]),
        engineFingerprint=fingerprint,
    )


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
