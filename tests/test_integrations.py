"""Contract tests use a fake transport, never a paid provider call."""

import asyncio
import httpx
import pytest
from server import integrations
from server.app import app
from fastapi.testclient import TestClient

REPORT = {
    "query": {"duration": 9.6, "sampledFrames": 20, "filename": "private.mov"},
    "results": [
        {
            "source": {"title": "Source", "work": "Film"},
            "alignment": {
                "support": 12,
                "sourceStart": 8,
                "sourceEnd": 20,
                "speed": 1.25,
                "offset": 8,
                "residual": 0.08,
                "speedReliable": False,
                "timingAmbiguous": True,
            },
            "medianInliers": 50,
        }
    ],
}


def test_summary_preserves_uncertainty_and_omits_private_filename():
    facts = integrations.summary_facts(REPORT)
    assert "private.mov" not in str(facts)
    assert facts["sources"][0]["speedReliable"] is False
    assert facts["sources"][0]["timingAmbiguous"] is True


def test_gemini_request_is_grounded_and_key_is_a_header(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-unit-test-key")
    original = httpx.AsyncClient

    def handler(request):
        assert "fake-unit-test-key" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "fake-unit-test-key"
        assert b"timingAmbiguous" in request.content
        assert b"private.mov" not in request.content
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "Measured evidence only."}]}}
                ]
            },
        )

    monkeypatch.setattr(
        integrations.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert asyncio.run(integrations.explain(REPORT)) == "Measured evidence only."


def test_provider_timeout_is_recoverable_without_key_leak(monkeypatch):
    async def timeout(report):
        raise httpx.ReadTimeout("secret-in-provider-url")

    monkeypatch.setattr(integrations, "explain", timeout)
    response = TestClient(app).post("/api/explain", json={"report": REPORT})
    assert response.status_code == 503
    assert "could not be reached" in response.json()["detail"]
    assert "secret-in-provider-url" not in response.text


def test_twinly_checks_readiness_before_review(monkeypatch):
    monkeypatch.setenv("TWINLY_API_KEY", "fake-unit-test-key")
    original = httpx.AsyncClient
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/me"):
            return httpx.Response(200, json={"can": {"chat": True}, "private": "omit"})
        assert request.url.path.endswith("/chat/completions")
        assert b"twinly-core" in request.content
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Inspect the original source."}}]
            },
        )

    monkeypatch.setattr(
        integrations.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert (
        asyncio.run(integrations.twinly_review(REPORT))
        == "Inspect the original source."
    )
    assert len(paths) == 2
    assert paths[0].endswith("/me")


def test_provider_rejection_does_not_return_provider_body(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-unit-test-key")
    original = httpx.AsyncClient
    monkeypatch.setattr(
        integrations.httpx,
        "AsyncClient",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, text="secret upstream response")
            ),
            **kwargs,
        ),
    )
    with pytest.raises(ValueError, match="HTTP 429") as caught:
        asyncio.run(integrations.explain(REPORT))
    assert "secret upstream response" not in str(caught.value)
