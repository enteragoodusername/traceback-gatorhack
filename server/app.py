"""Local-only API for real uploads, model retrieval and evidence exports."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any
import json
import os
import shutil
import time
import uuid
import httpx

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .engine import analyze, semantic_search, sources, register_source, INDEX, ROOT
from .media import MAX_SIZE, probe, sha256
from . import embedding, integrations

app = FastAPI(
    title="Traceback",
    version="0.1.0",
    description="Local video provenance analysis. Search is limited to your indexed library.",
)
UPLOADS = ROOT / "data/uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="traceback")
jobs: dict[str, dict[str, Any]] = {}
jobs_lock = Lock()


@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    # Browser requests from unrelated origins cannot trigger paid sponsor calls
    # or uploads on a local server. CLI clients have no Origin.
    if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
        from urllib.parse import urlparse

        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https") or parsed.hostname not in (
            "127.0.0.1",
            "localhost",
            "[::1]",
            "::1",
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "This local API only accepts requests from localhost."},
                status_code=403,
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "semantic": embedding.available(),
        "indexReady": (INDEX / "metadata.json").exists(),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "twinly": bool(os.getenv("TWINLY_API_KEY")),
        "version": "0.1.0",
    }


@app.get("/api/library")
def library():
    return {"sources": sources()}


@app.post("/api/sources", status_code=202)
def add_source(
    file: UploadFile = File(...),
    title: str = Form(...),
    creator: str = Form("User provided"),
    license: str = Form("Rights unverified"),
):
    import subprocess
    import cv2

    if not embedding.available():
        raise HTTPException(
            503, "Enable the local semantic model before indexing a source."
        )
    title = title.strip()[:100]
    creator = creator.strip()[:100] or "User provided"
    if not title:
        raise HTTPException(400, "A source title is required.")
    if license not in (
        "Rights unverified",
        "All rights reserved",
        "CC BY 3.0",
        "CC BY 4.0",
        "CC0",
    ):
        raise HTTPException(400, "Choose a supported license label.")
    job_id = uuid.uuid4().hex
    with jobs_lock:
        if any(
            j["status"] in ("uploading", "queued", "running") for j in jobs.values()
        ):
            raise HTTPException(
                429, "Wait for the current job to finish before adding a source."
            )
        jobs[job_id] = {
            "id": job_id,
            "status": "uploading",
            "kind": "source",
            "createdAt": time.time(),
            "message": "Receiving source",
        }
    sid = "user-" + uuid.uuid4().hex
    directory = ROOT / "data/sources" / sid
    directory.mkdir(parents=True)
    incoming = directory / "incoming"
    path = directory / "video.mp4"
    total = 0
    try:
        with incoming.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_SIZE:
                    raise HTTPException(413, "Source must be smaller than 100 MB.")
                out.write(chunk)
        input_sha256 = sha256(incoming)
        info = probe(incoming)
        if not 2 <= info["duration"] <= 60.1:
            raise HTTPException(400, "Use a source between 2 and 60 seconds long.")
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(incoming),
                "-an",
                "-vf",
                "scale=min(960\\,iw):-2",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-movflags",
                "+faststart",
                str(path),
            ],
            check=True,
            timeout=90,
        )
        incoming.unlink()
        cap = cv2.VideoCapture(str(path))
        cap.set(cv2.CAP_PROP_POS_MSEC, min(3, info["duration"] / 2) * 1000)
        ok, image = cap.read()
        cap.release()
        if not ok:
            raise ValueError("Could not read the source thumbnail.")
        cv2.imwrite(str(directory / "thumbnail.jpg"), image)
    except (ValueError, subprocess.SubprocessError, HTTPException) as exc:
        shutil.rmtree(directory, ignore_errors=True)
        with jobs_lock:
            jobs.pop(job_id, None)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(400, "Could not prepare this source video.") from exc
    finally:
        file.file.close()
    license_url = {
        "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
        "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
        "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    }
    source = dict(
        id=sid,
        title=title,
        description="Locally indexed, user-provided source. Rights metadata is supplied by the uploader.",
        category="Your library",
        duration=info["duration"],
        originalOffset=0,
        url=f"/api/sources/{sid}/video.mp4",
        thumbnail=f"/api/sources/{sid}/thumbnail.jpg",
        sha256=sha256(path),
        inputSha256=input_sha256,
        creator=creator,
        work=title,
        license=license,
        licenseUrl=license_url.get(license, ""),
        sourceUrl="",
        userProvided=True,
    )
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "stage": "index",
            "message": "Preparing the source index",
            "createdAt": time.time(),
            "kind": "source",
        }

    def task():
        with jobs_lock:
            jobs[job_id]["status"] = "running"
        try:
            register_source(source)
            with jobs_lock:
                jobs[job_id].update(
                    status="complete", source=source, message="Source indexed"
                )
        except Exception:
            with jobs_lock:
                jobs[job_id].update(
                    status="failed",
                    error="Could not index this source. See the local server log.",
                )
            import traceback

            traceback.print_exc()

    pool.submit(task)
    return {"id": job_id, "status": "queued"}


@app.get("/api/sources/{source_id}/{filename}")
def source_asset(source_id: str, filename: str):
    if (
        not source_id.startswith("user-")
        or len(source_id) != 37
        or not all(c in "0123456789abcdef" for c in source_id[5:])
    ):
        raise HTTPException(404)
    if filename not in ("video.mp4", "thumbnail.jpg"):
        raise HTTPException(404)
    path = ROOT / "data/sources" / source_id / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


def work(job_id: str, path: Path):
    def progress(stage, message):
        with jobs_lock:
            jobs[job_id].update(stage=stage, message=message)

    try:
        report = analyze(
            path,
            UPLOADS / job_id / "evidence",
            progress,
            use_semantic=embedding.available(),
        )
        report["query"]["filename"] = jobs[job_id]["filename"]
        report["recorded"] = False
        stored = UPLOADS / job_id / "evidence/report.json"
        temporary = stored.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2))
        temporary.replace(stored)
        with jobs_lock:
            jobs[job_id].update(
                status="complete",
                stage="complete",
                message="Analysis complete",
                report=report,
            )
    except Exception as exc:
        with jobs_lock:
            jobs[job_id].update(
                status="failed",
                stage="failed",
                message="Analysis failed",
                error=str(exc)
                if isinstance(exc, (ValueError, RuntimeError))
                else "Could not complete this analysis. See the local server log.",
            )
        import traceback

        traceback.print_exc()


@app.post("/api/analyze", status_code=202)
async def start_analysis(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".webm", ".mkv", ".m4v"}:
        raise HTTPException(400, "Use an MP4, MOV, WebM, or MKV file.")
    job_id = uuid.uuid4().hex
    with jobs_lock:
        if (
            sum(
                j["status"] in ("uploading", "queued", "running") for j in jobs.values()
            )
            >= 2
        ):
            raise HTTPException(
                429, "Two analyses are already queued. Wait for one to finish."
            )
        jobs[job_id] = {
            "id": job_id,
            "status": "uploading",
            "message": "Receiving clip",
            "createdAt": time.time(),
        }
    directory = UPLOADS / job_id
    directory.mkdir()
    path = directory / ("query" + suffix)
    total = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_SIZE:
                    raise HTTPException(413, "Video must be smaller than 100 MB.")
                out.write(chunk)
        info = probe(path)
        if info["duration"] > 60.1:
            raise HTTPException(400, "Video must be 60 seconds or shorter.")
        if info["duration"] < 2:
            raise HTTPException(400, "Video must be at least 2 seconds long.")
    except (ValueError, HTTPException) as exc:
        shutil.rmtree(directory, ignore_errors=True)
        with jobs_lock:
            jobs.pop(job_id, None)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(400, str(exc)) from exc
    finally:
        await file.close()
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "stage": "queued",
            "message": "Waiting for the local engine",
            "filename": Path(file.filename or "clip").name[:200],
            "createdAt": time.time(),
        }

    def task():
        with jobs_lock:
            jobs[job_id]["status"] = "running"
        work(job_id, path)

    pool.submit(task)
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            if len(job_id) == 32 and all(c in "0123456789abcdef" for c in job_id):
                stored = UPLOADS / job_id / "evidence/report.json"
                if stored.is_file():
                    report = json.loads(stored.read_text())
                    report["recorded"] = False
                    return {
                        "id": job_id,
                        "status": "complete",
                        "message": "Completed analysis restored from disk",
                        "report": report,
                    }
            raise HTTPException(404, "Analysis not found.")
        return dict(jobs[job_id])


@app.get("/api/query/{job_id}")
def original_query(job_id: str):
    if len(job_id) != 32 or not all(c in "0123456789abcdef" for c in job_id):
        raise HTTPException(404, "Query not found.")
    directory = UPLOADS / job_id
    for suffix in (".mp4", ".mov", ".webm", ".mkv", ".m4v"):
        path = directory / ("query" + suffix)
        if path.is_file():
            return FileResponse(path)
    raise HTTPException(404, "Query not found.")


@app.get("/api/evidence/{job_id}/{filename}")
def evidence(job_id: str, filename: str):
    if len(job_id) != 32 or not all(c in "0123456789abcdef" for c in job_id):
        raise HTTPException(404)
    if Path(filename).name != filename or Path(filename).suffix not in {
        ".jpg",
        ".json",
    }:
        raise HTTPException(404)
    path = UPLOADS / job_id / "evidence" / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


@app.get("/api/frames/{source_id}/{second}")
def indexed_frame(source_id: str, second: int):
    # Semantic hits refer to the 1 fps visual index. Never substitute an
    # unrelated thumbnail while displaying a precise retrieved timestamp.
    if second < 0 or second > 60 or not any(s["id"] == source_id for s in sources()):
        raise HTTPException(404, "Indexed frame not found.")
    import numpy as np

    directory = INDEX / source_id
    metadata = directory / "visual.npz"
    if not metadata.is_file():
        raise HTTPException(404, "Indexed frame not found.")
    with np.load(metadata, allow_pickle=False) as data:
        positions = np.flatnonzero(np.isclose(data["times"], second))
    if not len(positions):
        raise HTTPException(404, "Indexed frame not found.")
    path = directory / f"{int(positions[0]):03}.jpg"
    if not path.is_file():
        raise HTTPException(404, "Indexed frame not found.")
    return FileResponse(path)


@app.post("/api/search")
def search(request: SearchRequest):
    try:
        return {"results": semantic_search(request.query), "engine": embedding.MODEL_ID}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(503, str(exc)) from exc


class ExplainRequest(BaseModel):
    report: dict


def validate_report(report):
    try:
        if len(json.dumps(report)) > 500_000:
            raise ValueError("Report is too large.")
        facts = integrations.summary_facts(report)
        if not isinstance(facts["durationSeconds"], (int, float)):
            raise ValueError("Invalid duration.")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(400, "Invalid evidence report.") from exc


@app.post("/api/explain")
async def explain(request: ExplainRequest):
    validate_report(request.report)
    try:
        return {
            "text": await integrations.explain(request.report),
            "provider": "Gemini",
            "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        }
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            503,
            "The provider could not be reached. Check your connection and try again.",
        ) from exc


@app.get("/api/twinly/readiness")
async def twinly_readiness():
    try:
        return await integrations.twinly_readiness()
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            503,
            "The provider could not be reached. Check your connection and try again.",
        ) from exc


@app.post("/api/twinly/review")
async def twinly_review(request: ExplainRequest):
    validate_report(request.report)
    try:
        return {
            "text": await integrations.twinly_review(request.report),
            "provider": "Twinly",
        }
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            503,
            "The provider could not be reached. Check your connection and try again.",
        ) from exc


# A built frontend makes the complete application a single localhost service.
if (ROOT / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")
