"""HTTP transport + auth (§7A) — none|bearer|oauth|dual."""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from jose import jwt
from starlette.testclient import TestClient

from mcp_streamtv.auth_http import (
    auth0_issuer,
    auth0_jwks_url,
    cloudflare_access_issuer,
    cloudflare_access_jwks_url,
    is_loopback_host,
    profile_from_oauth_claims,
    resolve_oauth_endpoints,
    validate_bind_auth,
    validate_bearer_header,
    validate_oauth_token,
)
from mcp_streamtv.main import _active_specs, build_http_app


def test_loopback_only_none_auth() -> None:
    validate_bind_auth("127.0.0.1", "none")
    validate_bind_auth("localhost", "none")
    with pytest.raises(SystemExit):
        validate_bind_auth("0.0.0.0", "none")
    with pytest.raises(SystemExit):
        validate_bind_auth("192.0.2.1", "none")
    validate_bind_auth("0.0.0.0", "bearer")
    validate_bind_auth("0.0.0.0", "oauth")
    validate_bind_auth("0.0.0.0", "dual")


def test_is_loopback() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("::1")
    assert not is_loopback_host("0.0.0.0")


def test_bearer_header_constant_time() -> None:
    tok = "a" * 32
    assert validate_bearer_header(f"Bearer {tok}", tok)
    assert not validate_bearer_header("Bearer wrong", tok)
    assert not validate_bearer_header(None, tok)


def test_resolve_oauth_endpoints_providers() -> None:
    iss, jwks = resolve_oauth_endpoints(
        provider="auth0", team_or_domain="dev-xyz.us.auth0.com"
    )
    assert iss == auth0_issuer("dev-xyz.us.auth0.com")
    assert jwks == auth0_jwks_url("dev-xyz.us.auth0.com")
    cf_iss, cf_jwks = resolve_oauth_endpoints(
        provider="cloudflare_access", team_or_domain="myteam"
    )
    assert cf_iss == cloudflare_access_issuer("myteam")
    assert cf_jwks == cloudflare_access_jwks_url("myteam")
    assert cf_jwks.endswith("/cdn-cgi/access/certs")


def test_tools_list_equal_across_profiles_registry() -> None:
    """R12 registry identity: same profile → same tool names for both transports."""
    for profile in ("guided", "planner", "builder"):
        a = [n for n, _ in _active_specs(profile)]
        b = [n for n, _ in _active_specs(profile)]
        assert a == b
    guided = [n for n, _ in _active_specs("guided")]
    assert len(guided) == 11
    assert "channel_build" in guided
    planner = [n for n, _ in _active_specs("planner")]
    assert "channel_build" not in planner


def _hs256_jwks(secret: str) -> dict[str, Any]:
    # python-jose accepts raw secret for HS256; expose as oct key
    import base64

    k = base64.urlsafe_b64encode(secret.encode()).rstrip(b"=").decode()
    return {"keys": [{"kty": "oct", "kid": "test", "k": k, "alg": "HS256"}]}


def test_oauth_accepts_valid_rejects_wrong_aud() -> None:
    secret = "test-secret-key-for-hs256-oauth!!"
    jwks = _hs256_jwks(secret)
    good = jwt.encode(
        {"sub": "u1", "iss": "https://issuer.test", "aud": "streamtv-mcp", "scope": "streamtv.read"},
        secret,
        algorithm="HS256",
    )
    claims = validate_oauth_token(
        good, issuer="https://issuer.test", audience="streamtv-mcp", jwks=jwks
    )
    assert claims["sub"] == "u1"
    assert profile_from_oauth_claims(claims) == "planner"

    bad = jwt.encode(
        {"sub": "u1", "iss": "https://issuer.test", "aud": "wrong", "scope": "streamtv.write"},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(ValueError):
        validate_oauth_token(
            bad, issuer="https://issuer.test", audience="streamtv-mcp", jwks=jwks
        )


@pytest.fixture
def bearer_token() -> str:
    return secrets.token_urlsafe(32)


@pytest.fixture
def http_app_none():
    return build_http_app(
        profile="guided",
        host="127.0.0.1",
        path="/mcp",
        auth="none",
        allowed_hosts=["127.0.0.1:8411", "localhost:8411", "testserver", "testserver:80"],
        allowed_origins=[
            "http://127.0.0.1:8411",
            "http://localhost:8411",
            "http://testserver",
        ],
    )


@pytest.fixture
def http_app_bearer(bearer_token: str):
    return build_http_app(
        profile="guided",
        host="127.0.0.1",
        path="/mcp",
        auth="bearer",
        bearer_token=bearer_token,
        allowed_hosts=["127.0.0.1:8411", "testserver", "testserver:80"],
        allowed_origins=["http://127.0.0.1:8411", "http://testserver"],
    )


def test_http_none_reaches_mcp_path(http_app_none) -> None:
    with TestClient(http_app_none) as client:
        # Without MCP session headers the transport may return 400/406 — but not 401
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp.status_code != 401


def test_bearer_401_without_token(http_app_bearer) -> None:
    with TestClient(http_app_bearer) as client:
        resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers


def test_bearer_allows_with_token(http_app_bearer, bearer_token: str) -> None:
    with TestClient(http_app_bearer) as client:
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        assert resp.status_code != 401


def test_bad_origin_rejected(http_app_none) -> None:
    with TestClient(http_app_none) as client:
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Origin": "http://evil.example"},
        )
        # DNS-rebinding protection should reject (400/403) — not succeed as 2xx MCP
        assert resp.status_code >= 400


