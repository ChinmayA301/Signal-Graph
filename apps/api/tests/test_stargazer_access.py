"""Live mode must say so when GitHub withholds a repo's stargazer list (no network)."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile

import httpx
import pytest

if "DATABASE_URL" not in os.environ:   # same throwaway-SQLite setup as test_api_smoke
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import analysis_pipeline, github_ingest  # noqa: E402
from app.services.github_ingest import StargazersUnavailable, fetch_live_dataset  # noqa: E402


def _repo_payload(stargazer_count: int, edges: list) -> dict:
    return {"data": {"repository": {
        "databaseId": 1, "stargazerCount": stargazer_count, "forkCount": 3,
        "createdAt": "2024-01-01T00:00:00Z", "pushedAt": "2026-11-01T00:00:00Z",
        "openIssues": {"totalCount": 0}, "openPullRequests": {"totalCount": 0},
        "stargazers": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "edges": edges},
    }}}


def _patch_client(monkeypatch, payload: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/graphql":
            query = json.loads(request.content)["query"]
            return httpx.Response(200, json=payload if "stargazers(" in query else {"data": {"repository": None}})
        return httpx.Response(200, json=[])   # REST /contributors
    real = httpx.AsyncClient
    monkeypatch.setattr(github_ingest.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_restricted_stargazer_list_raises_specific_error(monkeypatch) -> None:
    _patch_client(monkeypatch, _repo_payload(52_000, []))
    with pytest.raises(StargazersUnavailable) as err:
        asyncio.run(fetch_live_dataset("someone", "popular", "tok", coadoption_enabled=False))
    assert err.value.stargazer_count == 52_000
    assert "admins and collaborators" in str(err.value)


def test_repo_with_no_stars_is_not_reported_as_restricted(monkeypatch) -> None:
    _patch_client(monkeypatch, _repo_payload(0, []))
    with pytest.raises(RuntimeError) as err:
        asyncio.run(fetch_live_dataset("someone", "empty", "tok", coadoption_enabled=False))
    assert not isinstance(err.value, StargazersUnavailable)


def test_api_carries_notice_when_stargazers_restricted(monkeypatch) -> None:
    async def restricted(owner, name, token, **kw):
        raise StargazersUnavailable(owner, name, 1234)
    monkeypatch.setattr(analysis_pipeline, "fetch_live_dataset", restricted)
    app.dependency_overrides[get_settings] = lambda: Settings(mock_mode=False, github_token="tok")
    try:
        with TestClient(app) as client:
            r = client.post("/analyze", json={"repo_url": "https://github.com/someone/restricted"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["repository"]["ingestion_source"] == "mock_no_stargazer_access"
            assert "admins and collaborators" in body["data_notice"]
            # The persisted read path reports the same thing.
            again = client.get("/repo/someone/restricted").json()
            assert again["data_notice"] == body["data_notice"]
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_mock_mode_is_labelled_demo_data() -> None:
    with TestClient(app) as client:
        body = client.post("/analyze", json={"repo_url": "https://github.com/a/b", "force_mock": True}).json()
        assert body["repository"]["ingestion_source"] == "mock"
        assert body["data_notice"].startswith("Demo data")
