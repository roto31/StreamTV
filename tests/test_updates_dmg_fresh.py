"""The DMG endpoint must bypass the release cache."""

from __future__ import annotations

from typing import Any

from streamtv.api import updates


def _release(tag: str) -> dict[str, Any]:
    return {
        "tag_name": tag,
        "name": tag,
        "body": "",
        "html_url": "",
        "published_at": "",
        "error": None,
        "assets": [
            {"name": f"StreamTV.{tag[1:]}-macos.dmg", "browser_download_url": f"https://x/{tag}.dmg"}
        ],
    }


def test_force_refresh_ignores_cache(monkeypatch: Any) -> None:
    import io
    import json
    import time

    updates._CACHE["payload"] = _release("v1.0.0")
    updates._CACHE["fetched_at"] = time.time()

    class _Resp(io.BytesIO):
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

    body = json.dumps({"tag_name": "v2.0.0", "assets": []}).encode()
    monkeypatch.setattr(updates, "urlopen", lambda *a, **k: _Resp(body))

    assert updates._fetch_latest_release()["tag_name"] == "v1.0.0"
    assert updates._fetch_latest_release(force=True)["tag_name"] == "v2.0.0"
