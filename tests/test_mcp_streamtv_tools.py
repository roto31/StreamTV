"""Guided + detail tools hit the right /api/builder routes (§7.1–§7.2)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from mcp_streamtv import guided, tools


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((request.method, path))
        if path.endswith("/channels"):
            return httpx.Response(200, json=[{"number": "80", "name": "Demo"}])
        if path.endswith("/drafts") and request.method == "POST":
            return httpx.Response(
                200, json={"id": "d1", "channel": {"number": "", "name": ""}}
            )
        if "/drafts/d1" in path and request.method == "PATCH":
            body = json.loads(request.content.decode() or "{}")
            return httpx.Response(
                200,
                json={
                    "id": "d1",
                    "requirements": body.get("requirements")
                    or {"audience": "kids", "theme": "christmas"},
                    "plan_token": "tok-abc",
                    "candidates": [
                        {
                            "id": "c1",
                            "title": "Frosty",
                            "tier": 1,
                            "commercials": "yes",
                            "network": "CBS",
                            "air_date": "1989-12-01",
                            "role": "program",
                        }
                    ],
                    "explain_level": "beginner",
                },
            )
        if path.endswith("/drafts/d1") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "d1",
                    "plan_token": "tok-abc",
                    "requirements": {"audience": "kids", "theme": "christmas", "sources": ["archive"]},
                    "candidates": [
                        {
                            "id": "c1",
                            "title": "Frosty",
                            "tier": 1,
                            "commercials": "yes",
                            "network": "CBS",
                            "air_date": "1989-12-01",
                            "role": "program",
                        }
                    ],
                    "plan_questions": [],
                },
            )
        if path.endswith("/discover"):
            return httpx.Response(
                200, json={"draft_id": "d1", "candidate_count": 1, "candidates": [{"id": "c1"}]}
            )
        if path.endswith("/classify"):
            return httpx.Response(
                200,
                json={
                    "draft_id": "d1",
                    "candidates": [
                        {
                            "id": "c1",
                            "title": "Frosty",
                            "tier": 1,
                            "commercials": "yes",
                            "network": "CBS",
                            "air_date": "1989-12-01",
                        }
                    ],
                },
            )
        if path.endswith("/candidates/add"):
            return httpx.Response(200, json={"id": "d1"})
        if path.endswith("/plan"):
            return httpx.Response(
                200,
                json={
                    "draft_id": "d1",
                    "plan_token": "tok-abc",
                    "preview": {"program_count": 1, "canonical_titles": ["frosty"]},
                    "questions": [],
                },
            )
        if path.endswith("/validate"):
            return httpx.Response(
                200,
                json={
                    "overall": "PASS",
                    "ok": True,
                    "summary_table": "| Gate | Result |\n| G5 | PASS |",
                },
            )
        if path.endswith("/report"):
            return httpx.Response(200, json={"artifacts": {"dir": "/tmp/x"}})
        if path.endswith("/build"):
            return httpx.Response(200, json={"id": "job1", "status": "pending"})
        if path.endswith("/discover/youtube"):
            return httpx.Response(200, json={"results": []})
        if path.endswith("/discover/archive"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={})


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    rec = _Recorder()
    transport = httpx.MockTransport(rec.handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    class _Wrap:
        async def request(self, method: str, url: str, **kwargs: Any) -> Any:
            # tools.HTTPClient.request returns parsed JSON
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()

        async def close(self) -> None:
            await client.aclose()

    wrap = _Wrap()

    async def _get() -> Any:
        return wrap

    monkeypatch.setattr(tools, "get_client", _get)
    monkeypatch.setattr(tools.config, "base_url", "http://test")
    return rec


@pytest.mark.asyncio
async def test_channel_start_hits_drafts(mock_client: _Recorder) -> None:
    out = await guided.channel_start(template="kids_specials", name="Kids Xmas")
    assert out["draft_id"] == "d1"
    assert any(c[1].endswith("/drafts") for c in mock_client.calls)


@pytest.mark.asyncio
async def test_channel_find_hits_discover_and_classify(mock_client: _Recorder) -> None:
    out = await guided.channel_find("d1")
    assert out["status"] == "completed"
    paths = [c[1] for c in mock_client.calls]
    assert any(p.endswith("/discover") for p in paths)
    assert any(p.endswith("/classify") for p in paths)


@pytest.mark.asyncio
async def test_channel_build_needs_confirmation(mock_client: _Recorder) -> None:
    out = await guided.channel_build("d1", plan_token="tok-abc", confirm="no")
    assert out.get("needs_confirmation") is True


@pytest.mark.asyncio
async def test_channel_build_with_token(mock_client: _Recorder) -> None:
    out = await guided.channel_build("d1", plan_token="tok-abc", confirm="build")
    assert "summary_table" in out or out.get("needs_confirmation")
    paths = [c[1] for c in mock_client.calls]
    assert any(p.endswith("/validate") for p in paths)


@pytest.mark.asyncio
async def test_detail_discover_youtube(mock_client: _Recorder) -> None:
    out = await tools.discover_youtube("christmas", max_results=5)
    assert "results" in out
    assert any(c[1].endswith("/discover/youtube") for c in mock_client.calls)
