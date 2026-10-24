"""Exercise real source ingestion, semantic search and analysis over localhost HTTP.

Uses separately prepared licensed test clips; never mocks model inference.
The caller may retain or remove the source after inspecting the saved result.
"""

import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/live-smoke"
client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=150)


def wait(job_id):
    previous = None
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        response = client.get("/api/jobs/" + job_id)
        response.raise_for_status()
        job = response.json()
        if job.get("message") != previous:
            print(job.get("message"), flush=True)
            previous = job.get("message")
        if job["status"] == "failed":
            raise RuntimeError(job.get("error"))
        if job["status"] == "complete":
            return job
        time.sleep(2)
    raise RuntimeError("Job exceeded the smoke-test deadline")


with (OUT / "source.mp4").open("rb") as f:
    response = client.post(
        "/api/sources",
        files={"file": ("sintel-source.mp4", f, "video/mp4")},
        data={
            "title": "Sintel · independent ingestion test",
            "creator": "Blender Foundation | durian.blender.org",
            "license": "CC BY 3.0",
        },
    )
response.raise_for_status()
source_job = wait(response.json()["id"])
source = source_job["source"]
(OUT / "source-result.json").write_text(json.dumps(source_job, indent=2))
assert client.get(source["url"]).status_code == 200
search = client.post(
    "/api/search", json={"query": "An animated young woman in a snowy landscape"}
)
search.raise_for_status()
(OUT / "search-result.json").write_text(json.dumps(search.json(), indent=2))
for hit in search.json()["results"]:
    frame = client.get(f"/api/frames/{hit['sourceId']}/{int(hit['time'])}")
    assert frame.status_code == 200, hit
with (OUT / "query.mp4").open("rb") as f:
    response = client.post(
        "/api/analyze", files={"file": ("edited-sintel.mp4", f, "video/mp4")}
    )
response.raise_for_status()
job_id = response.json()["id"]
result = wait(job_id)
(OUT / "analysis-result.json").write_text(json.dumps(result, indent=2))
report = result["report"]
expected = next(
    (m for m in report["results"] if m["source"]["id"] == source["id"]), None
)
assert expected is not None, "Newly indexed source was not recovered"
assert all(m["source"]["id"] == source["id"] for m in report["results"]), (
    "Unexpected source match"
)
for asset in report["evidenceAssets"]:
    response = client.get(f"/api/evidence/{job_id}/{asset['file']}")
    response.raise_for_status()
    import hashlib

    assert hashlib.sha256(response.content).hexdigest() == asset["sha256"]
summary = {
    "sourceId": source["id"],
    "jobId": job_id,
    "newSourceRecovered": True,
    "falseMatches": 0,
    "sourceStart": expected["alignment"]["sourceStart"],
    "speed": expected["alignment"]["speed"],
    "offsetError": abs(expected["alignment"]["offset"] - 4),
    "speedError": abs(expected["alignment"]["speed"] - 1.2),
    "verifiedFrames": expected["alignment"]["support"],
    "retrievalTop1": report["retrieval"]["rankings"][0]["sourceId"] == source["id"],
    "evidenceChecksumsVerified": len(report["evidenceAssets"]),
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2), flush=True)
