"""Run full frozen-engine checks in the larger retrieval experiment's library.

Reuses exact source embedding matrices from retrieval_scale.py and generates the
same 1 fps visual descriptors as index_source. Nothing changes the active library.
"""

import argparse
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import engine, embedding
from server.media import extract, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retrieval", type=Path, default=ROOT / "artifacts/retrieval-scale-v1"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/verification-scale-v1"
    )
    args = parser.parse_args()
    retrieval = args.retrieval.resolve()
    metadata = json.loads((retrieval / "summary.json").read_text())
    if (
        not metadata["complete"]
        or metadata["engineFingerprint"] != engine.ENGINE_FINGERPRINT
    ):
        parser.error(
            "A completed retrieval experiment with the current frozen engine is required."
        )
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Use an empty output directory to preserve previous evidence.")
    workspace = out / "workspace"
    (workspace / "data/index").mkdir(parents=True)
    (workspace / "public").symlink_to(ROOT / "public", target_is_directory=True)
    bundled = json.loads((ROOT / "public/manifest.json").read_text())["sources"]
    for source in bundled:
        (workspace / "data/index" / source["id"]).symlink_to(
            ROOT / "data/index" / source["id"], target_is_directory=True
        )
    cases = [
        ("04-bridge-vertical-crop", "bridge"),
        ("09-laboratory-gray-overlay", "laboratory"),
        ("14-observatory-mirror-slow", "observatory"),
        ("19-machines-zoom-fast", "machines"),
        ("negative-0", None),
        ("negative-2", None),
    ]
    query_folder = ROOT / "artifacts/benchmarks" / metadata["suite"]
    plan = dict(
        engineFingerprint=engine.ENGINE_FINGERPRINT,
        model=embedding.MODEL_ID,
        modelRevision=embedding.MODEL_REVISION,
        retrievalSummarySha256=sha256(retrieval / "summary.json"),
        sourceCount=metadata["sourceCount"],
        cases=[
            dict(
                id=name,
                expectedSourceId=expected,
                querySha256=sha256(query_folder / (name + ".mp4")),
            )
            for name, expected in cases
        ],
    )
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    custom = []
    for i, source in enumerate(metadata["distractors"]):
        sid = source["id"]
        video = retrieval / (sid + ".mp4")
        if sha256(video) != source["sha256"]:
            raise ValueError(f"Distractor changed: {sid}")
        source_dir = workspace / "data/sources" / sid
        source_dir.mkdir(parents=True)
        (source_dir / "video.mp4").symlink_to(video)
        directory = workspace / "data/index" / sid
        directory.mkdir()
        frames = extract(video, fps=1)
        payload = {}
        for j, frame in enumerate(frames):
            cv2.imwrite(
                str(directory / f"{j:03}.jpg"),
                frame.image,
                [cv2.IMWRITE_JPEG_QUALITY, 88],
            )
            payload[f"points_{j}"] = frame.points
            payload[f"desc_{j}"] = (
                frame.descriptors
                if frame.descriptors is not None
                else np.empty((0, 32), dtype=np.uint8)
            )
        payload["times"] = np.array([f.time for f in frames])
        payload["signatures"] = np.stack([f.signature for f in frames])
        np.savez_compressed(directory / "visual.npz", **payload)
        with np.load(retrieval / (sid + ".npz")) as existing:
            vectors = existing["vectors"].copy()
        times = np.array([frames[j].time for j in range(0, len(frames), 4)])
        if len(vectors) != len(times):
            raise ValueError("Reused embedding rows do not match source sampling.")
        np.savez_compressed(directory / "semantic.npz", vectors=vectors, times=times)
        custom.append(
            dict(
                id=sid,
                title=sid,
                duration=source["duration"],
                originalOffset=source["start"],
                url="",
                thumbnail="",
                sha256=source["sha256"],
                creator="Blender Foundation",
                work=source["work"],
                license="CC BY 3.0",
                licenseUrl="https://creativecommons.org/licenses/by/3.0/",
                sourceUrl="",
                userProvided=True,
            )
        )
        print(f"Visual index {i + 1}/{len(metadata['distractors'])}: {sid}", flush=True)
    (workspace / "data/library.json").write_text(json.dumps(custom, indent=2))
    engine.ROOT = workspace
    engine.INDEX = workspace / "data/index"
    engine.USER_LIBRARY = workspace / "data/library.json"
    engine._library = None
    summary = {
        **plan,
        "complete": False,
        "scope": "Six selected existing queries, four positive and two unrelated Sintel negatives, against the full expanded library. Actual semantic retrieval plus geometric and temporal verification. This is a small larger-library smoke test, not a new independent accuracy estimate or a controlled latency benchmark. Exact source vectors were reused from the retrieval experiment; visual descriptors were regenerated with the production sampling function.",
        "observations": [],
    }
    for case in plan["cases"]:
        started = time.monotonic()
        report = engine.analyze(
            query_folder / (case["id"] + ".mp4"), out / case["id"], use_semantic=True
        )
        expected = case["expectedSourceId"]
        actual = [r["source"]["id"] for r in report["results"]]
        row = dict(
            id=case["id"],
            expectedSourceId=expected,
            returnedSourceIds=actual,
            correct=actual == ([expected] if expected else []),
            elapsedSeconds=round(time.monotonic() - started, 2),
            reportSha256=sha256(out / case["id"] / "report.json"),
        )
        summary["observations"].append(row)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(row), flush=True)
    summary.update(
        complete=True,
        correct=sum(r["correct"] for r in summary["observations"]),
        total=len(plan["cases"]),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"Completed {summary['correct']}/{summary['total']} decisions across {summary['sourceCount']} indexed sources",
        flush=True,
    )


if __name__ == "__main__":
    main()
