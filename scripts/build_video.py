"""Render a captioned walkthrough from actual evidence and input media.

This is an evidence visualization, not a simulated browser recording.
Run build_demo.py and build_narration.py first. Requires Pillow and FFmpeg.
"""

import json
import re
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/video-build"
PUBLIC = ROOT / "public"
W, H = 1280, 720
PAPER = "#f6f7f3"
INK = "#203c36"
MUTED = "#657366"
GREEN = "#244f42"
LIME = "#d6ed9a"
FONT = PUBLIC / "fonts"
chapters = json.loads((OUT / "chapters.json").read_text())
manifest = json.loads((PUBLIC / "manifest.json").read_text())
sources = {s["id"]: s for s in manifest["sources"]}


def font(size, bold=False):
    return ImageFont.truetype(
        str(FONT / ("manrope-700.ttf" if bold else "dm-sans-400.ttf")), size
    )


def write(draw, xy, text, size=22, color=INK, bold=False):
    draw.text(xy, text, font=font(size, bold), fill=color)


def wrap(draw, text, xy, width, size=22, color=INK, bold=False, spacing=9):
    words = text.split()
    line = ""
    y = xy[1]
    for word in words:
        attempt = (line + " " + word).strip()
        if draw.textlength(attempt, font=font(size, bold)) > width and line:
            write(draw, (xy[0], y), line, size, color, bold)
            y += size + spacing
            line = word
        else:
            line = attempt
    if line:
        write(draw, (xy[0], y), line, size, color, bold)
    return y + size + spacing


def base(chapter, number):
    image = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((48, 34, 82, 68), radius=8, fill=GREEN)
    d.rectangle((57, 43, 73, 59), outline=LIME, width=2)
    write(d, (96, 31), "traceback.", 28, INK, True)
    write(d, (878, 42), "GATOR HACK V  /  ACTUAL RECORDED OUTPUTS", 13, MUTED)
    d.line((48, 87, 1232, 87), fill="#dce3d6", width=1)
    write(d, (50, 108), f"{number:02d}  /  " + chapter["id"].upper(), 13, GREEN, True)
    wrap(d, chapter["title"], (48, 138), 1180, 36, INK, True, 6)
    d.rectangle((0, 632, W, H), fill=GREEN)
    write(
        d,
        (48, 645),
        "Recorded pipeline walkthrough · Synthetic narration · No simulated live inference",
        13,
        "#ffffff",
    )
    write(
        d,
        (48, 672),
        "Film excerpts: (CC) Blender Foundation · Tears of Steel / mango.blender.org · Sintel / durian.blender.org · CC BY 3.0",
        12,
        "#d5e1ce",
    )
    return image, d


def panel(image, box, path, label, points=None, quad=None, side=None):
    d = ImageDraw.Draw(image)
    x, y, w, h = box
    d.rounded_rectangle((x, y, x + w, y + h), radius=12, fill="#e8ece3")
    source = Image.open(path).convert("RGB")
    contained = ImageOps.contain(source, (w - 24, h - 56))
    px = x + (w - contained.width) // 2
    py = y + 40 + (h - 48 - contained.height) // 2
    image.paste(contained, (px, py))
    write(d, (x + 14, y + 11), label, 13, INK, True)
    if points:
        for point in points:
            nx, ny = point[side]
            cx = px + nx * contained.width
            cy = py + ny * contained.height
            d.ellipse(
                (cx - 4, cy - 4, cx + 4, cy + 4), fill=LIME, outline=GREEN, width=1
            )
    if quad:
        coords = [
            (px + a * contained.width, py + b * contained.height) for a, b in quad
        ]
        d.line(coords + [coords[0]], fill=LIME, width=3)
    return image


def report(name):
    return json.loads((PUBLIC / "evidence" / name / "report.json").read_text())


