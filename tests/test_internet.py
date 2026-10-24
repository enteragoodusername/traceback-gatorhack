"""Tests mock external services; none of these answers ship in the application."""

import importlib
import json
import subprocess
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from server import internet
from server.app import app

client = TestClient(app)


def test_parse_public_video_results_rejects_ads_and_invalid_ids():
    video = {
        "videoId": "abcdefghijk",
        "title": {"runs": [{"text": "A real video title"}]},
        "ownerText": {"runs": [{"text": "Uploader"}]},
        "lengthText": {"simpleText": "1:23"},
    }
    data = {
        "contents": [
            {"videoRenderer": video},
            {"videoRenderer": video},
            {"videoRenderer": {**video, "videoId": "../../escape"}},
            {"adSlotRenderer": {"videoRenderer": {**video, "videoId": "ZYXWVUTSRQP"}}},
        ]
    }
    result = internet.parse_youtube(
        "<script>var ytInitialData = " + json.dumps(data) + ";</script>"
    )
    assert len(result) == 1
    assert result[0]["url"] == "https://www.youtube.com/watch?v=abcdefghijk"
    assert (
        result[0]["thumbnailUrl"] == "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"
    )
    with pytest.raises(RuntimeError):
        internet.parse_youtube("Consent required")


def test_provider_failure_keeps_live_results_without_fabricating_candidates(
    monkeypatch,
):
    def unavailable(query):
        raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(internet, "youtube_search", unavailable)
    monkeypatch.setattr(
        internet,
        "archive_search",
        lambda q: [{"id": "archive-new", "provider": "Internet Archive", "title": q}],
    )
    candidates, statuses = internet.discover(["current scene"])
    assert [c["id"] for c in candidates] == ["archive-new"]
    assert statuses[0]["status"] == "unavailable"
    assert statuses[1]["status"] == "ok"


def test_all_provider_failures_return_empty_not_saved_results(monkeypatch):
    def unavailable(query):
        raise RuntimeError("Offline")

    monkeypatch.setattr(internet, "youtube_search", unavailable)
    monkeypatch.setattr(internet, "archive_search", unavailable)
    candidates, statuses = internet.discover(["unique uploaded scene"])
    assert candidates == []
    assert all(s["status"] == "unavailable" for s in statuses)


def test_thumbnail_hosts_cannot_address_local_services():
    for url in [
        "http://i.ytimg.com/vi/a.jpg",
        "https://127.0.0.1/a",
        "https://localhost/a",
        "https://archive.org.evil.example/a",
        "https://user:pass@archive.org/a",
        "https://archive.org:8000/a",
    ]:
        assert not internet.allowed_thumbnail(url)
    assert internet.allowed_thumbnail("https://ia800000.us.archive.org/image.jpg")
    assert internet.allowed_thumbnail(
        "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"
    )


def test_ranking_uses_uploaded_pixels_and_downloaded_thumbnails(monkeypatch, tmp_path):
    path = tmp_path / "new-upload.mp4"
    path.write_bytes(b"original query")
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    monkeypatch.setattr(
        internet,
        "sample_frames",
        lambda p, o: (
            {"duration": 4},
            [{"time": 2, "image": "query-0.jpg", "pixels": frame}],
        ),
    )
    monkeypatch.setattr(internet, "caption_frames", lambda f: ["a lighthouse at night"])
    seen = []

    def discover(queries):
        seen.extend(queries)
        return [
            {"id": "far", "thumbnailUrl": "unused"},
            {"id": "near", "thumbnailUrl": "unused"},
        ], []

    monkeypatch.setattr(internet, "discover", discover)
    monkeypatch.setattr(
        internet,
        "download_thumbnail",
        lambda c, o: frame + (1 if c["id"] == "far" else 2),
    )

    def embed(items):
        assert np.array_equal(items[0]["image"], frame)
        assert items[1]["image"][0, 0, 0] == 1
        assert items[2]["image"][0, 0, 0] == 2
        return np.array([[1, 0], [0, 1], [0.8, 0.6]])

    monkeypatch.setattr(internet.embedding, "embed", embed)
    result = internet.search_video(path, tmp_path)
    assert seen == ["a lighthouse at night"]
    assert [r["id"] for r in result["results"]] == ["near", "far"]
    assert result["results"][0]["similarity"] == 0.8
    assert result["results"][0]["matchedFrame"] == 0
    assert "thumbnailUrl" not in result["results"][0]
    assert result["schemaVersion"] == "internet-1"


