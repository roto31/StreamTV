"""Phase 1 red regressions for mcp_archive_org URL safety (D6)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

import pytest

from mcp_archive_org import tools as archive_tools


@pytest.fixture
def fake_archive_item(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Item with an original .mp4, a derivative .ia.mp4, and a spaced filename."""
    payload = {
        "metadata": {"title": "D6 Probe", "date": "1989-12-01"},
        "files": [
            {
                "name": "Show With Spaces.mp4",
                "format": "MPEG4",
                "source": "original",
                "length": "1810.4",
                "size": "100",
            },
            {
                "name": "Show With Spaces.ia.mp4",
                "format": "h.264",
                "source": "derivative",
                "length": "1810.4",
                "size": "50",
            },
        ],
        "server": "ia800000.us.archive.org",
        "dir": "/7/items/d6_probe_item",
    }

    async def fake_meta(identifier: str) -> dict[str, Any]:
        return dict(payload, identifier=identifier)

    monkeypatch.setattr(archive_tools, "archive_org_get_item_metadata", fake_meta)
    return payload


@pytest.mark.asyncio
async def test_d6_stream_url_is_canonical_download_never_ia_mp4_or_pinned(
    fake_archive_item: dict[str, Any],
) -> None:
    """D6: return archive.org/download/<id>/<urlencoded>; never .ia.mp4 or storage node."""
    result = await archive_tools.archive_org_get_stream_url("d6_probe_item")
    assert "error" not in result, result

    stream_url = result["stream_url"]
    parsed = urlparse(stream_url)

    assert parsed.netloc == "archive.org", (
        "D6: must not return storage-server-pinned URL "
        f"(got host {parsed.netloc!r}, url {stream_url!r})"
    )
    assert stream_url.startswith(
        "https://archive.org/download/d6_probe_item/"
    ), f"D6: expected canonical download URL, got {stream_url!r}"
    assert ".ia.mp4" not in stream_url.lower(), (
        f"D6: must never return *.ia.mp4 derivative (got {stream_url!r})"
    )
    assert "Show%20With%20Spaces.mp4" in stream_url or quote(
        "Show With Spaces.mp4", safe="/"
    ) in stream_url, (
        "D6: filename must be URL-encoded "
        f"(got {stream_url!r})"
    )
    # Exact runtime as integer seconds (source length 1810.4).
    length = result.get("duration")
    assert length == 1810 or length == 1810.4 or int(float(length)) == 1810, (
        f"D6: duration should expose file length (got {length!r})"
    )


@pytest.mark.asyncio
async def test_d6_get_item_files_excludes_ia_mp4_by_default(
    fake_archive_item: dict[str, Any],
) -> None:
    """D6: format_filter=mp4 must not match *.ia.mp4; originals_only / exclude_derivatives."""
    result = await archive_tools.archive_org_get_item_files(
        "d6_probe_item", format_filter="mp4"
    )
    names = [f.get("name") for f in result["files"]]
    assert not any(str(n).lower().endswith(".ia.mp4") for n in names), (
        "D6: format_filter substring match includes .ia.mp4 "
        f"(got {names!r})"
    )
