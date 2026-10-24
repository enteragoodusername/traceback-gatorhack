"""Supplemental mixed-edit diagnostic; run with --root /path/to/traceback --out NEW_DIRECTORY.
Uses the unchanged four-source index and bundled licensed clips. Not an accuracy study.
"""

import argparse, hashlib, json, pathlib, subprocess, sys, time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root", type=pathlib.Path, required=True)
p.add_argument("--out", type=pathlib.Path, required=True)
a = p.parse_args()
root = a.root.resolve()
out = a.out.resolve()
if out.exists() and any(out.iterdir()):
    p.error("Use an empty output directory.")
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root))
from server import engine, embedding

if {source["id"] for source in engine.sources()} != {
    "bridge",
    "laboratory",
    "observatory",
    "machines",
}:
    p.error("Use a checkout with only the four bundled sources indexed.")

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def ff(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


# Each segment records its original file, start, output duration, and whether held still.
N = lambda t, d: dict(file="query-unrelated", start=t, duration=d)
S = lambda n, t, d: dict(file=n, start=t, duration=d)
B = lambda d: dict(color="black", duration=d)
cases = [
    dict(
        id="unmatched-bookends",
        segments=[N(0, 3), S("bridge", 8, 4), N(3, 3)],
        knownSources=["bridge"],
    ),
    dict(
        id="unmatched-middle",
        segments=[S("bridge", 8, 4), N(0, 4), S("laboratory", 9, 4)],
        knownSources=["bridge", "laboratory"],
    ),
    dict(
        id="still-then-motion",
        segments=[
            dict(file="bridge", start=12, duration=4, freeze=True),
            S("laboratory", 9, 6),
        ],
        knownSources=["bridge", "laboratory"],
        note="Bridge appears as a still; its playback speed is not identifiable. A lab match does not validate the still.",
    ),
    dict(
        id="black-bookends",
        segments=[B(3), S("machines", 7, 4), B(3)],
        knownSources=["machines"],
    ),
    dict(
        id="two-second-insert",
        segments=[N(0, 4), S("observatory", 5, 2), N(4, 4)],
        knownSources=["observatory"],
        note="Very short source interval; abstention is an acceptable diagnostic outcome.",
    ),
    dict(id="unrelated-and-black", segments=[N(0, 5), B(5)], knownSources=[]),
]
plan = dict(
    scope="Six predefined mixed edits from bundled material. Diagnostic observations only, no accuracy score. Known sources describe construction, not guaranteed recoverability. Unchanged production engine and four-source library.",
    engineFingerprint=engine.ENGINE_FINGERPRINT,
    model=embedding.MODEL_ID,
    modelRevision=embedding.MODEL_REVISION,
    sourceCommit=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip(),
    inputHashes={
        n: sha(root / "public/media" / f"{n}.mp4")
        for n in ["bridge", "laboratory", "observatory", "machines", "query-unrelated"]
    },
    cases=cases,
)
(out / "plan.json").write_text(json.dumps(plan, indent=2))
for case in cases:
    parts = []
    position = 0
    for i, s in enumerate(case["segments"]):
        seg = out / f"{case['id']}-{i}.mp4"
        parts.append(seg)
        s["queryStart"] = position
        position += s["duration"]
        s["queryEnd"] = position
        inputs = []
        if s.get("color"):
            inputs = [
                "-f",
                "lavfi",
                "-i",
                f"color=c={s['color']}:s=640x360:r=24:d={s['duration']}",
            ]
        elif s.get("freeze"):
            still = out / f"{case['id']}-{i}.jpg"
            ff(
                "-ss",
                s["start"],
                "-i",
                root / "public/media" / f"{s['file']}.mp4",
                "-frames:v",
                1,
                still,
            )
            inputs = ["-loop", 1, "-i", still]
        else:
            inputs = [
                "-ss",
                s["start"],
                "-i",
                root / "public/media" / f"{s['file']}.mp4",
            ]
        ff(
            *inputs,
            "-t",
            s["duration"],
            "-an",
            "-vf",
            "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "25",
            seg,
        )
    listing = out / f"{case['id']}.txt"
    listing.write_text("".join("file '" + str(x) + "'\n" for x in parts))
    q = out / f"{case['id']}.mp4"
    ff(
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        listing,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        q,
    )
    case["querySha256"] = sha(q)
(out / "plan.json").write_text(json.dumps(plan, indent=2))
summary = {**plan, "complete": False, "observations": []}
for case in cases:
    print("Analyzing " + case["id"], flush=True)
    t = time.monotonic()
    report = engine.analyze(
        out / f"{case['id']}.mp4", out / case["id"], use_semantic=True
    )
    row = dict(
        id=case["id"],
        elapsedSeconds=round(time.monotonic() - t, 2),
        reportSha256=sha(out / case["id"] / "report.json"),
        results=[
            dict(
                sourceId=r["source"]["id"],
                coverage=r["coverage"],
                alignment=r["alignment"],
            )
            for r in report["results"]
        ],
    )
    summary["observations"].append(row)
    summary["complete"] = len(summary["observations"]) == len(cases)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(row), flush=True)