def draw_frame(chapter, number, variant=0):
    image, d = base(chapter, number)
    kind = chapter["id"]
    if kind == "opening":
        panel(
            image,
            (48, 230, 355, 360),
            PUBLIC / "media/query-vertical.jpg",
            "THE EDITED CLIP",
        )
        write(d, (455, 245), "A crop. A caption. A faster cut.", 30, INK, True)
        wrap(
            d,
            "Find the indexed source, then inspect the connection.",
            (455, 304),
            690,
            30,
            GREEN,
            True,
        )
        wrap(
            d,
            "Local video analysis · Natural-language archive search · Reproducible evidence packets",
            (455, 417),
            665,
            23,
            MUTED,
        )
        write(
            d,
            (455, 553),
            "FOUR LICENSED SOURCES  /  NEW INPUTS SUPPORTED LOCALLY",
            14,
            GREEN,
            True,
        )
    elif kind == "retrieval":
        searches = json.loads((PUBLIC / "semantic-searches.json").read_text())[
            "searches"
        ]
        chosen = searches[variant % len(searches)]
        d.rounded_rectangle((48, 220, 1232, 282), radius=10, fill="#e8efde")
        write(d, (68, 237), "SEARCH  /  " + chosen["query"], 23, GREEN, True)
        for i, hit in enumerate(chosen["results"][:3]):
            x = 48 + i * 400
            sid = hit["sourceId"]
            second = int(hit["time"])
            panel(
                image,
                (x, 306, 384, 216),
                PUBLIC / f"semantic-frames/{sid}-{second}.jpg",
                f"{i + 1}.  " + sources[sid]["title"].upper(),
            )
            write(
                d,
                (x + 5, 538),
                f"{second:02d}s · cosine similarity {hit['similarity']:.3f}",
                17,
                MUTED,
            )
        write(
            d,
            (48, 590),
            "Qwen3-VL-Embedding-2B · January 2026 · Pixels + text, without source titles as inputs",
            17,
            GREEN,
        )
    elif kind == "evidence":
        data = report("vertical")
        found = data["results"][0]
        a = found["alignment"]
        e = found["evidence"][variant % len(found["evidence"])]
        panel(
            image,
            (48, 225, 390, 305),
            PUBLIC / "evidence/vertical" / e["queryImage"],
            f"QUERY  /  {e['queryTime']:.2f}s",
            e["points"],
            side="query",
        )
        panel(
            image,
            (460, 225, 772, 305),
            PUBLIC / "evidence/vertical" / e["sourceImage"],
            f"INDEXED SOURCE  /  {e['sourceTime']:.2f}s",
            e["points"],
            e["quad"],
            "source",
        )
        values = [
            ("VERIFIED QUERY FRAMES", str(a["support"])),
            (
                "PLAYBACK ESTIMATE",
                f"{a['speed']:.2f}×" if a["speedReliable"] else "Uncertain",
            ),
            ("THIS FRAME PAIR", f"{e['inliers']} inliers"),
        ]
        for i, (label, value) in enumerate(values):
            x = 48 + i * 400
            write(d, (x, 547), label, 13, MUTED, True)
            write(d, (x, 568), value, 28, INK, True)
    elif kind == "montage":
        data = report("montage")
        matches = sorted(data["results"], key=lambda m: m["alignment"]["queryStart"])
        for i, m in enumerate(matches[:2]):
            e = m["evidence"][0]
            a = m["alignment"]
            x = 48 + i * 600
            panel(
                image,
                (x, 225, 584, 233),
                PUBLIC / "evidence/montage" / e["sourceImage"],
                m["source"]["title"].upper(),
                e["points"],
                e["quad"],
                "source",
            )
            write(
                d,
                (x, 475),
                f"Query {a['queryStart']:.1f}–{a['queryEnd']:.1f}s",
                24,
                INK,
                True,
            )
            write(
                d,
                (x, 513),
                f"{a['support']} verified frames · source {a['sourceStart']:.1f}–{a['sourceEnd']:.1f}s",
                17,
                MUTED,
            )
            d.rounded_rectangle((x, 552, x + 584, 580), radius=6, fill="#e2e8da")
            left = x + 584 * a["queryStart"] / data["query"]["duration"]
            right = x + 584 * a["queryEnd"] / data["query"]["duration"]
            d.rounded_rectangle((left, 552, right, 580), radius=6, fill=GREEN)
    elif kind == "negative":
        data = report("unrelated")
        evaluation = json.loads((PUBLIC / "evaluation.json").read_text())
        assert not data["results"], (
            "Do not narrate an abstention unless the actual run abstained"
        )
        panel(
            image,
            (48, 230, 570, 300),
            PUBLIC / "media/query-unrelated.jpg",
            "UNRELATED QUERY / SINTEL",
        )
        write(d, (666, 242), "No verified match.", 32, INK, True)
        wrap(
            d,
            "No source was verified in this indexed library. That is not a claim that the clip is original.",
            (666, 301),
            545,
            22,
            MUTED,
        )
        write(
            d,
            (666, 422),
            f"{evaluation['recovered']}/{evaluation['positiveCount']} edited sources recovered",
            24,
            GREEN,
            True,
        )
        write(
            d,
            (666, 461),
            f"{evaluation['rejected']}/{evaluation['negativeCount']} negatives rejected",
            24,
            GREEN,
            True,
        )
        wrap(
            d,
            "Controlled edits of four excerpts. Every case is published.",
            (666, 510),
            525,
            18,
            MUTED,
        )
        write(
            d,
            (48, 577),
            "Verification can abstain. Similarity scores alone cannot establish a shared source.",
            19,
            GREEN,
        )
    elif kind == "packet":
        data = report("vertical")
        a = data["results"][0]["alignment"]
        d.rounded_rectangle((48, 224, 690, 592), radius=12, fill=GREEN)
        write(d, (76, 247), "traceback-evidence.zip", 25, "#ffffff", True)
        for i, line in enumerate(
            [
                "report.json",
                "report.sha256",
                "README.txt",
                f"frames/  ({len(data['evidenceAssets'])} inspected images)",
            ]
        ):
            write(d, (84, 310 + i * 47), line, 23, "#d6ed9a")
        write(d, (76, 549), "Independent checksum verifier included.", 17, "#ffffff")
        y = 232
        for heading, body in [
            ("Content identity", "Query and source SHA-256 hashes"),
            ("Measured evidence", "Corresponding points and source timestamps"),
            ("Reproducible method", "Pinned model revision and engine fingerprint"),
            ("Explicit limits", "Shared imagery does not prove ownership"),
        ]:
            write(d, (742, y), heading, 23, INK, True)
            wrap(d, body, (742, y + 34), 475, 19, MUTED)
            y += 91
    else:
        write(d, (48, 248), "Find the source.", 56, INK, True)
        write(d, (48, 321), "Follow the evidence.", 56, GREEN, True)
        wrap(
            d,
            "Run new analysis locally. Inspect actual saved runs online.",
            (52, 428),
            1090,
            27,
            MUTED,
        )
        d.rounded_rectangle((48, 503, 1232, 590), radius=12, fill="#e7efd9")
        write(
            d,
            (70, 525),
            "github.com/enteragoodusername/traceback-gatorhack",
            28,
            GREEN,
            True,
        )
    return image


