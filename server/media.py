"""Bounded media decoding and explainable visual descriptors."""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import subprocess
import cv2
import numpy as np

MAX_DURATION = 60.0
MAX_SIZE = 100 * 1024 * 1024


@dataclass
class Frame:
    time: float
    image: np.ndarray
    points: np.ndarray
    descriptors: np.ndarray | None
    signature: np.ndarray


def probe(path: Path) -> dict:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,codec_name:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError("Video duration must be positive.")
        if stream["width"] * stream["height"] > 4096 * 2160:
            raise ValueError("Please resize this video to 4K or smaller.")
        return dict(
            duration=duration,
            width=stream["width"],
            height=stream["height"],
            codec=stream["codec_name"],
        )
    except (
        subprocess.SubprocessError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("This file could not be read as a supported video.") from exc


def signature(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (32, 18)).astype(np.float32)
    small = (small - small.mean()) / (small.std() + 1e-6)
    return small.flatten()


def describe(image: np.ndarray, time: float) -> Frame:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(
        nfeatures=900, scaleFactor=1.2, nlevels=8, edgeThreshold=19, fastThreshold=12
    )
    kp, desc = orb.detectAndCompute(gray, None)
    pts = np.array([k.pt for k in kp], dtype=np.float32).reshape(-1, 2)
    return Frame(time, image, pts, desc, signature(image))


def extract(
    path: Path, fps: float = 2, max_duration: float = MAX_DURATION, width: int = 640
) -> list[Frame]:
    info = probe(path)
    if info["duration"] > max_duration + 0.1:
        raise ValueError(f"Please use a clip of {int(max_duration)} seconds or less.")
    cap = cv2.VideoCapture(str(path))
    frames = []
    try:
        for time in np.arange(0, info["duration"] - 0.04, 1 / fps):
            cap.set(cv2.CAP_PROP_POS_MSEC, float(time) * 1000)
            ok, image = cap.read()
            if not ok:
                continue
            h, w = image.shape[:2]
            if w > width or h > width:
                scale = width / max(w, h)
                image = cv2.resize(image, (round(w * scale), round(h * scale)))
            frames.append(describe(image, round(float(time), 3)))
    finally:
        cap.release()
    if len(frames) < 3:
        raise ValueError("Please use a video at least 2 seconds long.")
    return frames


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(query: Frame, source: Frame) -> dict | None:
    if (
        query.descriptors is None
        or source.descriptors is None
        or len(source.points) < 8
        or len(query.points) < 8
    ):
        return None
    matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        query.descriptors, source.descriptors, k=2
    )
    good = [
        a
        for pair in matches
        if len(pair) == 2
        for a, b in [pair]
        if a.distance < 0.76 * b.distance and a.distance < 66
    ]
    # Repeated textures can send several query points to one source point.
    # A one-to-one correspondence is necessary before fitting geometry.
    unique = {}
    for m in good:
        if m.trainIdx not in unique or m.distance < unique[m.trainIdx].distance:
            unique[m.trainIdx] = m
    good = list(unique.values())
    if len(good) < 12:
        return None
    q = np.float32([query.points[m.queryIdx] for m in good])
    s = np.float32([source.points[m.trainIdx] for m in good])
    homography, mask = cv2.findHomography(q, s, cv2.RANSAC, 4.0)
    if homography is None or mask is None or not np.isfinite(homography).all():
        return None
    inlier = mask.ravel().astype(bool)
    count = int(inlier.sum())
    ratio = count / len(good)
    if count < 12 or ratio < 0.45:
        return None
    h, w = query.image.shape[:2]
    sh, sw = source.image.shape[:2]
    hull = cv2.convexHull(q[inlier])
    coverage = float(cv2.contourArea(hull) / (w * h))
    source_coverage = float(cv2.contourArea(cv2.convexHull(s[inlier])) / (sw * sh))
    if coverage < 0.025 or source_coverage < 0.015:
        return None
    quad = cv2.perspectiveTransform(
        np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2), homography
    ).reshape(-1, 2)
    if not np.isfinite(quad).all() or np.max(np.abs(quad)) > max(sw, sh) * 5:
        return None
    if not cv2.isContourConvex(quad.astype(np.float32)):
        return None
    area = abs(float(cv2.contourArea(quad.astype(np.float32)))) / (sw * sh)
    if not 0.04 < area < 6:
        return None
    # Shared titles, logos and repeated small textures are not enough. Check the
    # aligned image content over the visible overlap, independently of keypoints.
    try:
        inverse = np.linalg.inv(homography)
    except np.linalg.LinAlgError:
        return None
    aligned = cv2.warpPerspective(
        cv2.cvtColor(source.image, cv2.COLOR_BGR2GRAY), inverse, (w, h)
    )
    valid = cv2.warpPerspective(np.full((sh, sw), 255, dtype=np.uint8), inverse, (w, h))
    valid = cv2.erode(valid, np.ones((7, 7), np.uint8)) > 250
    if valid.mean() < 0.25:
        return None
    qgray = cv2.cvtColor(query.image, cv2.COLOR_BGR2GRAY)
    # Blur reduces sensitivity to compression and sub-frame motion.
    qvalues = cv2.GaussianBlur(qgray, (5, 5), 0)[valid].astype(np.float32)
    svalues = cv2.GaussianBlur(aligned, (5, 5), 0)[valid].astype(np.float32)
    qvalues -= qvalues.mean()
    svalues -= svalues.mean()
    correlation = float(
        np.dot(qvalues, svalues)
        / (np.linalg.norm(qvalues) * np.linalg.norm(svalues) + 1e-8)
    )
    if correlation < 0.45:
        return None
    evidence = []
    for qi, si in zip(q[inlier][:36], s[inlier][:36]):
        evidence.append(
            dict(
                query=[round(float(qi[0] / w), 5), round(float(qi[1] / h), 5)],
                source=[round(float(si[0] / sw), 5), round(float(si[1] / sh), 5)],
            )
        )
    return dict(
        queryTime=query.time,
        sourceTime=source.time,
        inliers=count,
        tentative=len(good),
        inlierRatio=round(ratio, 4),
        coverage=round(coverage, 4),
        photometricCorrelation=round(correlation, 4),
        points=evidence,
        quad=[[round(float(x / sw), 4), round(float(y / sh), 4)] for x, y in quad],
        mirrored=False,
    )
