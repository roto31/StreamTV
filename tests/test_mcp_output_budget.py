"""Guided tool output size budget (§7.5)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from mcp_streamtv import guided, tools


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    big = {
        "id": "d1",
        "plan_token": "tok",
        "requirements": {"audience": "kids", "theme": "christmas", "sources": ["archive"]},
        "candidates": [
            {
                "id": f"c{i}",
                "title": f"Special {i} " + ("x" * 200),
                "tier": 1 if i % 2 == 0 else 2,
                "commercials": "yes",
                "network": "CBS",
                "air_date": "1989-12-01",
                "role": "program",
                "description": "y" * 2000,
            }
            for i in range(80)
        ],
        "plan_questions": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/drafts") and request.method == "POST":
            return httpx.Response(200, json={"id": "d1", "channel": {}})
        if "/drafts/d1" in path:
            if request.method == "PATCH":
                return httpx.Response(200, json=big)
            return httpx.Response(200, json=big)
        if path.endswith("/discover"):
            return httpx.Response(
                200, json={"candidate_count": 80, "candidates": big["candidates"]}
            )
        if path.endswith("/classify"):
            return httpx.Response(200, json={"candidates": big["candidates"]})
        if path.endswith("/plan"):
            return httpx.Response(
                200,
                json={
                    "plan_token": "tok",
                    "preview": {
                        "program_count": 80,
                        "channel": {"channels": [{"streams": big["candidates"]}]},
                        "schedule": {"sequence": []},
                        "canonical_titles": [f"t{i}" for i in range(80)],
                    },
                    "questions": [],
                },
            )
        if path.endswith("/channels"):
            return httpx.Response(200, json=[{"number": str(i), "name": f"C{i}"} for i in range(200)])
        if path.endswith("/drafts") and request.method == "GET":
            return httpx.Response(200, json=[{"id": f"d{i}"} for i in range(5)])
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    class _Wrap:
        async def request(self, method: str, url: str, **kwargs: Any) -> Any:
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()

    async def _get() -> Any:
        return _Wrap()

    monkeypatch.setattr(tools, "get_client", _get)
    monkeypatch.setattr(tools.config, "base_url", "http://test")


@pytest.mark.asyncio
async def test_guided_results_under_16k(mock_client: None) -> None:
    results = [
        await guided.channel_guide(),
        await guided.channel_list(),
        await guided.channel_start(name="Huge"),
        await guided.channel_set_requirements("d1", audience="kids", theme="christmas"),
        await guided.channel_find("d1"),
        await guided.channel_shortlist("d1", page=1),
        await guided.channel_plan("d1"),
    ]
    for out in results:
        raw = json.dumps(out, default=str)
        assert len(raw) <= 16000, f"over budget: {len(raw)}"


def test_intake_hard_rules_in_all_variants() -> None:
    from mcp_streamtv import resources

    for text in (
        resources.CHANNEL_INTAKE_PROMPT,
        resources.CHANNEL_INTAKE_EXPERT,
        resources.CHANNEL_INTAKE_COMPACT,
    ):
        assert ".ia.mp4" in text or "ia.mp4" in text
        assert "runtime" in text.lower() or "Runtime" in text
        assert "build" in text.lower()
        assert "NEW" in text or "new channel" in text.lower()
