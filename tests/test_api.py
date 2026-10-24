from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


def test_health_never_exposes_credentials(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-value")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["gemini"] is True
    assert "private-test-value" not in response.text


def test_rejects_non_video_upload():
    response = client.post(
        "/api/analyze", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_rejects_invalid_video_bytes():
    response = client.post(
        "/api/analyze", files={"file": ("clip.mp4", b"not a video", "video/mp4")}
    )
    assert response.status_code == 400
    assert "supported video" in response.json()["detail"]


def test_foreign_origins_cannot_invoke_local_api():
    response = client.post(
        "/api/search",
        json={"query": "test"},
        headers={"origin": "https://unrelated.example"},
    )
    assert response.status_code == 403


def test_unknown_job_and_invalid_evidence_path():
    assert client.get("/api/jobs/unknown").status_code == 404
    assert client.get("/api/evidence/not-an-id/secret.json").status_code == 404


def test_explanation_requires_valid_evidence():
    assert client.post("/api/explain", json={"report": {}}).status_code == 400


def test_missing_twinly_credentials_is_explicit(monkeypatch):
    monkeypatch.delenv("TWINLY_API_KEY", raising=False)
    response = client.get("/api/twinly/readiness")
    assert response.status_code == 503
    assert "TWINLY_API_KEY" in response.json()["detail"]


def test_invalid_source_releases_queue_reservation(monkeypatch, tmp_path):
    import importlib

    module = importlib.import_module("server.app")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.embedding, "available", lambda: True)
    monkeypatch.setattr(module, "jobs", {})
    response = client.post(
        "/api/sources",
        data={"title": "Test source"},
        files={"file": ("test.mp4", b"not video", "video/mp4")},
    )
    assert response.status_code == 400
    assert module.jobs == {}
    assert list((tmp_path / "data/sources").glob("*")) == []


def test_source_ingestion_respects_in_progress_upload(monkeypatch):
    import importlib

    module = importlib.import_module("server.app")
    monkeypatch.setattr(module.embedding, "available", lambda: True)
    monkeypatch.setattr(module, "jobs", {"inflight": {"status": "uploading"}})
    response = client.post(
        "/api/sources",
        data={"title": "Test source"},
        files={"file": ("test.mp4", b"not video", "video/mp4")},
    )
    assert response.status_code == 429


def test_completed_job_restores_evidence_after_restart(monkeypatch, tmp_path):
    import importlib
    import json

    module = importlib.import_module("server.app")
    monkeypatch.setattr(module, "UPLOADS", tmp_path)
    monkeypatch.setattr(module, "jobs", {})
    job_id = "a" * 32
    folder = tmp_path / job_id / "evidence"
    folder.mkdir(parents=True)
    (folder / "report.json").write_text(
        json.dumps({"query": {"duration": 4}, "results": []})
    )
    response = client.get("/api/jobs/" + job_id)
    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    assert response.json()["report"]["recorded"] is False


def test_semantic_frame_uses_timestamp_not_assumed_position(monkeypatch, tmp_path):
    import importlib
    import numpy as np

    module = importlib.import_module("server.app")
    monkeypatch.setattr(module, "INDEX", tmp_path)
    monkeypatch.setattr(module, "sources", lambda: [{"id": "example"}])
    folder = tmp_path / "example"
    folder.mkdir()
    np.savez(folder / "visual.npz", times=np.array([0.0, 2.0, 3.0]))
    (folder / "001.jpg").write_bytes(b"correct-frame")
    assert client.get("/api/frames/example/2").content == b"correct-frame"
    assert client.get("/api/frames/example/1").status_code == 404
    assert client.get("/api/frames/unknown/2").status_code == 404


def test_source_normalization_preserves_original_upload_identity(monkeypatch, tmp_path):
    import hashlib
    import importlib
    import subprocess

    module = importlib.import_module("server.app")
    source = tmp_path / "submitted.mp4"
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
            "testsrc2=size=320x180:rate=24:duration=2",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            str(source),
        ],
        check=True,
    )
    payload = source.read_bytes()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "jobs", {})
    monkeypatch.setattr(module.embedding, "available", lambda: True)
    registered = []
    monkeypatch.setattr(
        module, "register_source", lambda record: registered.append(record)
    )

    class Immediate:
        def submit(self, callback):
            callback()

    monkeypatch.setattr(module, "pool", Immediate())
    response = client.post(
        "/api/sources",
        data={"title": "Original test pattern", "creator": "   ", "license": "CC0"},
        files={"file": ("submitted.mp4", payload, "video/mp4")},
    )
    assert response.status_code == 202
    result = client.get("/api/jobs/" + response.json()["id"]).json()
    assert result["status"] == "complete"
    record = result["source"]
    assert record["inputSha256"] == hashlib.sha256(payload).hexdigest()
    normalized = tmp_path / "data/sources" / record["id"] / "video.mp4"
    assert record["sha256"] == hashlib.sha256(normalized.read_bytes()).hexdigest()
    assert record["creator"] == "User provided"
    assert registered[0] == record


def test_saved_query_endpoint_serves_only_the_original_video(monkeypatch, tmp_path):
    import importlib

    module = importlib.import_module("server.app")
    monkeypatch.setattr(module, "UPLOADS", tmp_path)
    job_id = "c" * 32
    folder = tmp_path / job_id
    folder.mkdir()
    (folder / "query.mp4").write_bytes(b"original-query-video")
    (folder / "private.txt").write_bytes(b"not-a-query")
    assert client.get("/api/query/" + job_id).content == b"original-query-video"
    assert client.get("/api/query/not-an-id").status_code == 404
    assert client.get("/api/query/" + "d" * 32).status_code == 404