def run(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
        check=True,
    )


def main():
    video_parts = []
    caption_lines = []
    offset = 0
    for number, chapter in enumerate(chapters, 1):
        kind = chapter["id"]
        duration = chapter["duration"]
        variant_count = 4 if kind in ("retrieval", "evidence") else 1
        frames = []
        for variant in range(variant_count):
            file = OUT / f"{kind}-{variant}.png"
            draw_frame(chapter, number, variant).save(file)
            frames.append(file)
        listing = OUT / f"{kind}-frames.txt"
        listing.write_text(
            "".join(
                f"file '{p}'\nduration {duration / variant_count:.6f}\n" for p in frames
            )
            + f"file '{frames[-1]}'\n"
        )
        video = OUT / f"{kind}.mp4"
        video_args = [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            listing,
            "-i",
            OUT / f"{kind}.wav",
        ]
        if kind in ("opening", "negative"):
            filename = "query-vertical" if kind == "opening" else "query-unrelated"
            box = (48, 230, 355, 360) if kind == "opening" else (48, 230, 570, 300)
            x, y, width, height = box
            sample = Image.open(PUBLIC / f"media/{filename}.jpg")
            fitted = ImageOps.contain(sample, (width - 24, height - 56))
            px = x + (width - fitted.width) // 2
            py = y + 40 + (height - 48 - fitted.height) // 2
            video_args += [
                "-stream_loop",
                "-1",
                "-i",
                PUBLIC / f"media/{filename}.mp4",
                "-filter_complex",
                f"[2:v]scale={fitted.width}:{fitted.height},setsar=1,fps=24[moving];[0:v]fps=24[background];[background][moving]overlay={px}:{py}:shortest=1,format=yuv420p[video]",
                "-map",
                "[video]",
                "-map",
                "1:a",
            ]
        else:
            video_args += ["-vf", "fps=24,format=yuv420p", "-map", "0:v", "-map", "1:a"]
        run(
            *video_args,
            "-af",
            "apad,loudnorm=I=-17:TP=-1.5:LRA=9",
            "-t",
            duration,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            20,
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            video,
        )
        video_parts.append(video)
        # Sentence-level captions; approximate timing is documented and readable.
        sentences = [s.strip() + "." for s in chapter["text"].split(".") if s.strip()]
        weights = [len(s.split()) for s in sentences]
        total = sum(weights)
        position = offset
        for sentence, weight in zip(sentences, weights):
            end = position + (duration - 1.2) * weight / total
            caption_lines.append((position, end, sentence))
            position = end
        offset += duration
        print("Rendered", kind, flush=True)
    listing = OUT / "video-parts.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in video_parts))
    destination = ROOT / "artifacts/traceback-demo.mp4"
    run(
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
        destination,
    )

    def stamp(value):
        ms = round(value * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    (ROOT / "artifacts/traceback-demo.srt").write_text(
        "\n".join(
            f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}\n"
            for i, (start, end, text) in enumerate(caption_lines, 1)
        )
    )
    subtitle = ROOT / "artifacts/traceback-demo.srt"
    (ROOT / "artifacts/traceback-demo.vtt").write_text(
        "WEBVTT\n\n"
        + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", subtitle.read_text())
    )
    print(destination, flush=True)


if __name__ == "__main__":
    main()
