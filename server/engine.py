"""Semantic candidate retrieval followed by geometric and temporal verification."""

from pathlib import Path
import json
import hashlib
from collections import OrderedDict
import time
import cv2
import numpy as np
from .media import Frame, extract, describe, probe, verify, sha256
from .temporal import fit_temporal
from . import embedding

ROOT = Path(__file__).resolve().parents[1]
_fingerprint = hashlib.sha256()
for _filename in ("media.py", "temporal.py", "embedding.py", "engine.py"):
    _fingerprint.update((ROOT / "server" / _filename).read_bytes())
ENGINE_FINGERPRINT = _fingerprint.hexdigest()
INDEX = ROOT / "data/index"
MANIFEST = ROOT / "public/manifest.json"
USER_LIBRARY = ROOT / "data/library.json"
_library = None
_dense_cache = OrderedDict()


def dense_frames(entry):
    sid = entry["source"]["id"]
    if sid not in _dense_cache:
        _dense_cache[sid] = extract(source_path(entry["source"]), fps=4)
        while len(_dense_cache) > 2:
            _dense_cache.popitem(last=False)
    _dense_cache.move_to_end(sid)
    return _dense_cache[sid]


def quality(match):
    return min(match["inliers"], 100) * match.get("photometricCorrelation", 1)


def sources():
    bundled = json.loads(MANIFEST.read_text())["sources"]
    custom = json.loads(USER_LIBRARY.read_text()) if USER_LIBRARY.exists() else []
    return bundled + custom


def source_path(source):
    if source.get("userProvided"):
        return ROOT / "data/sources" / source["id"] / "video.mp4"
    return ROOT / "public" / source["url"].lstrip("/")


def index_source(source, progress=print):
    sid = source["id"]
    path = source_path(source)
    progress(f"Indexing {source['title']}")
    frames = extract(path, fps=1)
    directory = INDEX / sid
    directory.mkdir(parents=True, exist_ok=True)
    payload = {}
    for i, f in enumerate(frames):
        cv2.imwrite(
            str(directory / f"{i:03}.jpg"), f.image, [cv2.IMWRITE_JPEG_QUALITY, 88]
        )
        payload[f"points_{i}"] = f.points
        payload[f"desc_{i}"] = (
            f.descriptors
            if f.descriptors is not None
            else np.empty((0, 32), dtype=np.uint8)
        )
    payload["times"] = np.array([f.time for f in frames])
    payload["signatures"] = np.stack([f.signature for f in frames])
    np.savez_compressed(directory / "visual.npz", **payload)
    sampled = list(range(0, len(frames), 4))
    vectors = embedding.embed([{"image": frames[i].image} for i in sampled])
    np.savez_compressed(
        directory / "semantic.npz",
        vectors=vectors,
        times=np.array([frames[i].time for i in sampled]),
    )
    return dict(
        id=sid, sha256=sha256(path), frames=len(frames), semanticFrames=len(sampled)
    )


def register_source(source, progress=print):
    record = index_source(source, progress)
    custom = json.loads(USER_LIBRARY.read_text()) if USER_LIBRARY.exists() else []
    custom.append(source)
    temporary = USER_LIBRARY.with_suffix(".tmp")
    temporary.write_text(json.dumps(custom, indent=2))
    temporary.replace(USER_LIBRARY)
    global _library
    _library = None
    return record


def build_index(progress=print):
    INDEX.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sources():
        records.append(index_source(source, progress))
    (INDEX / "metadata.json").write_text(
        json.dumps(
            dict(
                model=embedding.MODEL_ID,
                revision=embedding.MODEL_REVISION,
                sources=records,
            ),
            indent=2,
        )
    )
    global _library
    _library = None
    return records


def load_library():
    global _library
    if _library is not None:
        return _library
    library = []
    for source in sources():
        directory = INDEX / source["id"]
        if not (directory / "visual.npz").exists():
            raise RuntimeError(
                "Source index is missing. Run python -m server.index first."
            )
        with np.load(directory / "visual.npz", allow_pickle=False) as data:
            frames = []
            for i, t in enumerate(data["times"]):
                image = cv2.imread(str(directory / f"{i:03}.jpg"))
                desc = data[f"desc_{i}"]
                frames.append(
                    Frame(
                        float(t),
                        image,
                        data[f"points_{i}"],
                        desc if len(desc) else None,
                        data["signatures"][i],
                    )
                )
        with np.load(directory / "semantic.npz", allow_pickle=False) as data:
            vectors = data["vectors"]
            times = data["times"]
        library.append(dict(source=source, frames=frames, vectors=vectors, times=times))
    _library = library
    return library