def test_model_failure_never_fabricates_visual_scores(monkeypatch, tmp_path):
    path = tmp_path / "query.mp4"
    path.write_bytes(b"input")
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    monkeypatch.setattr(
        internet,
        "sample_frames",
        lambda p, o: (
            {"duration": 4},
            [{"time": 2, "image": "query-0.jpg", "pixels": frame}],
        ),
    )
    monkeypatch.setattr(
        internet,
        "discover",
        lambda q: ([{"id": "live-video", "thumbnailUrl": "unused"}], []),
    )
    monkeypatch.setattr(internet, "download_thumbnail", lambda c, o: frame)

    def unavailable(items):
        raise RuntimeError("Model unavailable")

    monkeypatch.setattr(internet.embedding, "embed", unavailable)
    result = internet.search_video(
        path, tmp_path, query_override="actual user refinement"
    )
    assert "similarity" not in result["results"][0]
    assert "Visual ranking could not finish" in result["warnings"][0]
    assert result["queries"] == ["actual user refinement"]


@pytest.fixture
def uploaded_video(tmp_path):
    path = tmp_path / "fresh-video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=10:duration=2",
            "-c:v",
            "libx264",
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


def test_one_file_endpoint_runs_live_worker_and_restores_user_result(
    monkeypatch, tmp_path, uploaded_video
):
    api = importlib.import_module("server.app")
    monkeypatch.setattr(api, "UPLOADS", tmp_path)
    monkeypatch.setattr(api, "jobs", {})

    class Immediate:
        def submit(self, callback):
            callback()

    monkeypatch.setattr(api, "pool", Immediate())
    calls = []

    def search(path, output, progress, query_override=None):
        calls.append(path.read_bytes())
        return {
            "schemaVersion": "internet-1",
            "query": {"filename": path.name},
            "results": [],
            "queries": [query_override or "generated scene"],
        }

    monkeypatch.setattr(internet, "search_video", search)
    response = client.post(
        "/api/search-video",
        files={"file": ("my-footage.mp4", uploaded_video, "video/mp4")},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    result = client.get("/api/jobs/" + job_id).json()
    assert result["status"] == "complete"
    assert result["result"]["query"]["filename"] == "my-footage.mp4"
    assert calls == [uploaded_video]
    api.jobs.clear()
    assert client.get("/api/jobs/" + job_id).json()["result"] == result["result"]
    refined = client.post(
        "/api/refine/" + job_id, json={"query": "more specific scene"}
    )
    assert refined.status_code == 202
    refined_id = refined.json()["id"]
    assert client.get("/api/jobs/" + refined_id).json()["result"]["queries"] == [
        "more specific scene"
    ]
    assert client.get("/api/query/" + refined_id).content == uploaded_video


def test_search_upload_rejects_bad_files_and_full_queue(monkeypatch):
    api = importlib.import_module("server.app")
    assert (
        client.post(
            "/api/search-video", files={"file": ("notes.txt", b"text")}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/search-video", files={"file": ("clip.mp4", b"invalid")}
        ).status_code
        == 400
    )
    monkeypatch.setattr(
        api, "jobs", {"a": {"status": "running"}, "b": {"status": "queued"}}
    )
    assert (
        client.post(
            "/api/search-video", files={"file": ("clip.mp4", b"invalid")}
        ).status_code
        == 429
    )


def test_search_assets_are_scoped_to_job_images(monkeypatch, tmp_path):
    api = importlib.import_module("server.app")
    monkeypatch.setattr(api, "UPLOADS", tmp_path)
    job_id = "d" * 32
    folder = tmp_path / job_id / "web"
    folder.mkdir(parents=True)
    (folder / "query-0.jpg").write_bytes(b"frame")
    (folder / "private.json").write_bytes(b"not an image")
    assert client.get(f"/api/search-assets/{job_id}/query-0.jpg").content == b"frame"
    assert client.get(f"/api/search-assets/{job_id}/private.json").status_code == 404
    assert client.get("/api/search-assets/unknown/query-0.jpg").status_code == 404
    assert (
        client.post("/api/refine/unknown", json={"query": "scene"}).status_code == 404
    )


def test_distinct_scenes_share_the_candidate_budget(monkeypatch):
    monkeypatch.setattr(
        internet,
        "youtube_search",
        lambda query: [{"id": f"{query}-{i}", "provider": "YouTube"} for i in range(8)],
    )
    monkeypatch.setattr(internet, "archive_search", lambda query: [])
    results, _ = internet.discover(["scene-one", "scene-two"])
    assert len(results) == 8
    assert sum(r["id"].startswith("scene-one") for r in results) == 4
    assert sum(r["id"].startswith("scene-two") for r in results) == 4
