"""Exercise documented failure modes; report observations, not an accuracy score."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.engine import analyze

OUT = ROOT / "artifacts/stress-cases"
OUT.mkdir(parents=True, exist_ok=True)
MEDIA = ROOT / "public/media"


def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


cases = [
    {
        "id": "reverse",
        "source": "bridge",
        "description": "Reverse playback is outside the positive-speed alignment model. Shared imagery may be found, but any positive playback estimate is not the true edit.",
        "filter": "reverse,scale=640:-2",
    },
    {
        "id": "heavy-blur",
        "source": "bridge",
        "description": "Severe blur removes the local visual detail needed for geometric verification.",
        "filter": "scale=48:-2,scale=640:-2:flags=bilinear",
    },
    {
        "id": "heavy-occlusion",
        "source": "bridge",
        "description": "An opaque overlay covers 70% of the image. This tests severe partial visibility.",
        "filter": "scale=640:-2,drawbox=x=0:y=0:w=iw:h=ih*0.7:color=black:t=fill",
    },
    {
        "id": "freeze",
        "source": "bridge",
        "description": "An eight-second repeated still has shared imagery but no identifiable playback speed.",
        "freeze": True,
    },
    {
        "id": "black",
        "source": None,
        "description": "A featureless black clip should have no verified source.",
        "color": "black",
    },
    {
        "id": "white",
        "source": None,
        "description": "A featureless white clip should have no verified source.",
        "color": "white",
    },
    {
        "id": "nonlinear",
        "source": "bridge",
        "description": "One source changes from normal playback to 2x halfway through. A single linear fit cannot explain the whole clip.",
        "nonlinear": True,
    },
    {
        "id": "small-inset",
        "source": "bridge",
        "description": "The source occupies a small picture-in-picture region over unrelated footage. Current overlap requirements may reject it.",
        "inset": True,
    },
]
rows = []
for case in cases:
    path = OUT / (case["id"] + ".mp4")
    common = [
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "25",
        "-movflags",
        "+faststart",
        path,
    ]
    if case.get("color"):
        ffmpeg(
            "-f", "lavfi", "-i", f"color=c={case['color']}:s=640x360:r=24:d=8", *common
        )
    elif case.get("freeze"):
        still = OUT / "still.jpg"
        ffmpeg("-ss", 12, "-i", MEDIA / "bridge.mp4", "-frames:v", 1, still)
        ffmpeg(
            "-loop", 1, "-i", still, "-t", 8, "-vf", "scale=640:-2", "-r", 24, *common
        )
    elif case.get("nonlinear"):
        ffmpeg(
            "-ss",
            8,
            "-t",
            12,
            "-i",
            MEDIA / "bridge.mp4",
            "-filter_complex",
            "[0:v]split[a][b];[a]trim=0:6,setpts=PTS-STARTPTS[x];[b]trim=6:12,setpts=(PTS-STARTPTS)/2[y];[x][y]concat=n=2:v=1:a=0,scale=640:-2[out]",
            "-map",
            "[out]",
            *common,
        )
    elif case.get("inset"):
        ffmpeg(
            "-i",
            MEDIA / "query-unrelated.mp4",
            "-ss",
            8,
            "-t",
            8,
            "-i",
            MEDIA / "bridge.mp4",
            "-filter_complex",
            "[0:v]scale=640:360[bg];[1:v]scale=256:-2[fg];[bg][fg]overlay=40:40:shortest=1[out]",
            "-map",
            "[out]",
            "-t",
            8,
            *common,
        )
    else:
        ffmpeg(
            "-ss",
            8,
            "-t",
            8,
            "-i",
            MEDIA / "bridge.mp4",
            "-vf",
            case["filter"],
            *common,
        )
    print("Analyzing stress case:", case["id"], flush=True)
    report = analyze(path, OUT / case["id"], use_semantic=True)
    row = {k: case[k] for k in ("id", "source", "description")}
    row.update(
        querySha256=report["query"]["sha256"],
        engineFingerprint=report["engineFingerprint"],
        elapsedSeconds=report["elapsedSeconds"],
        results=[
            {
                "sourceId": m["source"]["id"],
                "verifiedFrames": m["alignment"]["support"],
                "coverage": m["coverage"],
                "speed": m["alignment"]["speed"],
                "speedReliable": m["alignment"]["speedReliable"],
                "timingAmbiguous": m["alignment"]["timingAmbiguous"],
                "queryStart": m["alignment"]["queryStart"],
                "queryEnd": m["alignment"]["queryEnd"],
            }
            for m in report["results"]
        ],
    )
    rows.append(row)
    summary = {
        "complete": len(rows) == len(cases),
        "scope": "Eight deliberately difficult or unsupported edits. This is a diagnostic stress test, not a representative accuracy benchmark. Source identity describes construction, not an assertion that the current method must recover it.",
        "cases": rows,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(row), flush=True)
(ROOT / "public/validation/stress-cases.json").write_text(json.dumps(summary, indent=2))
