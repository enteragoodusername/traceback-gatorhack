"""Frozen-engine validation on a third film, in an isolated six-source library.

Uses two previously unindexed Big Buck Bunny excerpts plus the four bundled
sources. It does not alter the user's active library or the engine thresholds.
Every planned case is written before any model result is observed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import engine, embedding
from server.media import sha256

VIDEO_SHA = "738e2f999860553d056dd79c952f58f63cbb73892a57c72342ce9e5330d9d2d7"
CREDIT = "(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org"


def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--original", type=Path, default=ROOT / "data/originals/big-buck-bunny.m4v"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/cross-work-v2")
    args = parser.parse_args()
    if sha256(args.original) != VIDEO_SHA:
        parser.error("Original video checksum differs from the documented input.")
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Use an empty output directory to preserve prior results.")
    out.mkdir(parents=True, exist_ok=True)
    isolated = out / "workspace"
    (isolated / "data/index").mkdir(parents=True)
    (isolated / "public").symlink_to(ROOT / "public", target_is_directory=True)
    bundled = json.loads((ROOT / "public/manifest.json").read_text())["sources"]
    for source in bundled:
        (isolated / "data/index" / source["id"]).symlink_to(
            ROOT / "data/index" / source["id"], target_is_directory=True
        )
    engine.ROOT = isolated
    engine.INDEX = isolated / "data/index"
    engine.USER_LIBRARY = isolated / "data/library.json"
    engine._library = None
    sources = []
    cases = []
    transforms = [
        ("reencode", "scale=480:-2", 1.0, 28, 2.35),
        ("crop-fast", "crop=iw*0.65:ih*0.85,scale=360:-2", 1.25, 28, 9.45),
        ("mirror-slow", "hflip,scale=480:-2", 0.8, 27, 19.15),
        (
            "gray-caption",
            "hue=s=0,drawbox=x=0:y=ih-45:w=iw:h=45:color=black@0.7:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='EDITED CLIP':fontsize=20:fontcolor=white:x=15:y=h-32",
            1.0,
            30,
            28.05,
        ),
    ]
    for number, original_offset in enumerate((100, 300)):
        sid = (
            "user-"
            + hashlib.md5(f"traceback-cross-work-bbb-{number}".encode()).hexdigest()
        )
        folder = isolated / "data/sources" / sid
        folder.mkdir(parents=True)
        video = folder / "video.mp4"
        ffmpeg(
            "-ss",
            original_offset,
            "-t",
            40,
            "-i",
            args.original,
            "-vf",
            "scale=640:-2",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            23,
            "-movflags",
            "+faststart",
            video,
        )
        source = dict(
            id=sid,
            title=f"Big Buck Bunny excerpt {number + 1}",
            duration=40,
            originalOffset=original_offset,
            url=f"/api/sources/{sid}/video.mp4",
            thumbnail="",
            sha256=sha256(video),
            creator=CREDIT,
            work="Big Buck Bunny",
            license="CC BY 3.0",
            licenseUrl="https://creativecommons.org/licenses/by/3.0/",
            sourceUrl="https://peach.blender.org/",
            userProvided=True,
        )
        sources.append(source)
        for name, filters, speed, crf, start in transforms:
            case_id = f"bbb-{number + 1}-{name}"
            path = out / (case_id + ".mp4")
            ffmpeg(
                "-ss",
                start,
                "-t",
                8,
                "-i",
                video,
                "-vf",
                f"{filters},setpts=PTS/{speed}",
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                crf,
                "-movflags",
                "+faststart",
                path,
            )
            cases.append(
                dict(
                    id=case_id,
                    sourceId=sid,
                    offset=start,
                    speed=speed,
                    querySha256=sha256(path),
                    transform=name,
                )
            )
    for original_offset in (450, 520):
        case_id = f"bbb-unindexed-{original_offset}"
        path = out / (case_id + ".mp4")
        ffmpeg(
            "-ss",
            original_offset,
            "-t",
            8,
            "-i",
            args.original,
            "-vf",
            "scale=640:-2",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            28,
            path,
        )
        cases.append(
            dict(
                id=case_id,
                sourceId=None,
                originalOffset=original_offset,
                querySha256=sha256(path),
                transform="unindexed-same-film",
            )
        )
    plan = dict(
        engineFingerprint=engine.ENGINE_FINGERPRINT,
        model=embedding.MODEL_ID,
        modelRevision=embedding.MODEL_REVISION,
        originalSha256=VIDEO_SHA,
        sources=sources,
        cases=cases,
    )
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    print(
        "Frozen plan written: eight positive edits, two unindexed same-film negatives",
        flush=True,
    )
    for source in sources:
        engine.register_source(source, lambda m: print(m, flush=True))
    summary = {
        **plan,
        "scope": "Additional-film diagnostic validation, with no threshold changes. Two Big Buck Bunny excerpts joined the four bundled sources in an isolated six-source library. These synthetic edits are not a production accuracy estimate. All ten cases were specified before inference.",
        "credit": CREDIT,
        "licenseUrl": "https://peach.blender.org/about/",
        "complete": False,
        "observations": [],
    }
    for case in cases:
        started = time.monotonic()
        report = engine.analyze(
            out / (case["id"] + ".mp4"), out / case["id"], use_semantic=True
        )
        expected = case["sourceId"]
        returned = [r["source"]["id"] for r in report["results"]]
        match = next(
            (r for r in report["results"] if r["source"]["id"] == expected), None
        )
        observation = dict(
            id=case["id"],
            expectedSourceId=expected,
            returnedSourceIds=returned,
            correct=returned == ([expected] if expected else []),
            elapsedSeconds=round(time.monotonic() - started, 2),
            reportSha256=sha256(out / case["id"] / "report.json"),
        )
        observation["retrievalRank"] = next(
            (
                i + 1
                for i, row in enumerate(report["retrieval"]["rankings"])
                if row["sourceId"] == expected
            ),
            None,
        )
        if match:
            observation.update(
                offsetError=abs(match["alignment"]["offset"] - case["offset"]),
                speedError=abs(match["alignment"]["speed"] - case["speed"]),
                verifiedFrames=match["alignment"]["support"],
                speedReliable=match["alignment"]["speedReliable"],
                timingAmbiguous=match["alignment"]["timingAmbiguous"],
            )
        summary["observations"].append(observation)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(observation), flush=True)
    summary["complete"] = True
    summary.update(
        positiveCount=sum(bool(c["sourceId"]) for c in cases),
        negativeCount=sum(not c["sourceId"] for c in cases),
        recovered=sum(
            bool(r["expectedSourceId"]) and r["correct"]
            for r in summary["observations"]
        ),
        rejected=sum(
            not r["expectedSourceId"] and r["correct"] for r in summary["observations"]
        ),
        falseMatchCases=sum(
            bool(
                set(r["returnedSourceIds"])
                - ({r["expectedSourceId"]} if r["expectedSourceId"] else set())
            )
            for r in summary["observations"]
        ),
    )
    summary["correct"] = sum(r["correct"] for r in summary["observations"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"Complete: {summary['correct']}/{len(cases)} source decisions. No core changes.",
        flush=True,
    )


if __name__ == "__main__":
    main()