def semantic_search(text: str):
    library = load_library()
    vector = embedding.embed([{"text": text}])[0]
    results = []
    for entry in library:
        similarity = entry["vectors"] @ vector
        for i in np.argsort(similarity)[::-1][:3]:
            results.append(
                dict(
                    sourceId=entry["source"]["id"],
                    time=float(entry["times"][i]),
                    similarity=round(float(similarity[i]), 4),
                )
            )
    return sorted(results, key=lambda r: r["similarity"], reverse=True)[:8]


def analyze(
    path: Path, output: Path, progress=lambda stage, message: None, use_semantic=True
):
    started = time.perf_counter()
    cv2.setNumThreads(2)
    output.mkdir(parents=True, exist_ok=True)
    progress("extract", "Reading clip and extracting visual features")
    info = probe(path)
    query = extract(path, fps=2)
    library = load_library()
    retrieval = []
    if use_semantic:
        progress("retrieve", "Finding candidate moments with Qwen3-VL-Embedding")
        sample_indices = np.linspace(0, len(query) - 1, min(3, len(query)), dtype=int)
        vectors = embedding.embed([{"image": query[i].image} for i in sample_indices])
        for entry in library:
            similarities = vectors @ entry["vectors"].T
            retrieval.append(
                dict(
                    sourceId=entry["source"]["id"],
                    similarity=round(float(similarities.max(axis=1).mean()), 4),
                    moments=[
                        float(entry["times"][i])
                        for i in np.argsort(similarities.max(axis=0))[::-1][:4]
                    ],
                )
            )
        retrieval.sort(key=lambda r: r["similarity"], reverse=True)
        # Small libraries deliberately retain all candidates. Semantic ranking sets
        # verification order; a low semantic score must not conceal a true match.
        byid = {entry["source"]["id"]: entry for entry in library}
        library = [byid[r["sourceId"]] for r in retrieval]
    results = []
    progress("verify", "Checking shared visual features and consistent timestamps")
    flipped = [describe(cv2.flip(f.image, 1), f.time) for f in query]
    for candidate_index, entry in enumerate(library):
        best = []
        for qi, q in enumerate(query):
            if qi % 4 == 0:
                progress(
                    "verify",
                    f"Candidate {candidate_index + 1}/{len(library)} · {entry['source']['title']} · frame {qi + 1}/{len(query)}",
                )
            candidates = []
            for sf in entry["frames"]:
                match = verify(q, sf)
                # Mirror fallback only when unmirrored evidence is weak.
                if match is None or match["inliers"] < 18:
                    alternative = verify(flipped[qi], sf)
                    if alternative and (
                        match is None or alternative["inliers"] > match["inliers"]
                    ):
                        match = alternative
                        match["mirrored"] = True
                        for point in match["points"]:
                            point["query"][0] = round(1 - point["query"][0], 5)
                if match:
                    candidates.append(match)
            best.extend(sorted(candidates, key=quality, reverse=True)[:4])
        # A single edit cannot be both mirrored and unmirrored at the same time.
        # Fit the two orientations separately instead of mixing weak coincidences.
        hypotheses = [
            fit_temporal([m for m in best if m["mirrored"] == mirror])
            for mirror in (False, True)
        ]
        hypotheses = [h for h in hypotheses if h is not None]
        temporal = (
            max(
                hypotheses,
                key=lambda h: (h["support"], sum(m["inliers"] for m in h["matches"])),
            )
            if hypotheses
            else None
        )
        if temporal is None:
            continue
        if temporal["support"] < 4:
            continue
        # Search the full source at higher resolution; a wrong coarse offset
        # must not trap refinement in the wrong moment.
        progress(
            "refine",
            f"Refining timestamps in {entry['source']['title']} at 4 frames/second",
        )
        fine = dense_frames(entry)
        mirrored = bool(temporal["matches"][0]["mirrored"])
        fine_matches = []
        for qi, q in enumerate(flipped if mirrored else query):
            if qi % 4 == 0:
                progress(
                    "refine",
                    f"Refining {entry['source']['title']} · frame {qi + 1}/{len(query)}",
                )
            candidates = []
            for sf in fine:
                match = verify(q, sf)
                if match:
                    match["mirrored"] = mirrored
                    if mirrored:
                        for point in match["points"]:
                            point["query"][0] = round(1 - point["query"][0], 5)
                    candidates.append(match)
            fine_matches.extend(sorted(candidates, key=quality, reverse=True)[:6])
        refined = fit_temporal(fine_matches, tolerance=0.2)
        evidence_frames = entry["frames"]
        if refined and refined["support"] >= 4:
            temporal = refined
            evidence_frames = fine
        else:
            temporal["speedReliable"] = False
            temporal["refinementFailed"] = True
        support = temporal["support"]
        coverage = round(support / len(query), 4)
        if support < 4 or coverage < 0.2:
            continue
        if (
            temporal["sourceStart"] < -0.65
            or temporal["sourceEnd"] > entry["source"]["duration"] + 0.65
        ):
            continue
        evidence = sorted(
            temporal["matches"], key=lambda m: m["inliers"], reverse=True
        )[:6]
        for i, m in enumerate(evidence):
            qframe = min(query, key=lambda f: abs(f.time - m["queryTime"]))
            sframe = min(evidence_frames, key=lambda f: abs(f.time - m["sourceTime"]))
            prefix = f"{entry['source']['id']}-{i}"
            cv2.imwrite(str(output / f"{prefix}-query.jpg"), qframe.image)
            cv2.imwrite(str(output / f"{prefix}-source.jpg"), sframe.image)
            m["queryImage"] = f"{prefix}-query.jpg"
            m["sourceImage"] = f"{prefix}-source.jpg"
        compact = [
            {
                k: v
                for k, v in m.items()
                if k not in ["points", "quad", "queryImage", "sourceImage"]
            }
            for m in temporal["matches"]
        ]
        temporal["matches"] = compact
        results.append(
            dict(
                source=entry["source"],
                alignment=temporal,
                coverage=coverage,
                medianInliers=int(np.median([m["inliers"] for m in compact])),
                evidence=evidence,
                verdict="strong" if support >= 6 and coverage >= 0.5 else "partial",
            )
        )
    results.sort(
        key=lambda r: (r["alignment"]["support"], r["medianInliers"]), reverse=True
    )
    progress("package", "Building a reproducible evidence packet")
    filenames = sorted(
        {
            m[key]
            for result in results
            for m in result["evidence"]
            for key in ("queryImage", "sourceImage")
        }
    )
    assets = [dict(file=name, sha256=sha256(output / name)) for name in filenames]
    report = dict(
        schemaVersion="1.1",
        engineFingerprint=ENGINE_FINGERPRINT,
        evidenceAssets=assets,
        query=dict(
            filename=path.name,
            sha256=sha256(path),
            duration=round(info["duration"], 3),
            width=info["width"],
            height=info["height"],
            sampledFrames=len(query),
        ),
        retrieval=dict(
            engine=embedding.MODEL_ID if use_semantic else "visual-only",
            revision=embedding.MODEL_REVISION if use_semantic else None,
            rankings=retrieval,
        ),
        results=results,
        elapsedSeconds=round(time.perf_counter() - started, 2),
        method=dict(
            visual="ORB + unique ratio matches + RANSAC homography + aligned appearance correlation",
            temporal="Weighted linear timestamp consensus",
            sourceSampleFps=1,
            querySampleFps=2,
            refinementFps=4,
            toleranceSeconds=0.65,
        ),
        limitations=[
            "Search is limited to the indexed source library.",
            "A visual match is evidence of shared imagery, not proof of ownership, infringement, or first publication.",
            "Source frames are sampled at 1 fps, then verified candidates are refined at 4 fps. Per-alignment tolerances are not guaranteed error bounds or statistical confidence intervals.",
            "Semantic similarities are uncalibrated retrieval scores, not probabilities.",
            "The playback speed range is a deterministic consistency interval under the timestamp tolerance, not a calibrated confidence interval.",
        ],
    )
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report
