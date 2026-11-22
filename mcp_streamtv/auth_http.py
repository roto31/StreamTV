"""HTTP auth for Streamable MCP transport (§7A.2).

Modes:
  none   — loopback only
  bearer — STREAMTV_MCP_TOKEN in Authorization: Bearer
  oauth  — JWT from Auth0 / Cloudflare Access / custom OIDC (resource server)
  dual   — Cloudflare Access JWT (Cf-Access-Jwt-Assertion) AND MCP bearer token
"""

from __future__ import annotations

import hmac
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"})
_AUTH_MODES = frozenset({"none", "bearer", "oauth", "dual"})


def is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower()
    if h in _LOOPBACK:
        return True
    if h.startswith("[") and h.endswith("]"):
        return h[1:-1] in _LOOPBACK
    return False


def validate_bind_auth(host: str, auth: str) -> None:
    """Exit-condition helper: non-loopback + auth=none is forbidden."""
    auth = (auth or "none").strip().lower()
    if auth not in _AUTH_MODES:
        raise SystemExit(
            f"ERROR: unknown auth mode {auth!r} "
            f"(want none|bearer|oauth|dual)"
        )
    if auth == "none" and not is_loopback_host(host):
        raise SystemExit(
            "ERROR: STREAMTV_MCP_AUTH=none is only allowed on loopback "
            f"(got host={host!r}). Use --auth bearer, oauth, or dual."
        )


def require_bearer_token(token: str) -> str:
    t = (token or "").strip()
    if len(t) < 32:
        raise SystemExit(
            "ERROR: STREAMTV_MCP_TOKEN must be at least 32 characters for bearer/dual auth"
        )
    return t


def cloudflare_access_issuer(team_domain: str) -> str:
    """team_domain: 'myteam' or 'myteam.cloudflareaccess.com'."""
    d = (team_domain or "").strip().rstrip("/")
    if not d:
        return ""
    if d.startswith("https://"):
        return d
    if ".cloudflareaccess.com" in d:
        return f"https://{d}"
    return f"https://{d}.cloudflareaccess.com"


def cloudflare_access_jwks_url(team_domain: str) -> str:
    issuer = cloudflare_access_issuer(team_domain)
    return f"{issuer}/cdn-cgi/access/certs" if issuer else ""


def auth0_issuer(domain: str) -> str:
    """domain: 'dev-xxx.us.auth0.com' or full https issuer."""
    d = (domain or "").strip().rstrip("/")
    if not d:
        return ""
    if d.startswith("https://"):
        return d
    return f"https://{d}/"


def auth0_jwks_url(domain: str) -> str:
    issuer = auth0_issuer(domain).rstrip("/")
    return f"{issuer}/.well-known/jwks.json" if issuer else ""


def resolve_oauth_endpoints(
    *,
    provider: str,
    team_or_domain: str = "",
    issuer: str = "",
    jwks_url: str = "",
) -> tuple[str, str]:
    """Return (issuer, jwks_url) for known providers."""
    provider = (provider or "custom").strip().lower()
    if provider in ("cloudflare_access", "cloudflare", "cf_access", "access"):
        iss = issuer or cloudflare_access_issuer(team_or_domain)
        jwks = jwks_url or cloudflare_access_jwks_url(team_or_domain)
        return iss, jwks
    if provider in ("auth0",):
        iss = issuer or auth0_issuer(team_or_domain)
        jwks = jwks_url or auth0_jwks_url(team_or_domain)
        return iss, jwks
    return (issuer or "").rstrip("/"), jwks_url or ""


class AuthRateLimiter:
    """Simple per-IP failed-auth rate limit (never logs tokens)."""

    def __init__(self, max_fails: int = 20, window_sec: float = 60.0) -> None:
        self.max_fails = max_fails
        self.window_sec = window_sec
        self._fails: dict[str, list[float]] = defaultdict(list)

    def blocked(self, ip: str) -> bool:
        now = time.time()
        bucket = [t for t in self._fails[ip] if now - t < self.window_sec]
        self._fails[ip] = bucket
        return len(bucket) >= self.max_fails

    def record_fail(self, ip: str) -> None:
        self._fails[ip].append(time.time())


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def validate_bearer_header(authorization: str | None, expected: str) -> bool:
    if not authorization:
        return False
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return constant_time_equals(parts[1].strip(), expected)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def validate_oauth_token(
    token: str,
    *,
    issuer: str,
    audience: str,
    jwks: dict[str, Any],
) -> dict[str, Any]:
    """Validate a JWT against a JWKS (resource-server mode). Raises ValueError."""
    from jose import jwt
    from jose.exceptions import JOSEError

    if not token:
        raise ValueError("missing token")
    keys = jwks.get("keys") or []
    if not keys:
        raise ValueError("empty JWKS")
    audiences: list[str] | str = audience
    if "," in (audience or ""):
        audiences = [a.strip() for a in audience.split(",") if a.strip()]
    last_err: Exception | None = None
    for key in keys:
        algs = [key.get("alg") or "RS256", "RS256", "ES256", "HS256"]
        try:
            return jwt.decode(
                token,
                key,
                algorithms=list(dict.fromkeys(algs)),
                audience=audiences,
                issuer=issuer,
                options={"verify_at_hash": False},
            )
        except JOSEError as exc:
            last_err = exc
            continue
    raise ValueError(str(last_err or "token invalid"))


