"""Live video discovery: local captions -> online search -> local visual ranking.

No fixture videos, manifests, saved examples, or known answers are read here.
Only scene descriptions leave the computer; candidate thumbnails come back.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import json
import re
import threading
from itertools import zip_longest
import time
from urllib.parse import quote, urlparse

import cv2
import httpx
import numpy as np
from PIL import Image
from . import embedding
from .media import probe, sha256

CAPTION_MODEL = "Salesforce/blip-image-captioning-base"
CAPTION_REVISION = "82a37760796d32b1411fe092ab5d4e227313294b"
_captioner = None
_caption_lock = threading.Lock()
HEADERS = {
    "User-Agent": "Traceback/0.2 (+https://github.com/enteragoodusername/traceback-gatorhack)"
}


def sample_frames(path: Path, output: Path):
    info = probe(path)
    output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(path))
    frames = []
    try:
        for i, fraction in enumerate((0.15, 0.5, 0.85)):
            second = info["duration"] * fraction
            cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            height, width = frame.shape[:2]
            if max(height, width) > 960:
                frame = cv2.resize(
                    frame,
                    (
                        round(width * 960 / max(height, width)),
                        round(height * 960 / max(height, width)),
                    ),
                )
            filename = f"query-{i}.jpg"
            if not cv2.imwrite(str(output / filename), frame):
                raise ValueError("Could not save a preview frame.")
            frames.append(
                {"time": round(second, 2), "image": filename, "pixels": frame}
            )
    finally:
        cap.release()
    if not frames:
        raise ValueError("No readable frames were found in this clip.")
    return info, frames


def caption_frames(frames):
    global _captioner
    import torch
    from transformers import BlipProcessor, BlipForConditionalGeneration

    torch.set_num_threads(4)
    with _caption_lock:
        if _captioner is None:
            processor = BlipProcessor.from_pretrained(
                CAPTION_MODEL, revision=CAPTION_REVISION
            )
            model = BlipForConditionalGeneration.from_pretrained(
                CAPTION_MODEL, revision=CAPTION_REVISION
            ).eval()
            _captioner = (processor, model)
        processor, model = _captioner
        captions = []
        for frame in frames:
            inputs = processor(
                images=Image.fromarray(
                    cv2.cvtColor(frame["pixels"], cv2.COLOR_BGR2RGB)
                ),
                return_tensors="pt",
            )
            with torch.inference_mode():
                tokens = model.generate(
                    **inputs, max_new_tokens=32, num_beams=3, repetition_penalty=1.2
                )
            caption = processor.decode(tokens[0], skip_special_tokens=True).strip()
            if caption:
                captions.append(caption)
        if not captions:
            raise ValueError("Could not describe this clip. Try a clearer video.")
        return captions


def renderer_text(value):
    if not isinstance(value, dict):
        return ""
    return value.get("simpleText") or "".join(
        r.get("text", "") for r in value.get("runs", [])
    )


def parse_youtube(html):
    marker = re.search(
        r'(?:var\s+ytInitialData|window\["ytInitialData"\])\s*=\s*', html
    )
    if not marker:
        raise RuntimeError("YouTube did not return a readable public search page.")
    data, _ = json.JSONDecoder().raw_decode(html[marker.end() :])
    results, seen = [], set()

    def walk(node):
        if len(results) >= 8:
            return
        if isinstance(node, dict):
            video = node.get("videoRenderer")
            if video:
                vid = video.get("videoId", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or vid in seen:
                    return
                seen.add(vid)
                results.append(
                    {
                        "id": "youtube-" + vid,
                        "title": renderer_text(video.get("title"))[:300],
                        "url": "https://www.youtube.com/watch?v=" + vid,
                        "thumbnailUrl": "https://i.ytimg.com/vi/"
                        + vid
                        + "/hqdefault.jpg",
                        "provider": "YouTube",
                        "creator": renderer_text(video.get("ownerText"))[:200],
                        "duration": renderer_text(video.get("lengthText")),
                        "published": renderer_text(video.get("publishedTimeText")),
                    }
                )
            else:
                for key, value in node.items():
                    # Exclude ads, recommendations and unrelated sidebar content.
                    if key not in {
                        "adSlotRenderer",
                        "promotedSparklesWebRenderer",
                        "secondaryContents",
                    }:
                        walk(value)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(data)
    return results


def youtube_search(query):
    with httpx.Client(timeout=20, headers=HEADERS, follow_redirects=False) as client:
        response = client.get(
            "https://www.youtube.com/results", params={"search_query": query}
        )
        response.raise_for_status()
        return parse_youtube(response.text)


STOP_WORDS = set(
    "a an the of on in is are with and to at by from it there this that some standing sitting walking next front background picture image photo person people man woman wearing".split()
)


def archive_search(query):
    words = list(
        dict.fromkeys(
            w.lower()
            for w in re.findall(r"[A-Za-z]{3,}", query)
            if w.lower() not in STOP_WORDS
        )
    )[:5]
    if not words:
        return []
    # Query text is tokenized rather than interpolated as an Archive search expression.
    expression = "mediatype:movies AND (" + " AND ".join(words[:3]) + ")"
    with httpx.Client(timeout=20, headers=HEADERS) as client:
        response = client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": expression,
                "fl[]": ["identifier", "title", "creator", "date"],
                "rows": 4,
                "output": "json",
            },
        )
        response.raise_for_status()
        docs = response.json().get("response", {}).get("docs", [])
    results = []
    for doc in docs:
        identifier = doc.get("identifier", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", identifier):
            continue
        creator = doc.get("creator", "")
        if isinstance(creator, list):
            creator = ", ".join(str(c) for c in creator)
        title = doc.get("title", identifier)
        if isinstance(title, list):
            title = " · ".join(str(t) for t in title)
        results.append(
            {
                "id": "archive-" + identifier,
                "title": str(title)[:300],
                "url": "https://archive.org/details/" + quote(identifier),
                "thumbnailUrl": "https://archive.org/services/img/" + quote(identifier),
                "provider": "Internet Archive",
                "creator": str(creator)[:200],
                "duration": "",
                "published": str(doc.get("date", ""))[:40],
            }
        )
    return results


def discover(queries):
    tasks = [("YouTube", youtube_search, q) for q in queries[:2]]
    tasks.append(("Internet Archive", archive_search, queries[0]))
    candidates, seen, statuses, batches = [], set(), [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = [(provider, q, pool.submit(fn, q)) for provider, fn, q in tasks]
        for provider, query, future in pending:
            try:
                results = future.result()
                statuses.append(
                    {
                        "provider": provider,
                        "query": query,
                        "status": "ok",
                        "count": len(results),
                    }
                )
                batches.append(results)
            except Exception:
                statuses.append(
                    {
                        "provider": provider,
                        "query": query,
                        "status": "unavailable",
                        "count": 0,
                    }
                )
    # Interleave scene searches so the first caption cannot consume every slot.
    for row in zip_longest(*batches):
        for item in row:
            if item and item["id"] not in seen:
                seen.add(item["id"])
                candidates.append(item)
    # Reserve space for both services while bounding local inference time.
    youtube = [c for c in candidates if c["provider"] == "YouTube"][:8]
    archive = [c for c in candidates if c["provider"] == "Internet Archive"][:4]
    return youtube + archive, statuses


def allowed_thumbnail(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
        and (
            host == "i.ytimg.com"
            or host == "archive.org"
            or host.endswith(".archive.org")
        )
    )


def download_thumbnail(candidate, output):
    """Only service-controlled image hosts, bounded bytes, and validated redirect hops."""
    url = candidate["thumbnailUrl"]
    try:
        with httpx.Client(
            timeout=12, headers=HEADERS, follow_redirects=False
        ) as client:
            for _ in range(4):
                if not allowed_thumbnail(url):
                    return None
                with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = str(response.url.join(response.headers["location"]))
                        continue
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 4 * 1024 * 1024:
                            return None
                        chunks.append(chunk)
                    with Image.open(BytesIO(b"".join(chunks))) as image:
                        if image.width * image.height > 16_000_000:
                            return None
                        image = image.convert("RGB")
                        image.thumbnail((640, 640))
                        pixels = np.asarray(image)[:, :, ::-1].copy()
                        filename = candidate["id"] + ".jpg"
                        image.save(output / filename, format="JPEG", quality=88)
                        candidate["thumbnail"] = filename
                        return pixels
            return None
    except Exception:
        return None


def search_video(
    path: Path, output: Path, progress=lambda stage, message: None, query_override=None
):
    started = time.perf_counter()
    progress("frames", "Reading a few moments from your video")
    info, frames = sample_frames(path, output)
    progress("describe", "Describing the scenes on your computer")
    captions = caption_frames(frames) if not query_override else []
    queries = [query_override] if query_override else list(dict.fromkeys(captions))[:2]
    progress("search", "Searching YouTube and Internet Archive now")
    candidates, providers = discover(queries)
    warnings = []
    if any(s["status"] == "unavailable" for s in providers):
        warnings.append(
            "One or more live searches were unavailable. The available results are shown; no saved results were substituted."
        )
    progress("thumbnails", "Collecting preview images for visual comparison")
    with ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(lambda c: download_thumbnail(c, output), candidates))
    comparable = [(i, image) for i, image in enumerate(images) if image is not None]
    if comparable:
        progress("rank", "Comparing your frames with the video thumbnails")
        try:
            vectors = embedding.embed(
                [{"image": f["pixels"]} for f in frames]
                + [{"image": image} for _, image in comparable]
            )
            query_vectors = vectors[: len(frames)]
            for (index, _), vector in zip(comparable, vectors[len(frames) :]):
                similarities = query_vectors @ vector
                best = int(similarities.argmax())
                candidates[index]["similarity"] = round(float(similarities[best]), 4)
                candidates[index]["matchedFrame"] = best
            candidates.sort(key=lambda c: c.get("similarity", -2), reverse=True)
        except Exception:
            warnings.append(
                "Visual ranking could not finish. These are live search results in discovery order, without similarity scores."
            )
    for candidate in candidates:
        candidate.pop("thumbnailUrl", None)
    return {
        "schemaVersion": "internet-1",
        "searchedAt": datetime.now(timezone.utc).isoformat(),
        "query": {
            "filename": path.name,
            "duration": info["duration"],
            "sha256": sha256(path),
        },
        "queries": queries,
        "captions": captions,
        "frames": [{"time": f["time"], "image": f["image"]} for f in frames],
        "results": candidates,
        "providers": providers,
        "warnings": warnings,
        "elapsedSeconds": round(time.perf_counter() - started, 2),
        "rankingModel": embedding.MODEL_ID,
        "captionModel": CAPTION_MODEL,
        "limitation": "Similarity compares sampled frames with search-result thumbnails. It does not verify a full video, original source, ownership, or permission to reuse.",
    }
