"""Measure actual-pixel Qwen retrieval with disjoint same-film and cross-film distractors.

This is a retrieval experiment, not end-to-end source verification. It preserves
all query ranks, including failures. Source titles never enter model inputs.
Run after scripts/benchmark.py has generated the named query suite.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import embedding
from server.engine import ENGINE_FINGERPRINT
from server.media import extract, probe, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="heldout-refined-v4")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/retrieval-scale-v1"
    )
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Use an empty output directory to preserve earlier results.")
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "public/manifest.json").read_text())
    bundled = manifest["sources"]
    original_records = json.loads((ROOT / "docs/original-media.json").read_text())
    originals = [
        (
            "tears-of-steel",
            ROOT / "data/originals/tears-of-steel.mov",
            original_records[0]["sha256"],
        ),
        (
            "big-buck-bunny",
            ROOT / "data/originals/big-buck-bunny.m4v",
            "738e2f999860553d056dd79c952f58f63cbb73892a57c72342ce9e5330d9d2d7",
        ),
    ]
    planned = []
    for work, path, expected_hash in originals:
        if sha256(path) != expected_hash:
            parser.error(f"Original checksum differs: {path.name}")
        duration = probe(path)["duration"]
        for start in range(0, int(duration) - 20, 20):
            if work == "tears-of-steel" and any(
                start < s["originalOffset"] + s["duration"]
                and start + 20 > s["originalOffset"]
                for s in bundled
            ):
                continue
            planned.append(
                dict(
                    id=f"{work}-{start:03}",
                    work=work,
                    original=path.name,
                    originalSha256=expected_hash,
                    start=start,
                    duration=20,
                )
            )
    queries = sorted(
        (ROOT / "artifacts/benchmarks" / args.suite).glob("[0-9][0-9]-*.mp4")
    )
    if not queries:
        parser.error(
            "No positive benchmark queries found. Generate the named suite first."
        )
    query_plan = [
        dict(id=p.stem, sourceId=p.stem.split("-")[1], sha256=sha256(p))
        for p in queries
    ]
    plan = dict(
        model=embedding.MODEL_ID,
        modelRevision=embedding.MODEL_REVISION,
        engineFingerprint=ENGINE_FINGERPRINT,
        suite=args.suite,
        bundledSources=[s["id"] for s in bundled],
        distractors=planned,
        queries=query_plan,
    )
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    vectors = []
    for source in bundled:
        with np.load(ROOT / "data/index" / source["id"] / "semantic.npz") as data:
            vectors.append((source["id"], data["vectors"].copy()))
    for i, source in enumerate(planned):
        path = out / (source["id"] + ".mp4")
        original = ROOT / "data/originals" / source["original"]
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                str(source["start"]),
                "-t",
                "20",
                "-i",
                str(original),
                "-vf",
                "scale=640:-2",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                str(path),
            ],
            check=True,
        )
        source["sha256"] = sha256(path)
        frames = extract(path, fps=1)
        indices = list(range(0, len(frames), 4))
        values = embedding.embed([{"image": frames[j].image} for j in indices])
        vectors.append((source["id"], values))
        np.savez_compressed(out / (source["id"] + ".npz"), vectors=values)
        print(f"Indexed distractor {i + 1}/{len(planned)}: {source['id']}", flush=True)
    summary = {
        **plan,
        "complete": False,
        "sourceCount": len(vectors),
        "vectorCount": sum(len(v) for _, v in vectors),
        "scope": "Semantic retrieval only, using the same 32 positive query edits as the four-source evaluation. Added disjoint 20-second excerpts from Tears of Steel and Big Buck Bunny. No geometric verification, calibrated match probability, production latency, or unseen-query accuracy is claimed. All distractor intervals were fixed before inference; zero overlap with target source intervals.",
        "observations": [],
    }
    for path, query in zip(queries, query_plan):
        started = time.monotonic()
        frames = extract(path, fps=2)
        indices = np.linspace(0, len(frames) - 1, min(3, len(frames)), dtype=int)
        q = embedding.embed([{"image": frames[j].image} for j in indices])
        ranked = sorted(
            [
                dict(
                    sourceId=sid,
                    similarity=round(float((q @ v.T).max(axis=1).mean()), 4),
                )
                for sid, v in vectors
            ],
            key=lambda item: item["similarity"],
            reverse=True,
        )
        rank = next(
            i + 1
            for i, row in enumerate(ranked)
            if row["sourceId"] == query["sourceId"]
        )
        result = dict(
            id=query["id"],
            expectedSourceId=query["sourceId"],
            rank=rank,
            topFive=ranked[:5],
            elapsedSeconds=round(time.monotonic() - started, 2),
        )
        summary["observations"].append(result)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(result), flush=True)
    summary.update(
        complete=True,
        top1=sum(r["rank"] == 1 for r in summary["observations"]),
        top5=sum(r["rank"] <= 5 for r in summary["observations"]),
        total=len(queries),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"Complete: {summary['top1']}/{len(queries)} top 1; {summary['top5']}/{len(queries)} top 5 among {len(vectors)} sources.",
        flush=True,
    )


if __name__ == "__main__":
    main()
