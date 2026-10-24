"""Extract a user-selected interval before any search or model processing."""

from pathlib import Path
import subprocess
from .media import probe

MAX_UPLOAD_SIZE = 1024 * 1024 * 1024


def trim_video(source: Path, target: Path, start: float, duration: float):
    temporary = target.with_name("trimming.mp4")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                str(start),
                "-i",
                str(source),
                "-t",
                str(duration),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "scale=trunc(min(1280\\,iw)/2)*2:-2,fps=30",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            check=True,
            timeout=180,
            capture_output=True,
        )
        info = probe(temporary)
        if (
            not 1.9 <= info["duration"] <= 60.1
            or abs(info["duration"] - duration) > 0.2
        ):
            raise ValueError("The selected section could not be extracted completely.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
