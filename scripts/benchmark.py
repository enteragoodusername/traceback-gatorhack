"""Reproducible held-out edit benchmark. Ground truth never enters the engine."""

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.engine import analyze


def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="development")
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed", type=int, default=4107)
    parser.add_argument("--visual-only", action="store_true")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    directory = ROOT / "artifacts/benchmarks" / args.suite
    if directory.exists() and any(directory.iterdir()):
        parser.error("Choose a new suite name to preserve earlier benchmark evidence.")
    directory.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "public/manifest.json").read_text())
    transforms = [
        ("reencode", "scale=480:-2", 1.0, 29),
        ("vertical-crop", "crop=ih*0.7:ih,scale=320:-2", 1.25, 26),
        (
            "gray-overlay",
            "hue=s=0,drawbox=x=0:y=ih-50:w=iw:h=50:color=black@0.7:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='REPOSTED CLIP':fontsize=22:fontcolor=white:x=20:y=h-35",
            1.0,
            27,
        ),
        ("mirror-slow", "hflip,scale=480:-2", 0.8, 25),
        ("zoom-fast", "crop=iw*0.65:ih*0.65,scale=480:-2", 1.5, 28),
        ("rotate", "rotate=0.08:fillcolor=black,scale=480:-2", 1.0, 26),
        ("letterbox", "scale=480:-2,pad=480:360:(ow-iw)/2:(oh-ih)/2:black", 1.0, 28),
        ("low-quality", "scale=256:-2,eq=contrast=1.2:saturation=0.35", 1.2, 35),
    ]
    cases = []
    for i in range(args.count):
        source = manifest["sources"][i % len(manifest["sources"])]
        name, filters, speed, crf = transforms[
            (i // len(manifest["sources"])) % len(transforms)
        ]
        start = round(rng.uniform(2, 25), 2)
        length = 8
        case_id = f"{i:02}-{source['id']}-{name}"
        path = directory / f"{case_id}.mp4"
        ffmpeg(
            "-ss",
            start,
            "-t",
            length,
            "-i",
            ROOT / "public" / source["url"].lstrip("/"),
            "-vf",
            f"{filters},setpts=PTS/{speed}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            crf,
            "-movflags",
            "+faststart",
            path,
        )
        cases.append(
            dict(
                id=case_id,
                path=path,
                source=source["id"],
                offset=start,
                speed=speed,
                transform=name,
            )
        )
    for i, start in enumerate((5, 20, 35, 45)):
        path = directory / f"negative-{i}.mp4"
        ffmpeg(
            "-ss",
            start,
            "-t",
            8,
            "-i",
            ROOT / "data/originals/sintel-trailer.mp4",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            27,
            path,
        )
        cases.append(
            dict(id=f"negative-{i}", path=path, source=None, transform="unrelated-film")
        )
    # Same film, different excerpts: harder negatives than a different medium.
    for i, start in enumerate((320, 380, 540, 580)):
        path = directory / f"unindexed-{i}.mp4"
        ffmpeg(
            "-ss",
            start,
            "-t",
            8,
            "-i",
            ROOT / "data/originals/tears-of-steel.mov",
            "-an",
            "-vf",
            "scale=480:-2",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            27,
            path,
        )
        cases.append(
            dict(
                id=f"unindexed-{i}",
                path=path,
                source=None,
                transform="unindexed-same-film",
            )
        )
    results = []
    started = time.time()
    for i, case in enumerate(cases):
        print(f"[{i + 1}/{len(cases)}] {case['id']}", flush=True)
        report = analyze(
            case["path"], directory / case["id"], use_semantic=not args.visual_only
        )
        found = [r["source"]["id"] for r in report["results"]]
        correct = case["source"] in found if case["source"] else not found
        false = [sid for sid in found if sid != case["source"]]
        row = {k: v for k, v in case.items() if k != "path"}
        row.update(
            found=found,
            correct=correct,
            falseMatches=false,
            elapsedSeconds=report["elapsedSeconds"],
            semanticTop1=report["retrieval"]["rankings"][0]["sourceId"]
            if report["retrieval"]["rankings"]
            else None,
        )
        if case["source"] in found:
            aligned = next(
                r for r in report["results"] if r["source"]["id"] == case["source"]
            )["alignment"]
            row.update(
                offsetError=round(abs(aligned["offset"] - case["offset"]), 4),
                speedError=round(abs(aligned["speed"] - case["speed"]), 4),
                verifiedFrames=aligned["support"],
                speedReliable=aligned.get("speedReliable"),
                speedRange=aligned.get("speedRange"),
            )
        results.append(row)
        summary = dict(
            suite=args.suite,
            seed=args.seed,
            visualOnly=args.visual_only,
            elapsedSeconds=round(time.time() - started, 1),
            completed=len(results),
            total=len(cases),
            passed=sum(r["correct"] and not r["falseMatches"] for r in results),
            results=results,
        )
        (directory / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(row), flush=True)
    print("Saved", directory / "summary.json", flush=True)


if __name__ == "__main__":
    main()