def profile_from_oauth_claims(claims: dict[str, Any]) -> str:
    """Map token scopes → planner (read) or guided (write)."""
    scope = claims.get("scope") or claims.get("scp") or ""
    if isinstance(scope, list):
        scopes = {str(s).lower() for s in scope}
    else:
        scopes = {s.lower() for s in str(scope).split() if s}
    if "streamtv.write" in scopes or "write" in scopes:
        return "guided"
    if "streamtv.read" in scopes or "read" in scopes:
        return "planner"
    return "planner"


def make_auth_middleware(
    *,
    auth: str,
    bearer_token: str = "",
    oauth_issuer: str = "",
    oauth_audience: str = "",
    oauth_jwks: Optional[dict[str, Any]] = None,
    access_issuer: str = "",
    access_audience: str = "",
    access_jwks: Optional[dict[str, Any]] = None,
    on_oauth_profile: Optional[Callable[[str], None]] = None,
) -> Any:
    """Starlette middleware factory for none|bearer|oauth|dual."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response

    limiter = AuthRateLimiter()
    mode = (auth or "none").lower()

    def _unauthorized(detail: str = "unauthorized") -> JSONResponse:
        return JSONResponse(
            {"error": detail},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="streamtv-mcp"'},
        )

    class MCPAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            path = request.url.path
            if path.endswith(
                "/.well-known/oauth-protected-resource"
            ) or path.endswith("/.well-known/oauth-authorization-server"):
                return await call_next(request)

            if mode == "none":
                return await call_next(request)

            client = request.client.host if request.client else "unknown"
            if limiter.blocked(client):
                return JSONResponse({"error": "rate_limited"}, status_code=429)

            authz = request.headers.get("authorization")

            if mode == "bearer":
                if not validate_bearer_header(authz, bearer_token):
                    limiter.record_fail(client)
                    return _unauthorized("bearer_required")
                return await call_next(request)

            if mode == "oauth":
                token = extract_bearer_token(authz)
                try:
                    claims = validate_oauth_token(
                        token,
                        issuer=oauth_issuer,
                        audience=oauth_audience,
                        jwks=oauth_jwks or {"keys": []},
                    )
                except ValueError:
                    limiter.record_fail(client)
                    return _unauthorized("oauth_token_invalid")
                if on_oauth_profile is not None:
                    on_oauth_profile(profile_from_oauth_claims(claims))
                return await call_next(request)

            if mode == "dual":
                # Lock 1 = Cloudflare Access JWT on Cf-Access-Jwt-Assertion
                # Lock 2 = STREAMTV_MCP_TOKEN on Authorization: Bearer
                # (ChatGPT/Claude send the MCP secret; Cloudflare edge injects the Access JWT.)
                access_jwt = (
                    request.headers.get("cf-access-jwt-assertion")
                    or request.headers.get("Cf-Access-Jwt-Assertion")
                    or ""
                ).strip()
                if not access_jwt:
                    limiter.record_fail(client)
                    return _unauthorized("access_jwt_required")
                try:
                    validate_oauth_token(
                        access_jwt,
                        issuer=access_issuer or oauth_issuer,
                        audience=access_audience or oauth_audience,
                        jwks=access_jwks or oauth_jwks or {"keys": []},
                    )
                except ValueError:
                    limiter.record_fail(client)
                    return _unauthorized("access_jwt_invalid")

                if not validate_bearer_header(authz, bearer_token):
                    limiter.record_fail(client)
                    return _unauthorized("mcp_token_required")
                return await call_next(request)

            return _unauthorized("auth_misconfigured")

    return MCPAuthMiddleware