def test_oauth_http_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "oauth-http-middleware-secret-key!!"
    jwks = _hs256_jwks(secret)
    monkeypatch.setattr(
        "mcp_streamtv.main._load_oauth_jwks",
        lambda: ("https://issuer.test", jwks),
    )
    monkeypatch.setattr(
        "mcp_streamtv.config.config.mcp_oauth_audience", "streamtv-mcp"
    )
    app = build_http_app(
        profile="planner",
        host="127.0.0.1",
        path="/mcp",
        auth="oauth",
        allowed_hosts=["testserver", "127.0.0.1:8411"],
        allowed_origins=["http://testserver", "http://127.0.0.1:8411"],
    )
    with TestClient(app) as client:
        assert client.post("/mcp", json={}).status_code == 401
        tok = jwt.encode(
            {
                "sub": "u",
                "iss": "https://issuer.test",
                "aud": "streamtv-mcp",
                "scope": "streamtv.write",
            },
            secret,
            algorithm="HS256",
        )
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code != 401


def test_dual_requires_access_jwt_and_mcp_token(
    monkeypatch: pytest.MonkeyPatch, bearer_token: str
) -> None:
    secret = "dual-access-jwt-hs256-secret-key!!"
    jwks = _hs256_jwks(secret)
    issuer = "https://myteam.cloudflareaccess.com"
    audience = "access-aud-tag-test"
    monkeypatch.setattr(
        "mcp_streamtv.main._load_access_jwks",
        lambda: (issuer, audience, jwks),
    )
    app = build_http_app(
        profile="guided",
        host="127.0.0.1",
        path="/mcp",
        auth="dual",
        bearer_token=bearer_token,
        allowed_hosts=["testserver", "127.0.0.1:8411"],
        allowed_origins=["http://testserver", "http://127.0.0.1:8411"],
    )
    access_jwt = jwt.encode(
        {"sub": "u", "iss": issuer, "aud": audience},
        secret,
        algorithm="HS256",
    )
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    with TestClient(app) as client:
        assert client.post("/mcp", json=body).status_code == 401
        assert (
            client.post(
                "/mcp",
                json=body,
                headers={"Authorization": f"Bearer {bearer_token}"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp",
                json=body,
                headers={"Cf-Access-Jwt-Assertion": access_jwt},
            ).status_code
            == 401
        )
        ok = client.post(
            "/mcp",
            json=body,
            headers={
                "Cf-Access-Jwt-Assertion": access_jwt,
                "Authorization": f"Bearer {bearer_token}",
            },
        )
        assert ok.status_code != 401
        bad_access = client.post(
            "/mcp",
            json=body,
            headers={
                "Cf-Access-Jwt-Assertion": jwt.encode(
                    {"sub": "u", "iss": issuer, "aud": "wrong"},
                    secret,
                    algorithm="HS256",
                ),
                "Authorization": f"Bearer {bearer_token}",
            },
        )
        assert bad_access.status_code == 401
        assert bad_access.json().get("error") == "access_jwt_invalid"
