"""WebUI /documentation markdown link rewrite and auth template path."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_documentation_index_rewrites_beginner_guide_href() -> None:
    from streamtv.main import app

    client = TestClient(app)
    resp = client.get("/documentation")
    assert resp.status_code == 200
    body = resp.text
    assert "BEGINNER_GUIDE.md" not in body
    assert 'href="/docs/beginner"' in body or "/docs/beginner" in body


def test_docs_beginner_ok() -> None:
    from streamtv.main import app

    client = TestClient(app)
    resp = client.get("/docs/beginner")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_rewrite_doc_markdown_links_unit() -> None:
    from streamtv.api.docs import rewrite_doc_markdown_links

    html = (
        '<a href="./BEGINNER_GUIDE.md">Beginner</a>'
        '<a href="guides/SOFT_DEPLOY.md">Soft</a>'
        '<a href="https://example.com/x.md">Ext</a>'
        '<a href="/docs/already">Keep</a>'
    )
    out = rewrite_doc_markdown_links(html)
    assert 'href="/docs/beginner"' in out
    assert 'href="/docs/soft_deploy"' in out
    assert 'href="https://example.com/x.md"' in out
    assert 'href="/docs/already"' in out


def test_auth_pages_ok_with_foreign_cwd(tmp_path: Path, monkeypatch) -> None:
    """Application Support cwd must not 500 auth HTML (Issue: relative Jinja path)."""
    monkeypatch.chdir(tmp_path)
    from streamtv.main import app

    client = TestClient(app)
    for path in ("/api/auth/youtube", "/api/auth/archive-org", "/api/auth/archive"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text[:200]}"
        assert "Internal Server Error" not in resp.text
        assert "text/html" in resp.headers.get("content-type", "")


def test_auth_templates_dir_is_absolute() -> None:
    from streamtv.api import auth as auth_mod

    assert Path(auth_mod.TEMPLATES_DIR).is_absolute()
    assert (auth_mod.TEMPLATES_DIR / "auth_youtube.html").is_file()
    assert (auth_mod.TEMPLATES_DIR / "auth_archive_org.html").is_file()
