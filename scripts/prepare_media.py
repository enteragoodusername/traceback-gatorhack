"""Make attributed, deterministic demo media. Originals are never committed."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/media"
ORIGINAL = ROOT / "data/originals/tears-of-steel.mov"
SOURCES = [
    (
        "bridge",
        "The bridge",
        "An encounter above the Amsterdam canals.",
        225,
        40,
        "Exterior · People",
    ),
    (
        "laboratory",
        "The laboratory",
        "A team prepares an experiment inside the lab.",
        165,
        40,
        "Interior · Science",
    ),
    (
        "observatory",
        "The observatory",
        "A quiet conversation overlooking the city.",
        75,
        40,
        "Interior · City",
    ),
    (
        "machines",
        "The machines",
        "Mechanical creatures move through the city.",
        450,
        40,
        "Exterior · Action",
    ),
]


def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_montage():
    """A two-source query: the analyzer never receives these segment labels."""
    dest = OUT / "query-montage.mp4"
    ffmpeg(
        "-ss",
        8,
        "-t",
        7,
        "-i",
        OUT / "bridge.mp4",
        "-ss",
        9,
        "-t",
        7,
        "-i",
        OUT / "laboratory.mp4",
        "-filter_complex",
        "[0:v]scale=640:-2,setsar=1,eq=saturation=0.6,setpts=PTS-STARTPTS[a];"
        "[1:v]scale=640:-2,setsar=1,eq=contrast=1.12,setpts=PTS-STARTPTS[b];"
        "[a][b]concat=n=2:v=1:a=0[out]",
        "-map",
        "[out]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        27,
        "-movflags",
        "+faststart",
        dest,
    )
    ffmpeg("-ss", 2, "-i", dest, "-frames:v", 1, OUT / "query-montage.jpg")
    return dict(
        id="montage",
        title="Two stories, one edit",
        subtitle="Two sources · scene cut · color changes",
        source=None,
        start=0,
        length=14,
        speed=1,
        segments=[
            dict(source="bridge", queryStart=0, sourceStart=8, length=7),
            dict(source="laboratory", queryStart=7, sourceStart=9, length=7),
        ],
        url="/media/query-montage.mp4",
        thumbnail="/media/query-montage.jpg",
        sha256=digest(dest),
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = []
    for sid, title, description, start, duration, category in SOURCES:
        dest = OUT / f"{sid}.mp4"
        ffmpeg(
            "-ss",
            start,
            "-i",
            ORIGINAL,
            "-t",
            duration,
            "-vf",
            "scale=960:-2",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-movflags",
            "+faststart",
            dest,
        )
        ffmpeg(
            "-ss",
            8,
            "-i",
            dest,
            "-frames:v",
            1,
            "-vf",
            "scale=640:-2",
            OUT / f"{sid}.jpg",
        )
        sources.append(
            dict(
                id=sid,
                title=title,
                description=description,
                category=category,
                duration=duration,
                originalOffset=start,
                url=f"/media/{sid}.mp4",
                thumbnail=f"/media/{sid}.jpg",
                sha256=digest(dest),
                creator="Blender Foundation",
                work="Tears of Steel (2012)",
                license="CC BY 3.0",
                licenseUrl="https://creativecommons.org/licenses/by/3.0/",
                sourceUrl="https://mango.blender.org/",
            )
        )
    # This known transform is ground truth for evaluation, never an input to matching.
    demos = [
        dict(
            id="vertical",
            title="The cropped repost",
            subtitle="Vertical crop · color grade · 1.25× speed",
            source="bridge",
            start=8,
            length=12,
            speed=1.25,
            filters="crop=ih*0.62:ih,scale=360:-2,eq=saturation=0.65:contrast=1.12:brightness=0.015",
            overlay=True,
        ),
        dict(
            id="graded",
            title="A different look",
            subtitle="Color grade · compression · text overlay",
            source="laboratory",
            start=9,
            length=12,
            speed=1,
            filters="scale=640:-2,eq=saturation=0.2:contrast=1.18",
            overlay=True,
        ),
        dict(
            id="reframed",
            title="Hidden in plain sight",
            subtitle="Zoom · horizontal flip · 0.8× speed",
            source="machines",
            start=7,
            length=10,
            speed=0.8,
            filters="crop=iw*0.78:ih*0.78,hflip,scale=640:-2",
            overlay=False,
        ),
    ]
    for demo in demos:
        vf = demo["filters"] + f",setpts=PTS/{demo['speed']}"
        if demo["overlay"]:
            vf += ",drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.55:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='A different perspective':fontcolor=white:fontsize=18:x=(w-tw)/2:y=h-38"
        dest = OUT / f"query-{demo['id']}.mp4"
        ffmpeg(
            "-ss",
            demo["start"],
            "-t",
            demo["length"],
            "-i",
            OUT / f"{demo['source']}.mp4",
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "27",
            "-movflags",
            "+faststart",
            dest,
        )
        ffmpeg("-ss", 2, "-i", dest, "-frames:v", 1, OUT / f"query-{demo['id']}.jpg")
        demo.update(
            url=f"/media/query-{demo['id']}.mp4",
            thumbnail=f"/media/query-{demo['id']}.jpg",
            sha256=digest(dest),
        )
    negative = OUT / "query-unrelated.mp4"
    ffmpeg(
        "-ss",
        25,
        "-i",
        ROOT / "data/originals/sintel-trailer.mp4",
        "-t",
        10,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        24,
        "-movflags",
        "+faststart",
        negative,
    )
    ffmpeg("-ss", 2, "-i", negative, "-frames:v", 1, OUT / "query-unrelated.jpg")
    demos.append(
        dict(
            id="unrelated",
            title="A different story",
            subtitle="Unrelated footage · no indexed source",
            source=None,
            start=25,
            length=10,
            speed=1,
            url="/media/query-unrelated.mp4",
            thumbnail="/media/query-unrelated.jpg",
            sha256=digest(negative),
        )
    )
    demos.append(build_montage())
    manifest = dict(
        sources=sources,
        demos=demos,
        attribution="Tears of Steel — (CC) Blender Foundation | mango.blender.org; Sintel trailer — (CC) Blender Foundation | durian.blender.org. Both CC BY 3.0. Excerpts trimmed, resized, muted, and deliberately transformed for this demonstration.",
        originalUrl="https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov",
    )
    (ROOT / "public/manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Prepared", len(sources), "sources and", len(demos), "queries.", flush=True)


if __name__ == "__main__":
    main()
