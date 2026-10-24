"""Long-video selection uses actual FFmpeg output, never a saved answer."""

import importlib
import subprocess
import cv2
import pytest
from fastapi.testclient import TestClient
from server.media import probe

api = importlib.import_module("server.app")
client = TestClient(api.app)


@pytest.fixture(scope="module")
def long_video(tmp_path_factory):
    path = tmp_path_factory.mktemp("long-video") / "two-scenes.mp4"
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
            "color=red:size=160x90:rate=10:duration=70",
            "-f",
            "lavfi",
            "-i",
            "color=blue:size=160x90:rate=10:duration=10",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


@pytest.fixture
def pending(monkeypatch, tmp_path, long_video):
    monkeypatch.setattr(api, "UPLOADS", tmp_path)
    monkeypatch.setattr(api, "jobs", {})
    callbacks = []

    class Queue:
        def submit(self, callback):
            callbacks.append(callback)

    monkeypatch.setattr(api, "pool", Queue())
    r = client.post(
        "/api/search-video", files={"file": ("two-scenes.mp4", long_video, "video/mp4")}
    )
    assert r.status_code == 202
    assert r.json()["status"] == "needs_trim"
    assert callbacks == []  # No model work until the user chooses.
    return r.json()["id"], callbacks


def test_selected_pixels_only_reach_search_and_survive_refinement(
    pending, monkeypatch, tmp_path, long_video
):
    job, callbacks = pending
    assert client.get(f"/api/input/{job}").content == long_video
    ranged = client.get(f"/api/input/{job}", headers={"Range": "bytes=0-19"})
    assert ranged.status_code == 206 and len(ranged.content) == 20
    assert client.get(f"/api/query/{job}").status_code == 404
    api.jobs.clear()  # An unfinished selection survives restart.
    assert client.get(f"/api/jobs/{job}").json()["duration"] == 80
    seen = []

    def search(path, output, progress, query_override=None):
        info = probe(path)
        seen.append(path)
        assert info["duration"] == pytest.approx(8, abs=0.1)
        cap = cv2.VideoCapture(str(path))
        ok, pixels = cap.read()
        cap.release()
        assert ok and pixels[:, :, 0].mean() > 240 and pixels[:, :, 2].mean() < 10
        return {
            "schemaVersion": "internet-1",
            "query": {"filename": path.name},
            "results": [],
            "queries": ["blue scene"],
        }

    monkeypatch.setattr(
        importlib.import_module("server.internet"), "search_video", search
    )
    selected = client.post(
        f"/api/search-video/{job}/segment", json={"start": 72, "duration": 8}
    )
    assert selected.status_code == 202 and len(callbacks) == 1
    assert (
        client.post(
            f"/api/search-video/{job}/segment", json={"start": 0, "duration": 60}
        ).status_code
        == 409
    )
    callbacks.pop()()
    result = client.get(f"/api/jobs/{job}").json()
    assert result["status"] == "complete"
    assert result["result"]["selection"] == {
        "start": 72,
        "end": 80,
        "originalDuration": 80,
        "originalFilename": "two-scenes.mp4",
    }
    assert seen == [tmp_path / job / "query.mp4"]
    assert client.get(f"/api/query/{job}").content != long_video
    api.jobs.clear()
    assert client.get(f"/api/jobs/{job}").json()["result"] == result["result"]
    assert (
        client.post(
            f"/api/search-video/{job}/segment", json={"start": 0, "duration": 60}
        ).status_code
        == 409
    )
    refined = client.post(f"/api/refine/{job}", json={"query": "blue scene"})
    assert refined.status_code == 202
    callbacks.pop()()
    assert (
        client.get(f"/api/jobs/{refined.json()['id']}").json()["result"]["selection"]
        == result["result"]["selection"]
    )


@pytest.mark.parametrize(
    "selection,status",
    [
        ({"start": -1, "duration": 60}, 422),
        ({"start": 0, "duration": 61}, 422),
        ({"start": 0, "duration": 1}, 422),
        ({"start": 75, "duration": 6}, 400),
        ({"start": "NaN", "duration": 5}, 422),
    ],
)
def test_invalid_intervals_never_start_processing(pending, selection, status):
    job, callbacks = pending
    assert (
        client.post(f"/api/search-video/{job}/segment", json=selection).status_code
        == status
    )
    assert callbacks == []


def test_failed_trim_is_retryable_and_queue_limit_applies(pending, monkeypatch):
    job, callbacks = pending
    api.jobs.update({"x": {"status": "running"}, "y": {"status": "queued"}})
    url = f"/api/search-video/{job}/segment"
    selection = {"start": 20, "duration": 60}
    assert client.post(url, json=selection).status_code == 429
    assert callbacks == []
    api.jobs.pop("x")
    api.jobs.pop("y")

    def broken(*args):
        raise RuntimeError("Decoder failed")

    monkeypatch.setattr(api, "trim_video", broken)
    assert client.post(url, json=selection).status_code == 202
    callbacks.pop()()
    assert client.get(f"/api/jobs/{job}").json()["status"] == "failed"
    assert client.post(url, json=selection).status_code == 202


def test_full_sixty_seconds_can_end_at_last_frame(pending, monkeypatch):
    job, callbacks = pending

    def verify(job_id, path):
        assert probe(path)["duration"] == pytest.approx(60, abs=0.1)

    monkeypatch.setattr(api, "internet_work", verify)
    assert (
        client.post(
            f"/api/search-video/{job}/segment", json={"start": 20, "duration": 60}
        ).status_code
        == 202
    )
    callbacks.pop()()
    assert (api.UPLOADS / job / "clip.json").is_file()
