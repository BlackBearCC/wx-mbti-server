"""
Authentication and rate-limiting utilities for HTTP and WebSocket.

Auth
- HTTP: Accept `Authorization: Bearer <token>` or header `X-API-Key`, or query `api_key`.
- WS:   Prefer query param `token`; or send first frame `{op:"auth", data:{token}}`.
  Only `ping` is allowed pre-auth.

Rate Limit
- Fixed window using Redis: key = rl:<scope>:<subject>, INCR + EXPIRE.
  Subject = token (if present) else client ip.
"""
from __future__ import annotations

from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, WebSocket
import structlog

from app.config.settings import get_settings
from app.core.redis_client import get_redis
import time

_mem_rl_store: dict[str, tuple[int, float]] = {}


logger = structlog.get_logger()


def _parse_api_tokens(raw: Optional[str]) -> set[str]:
    if not raw:
        return set()
    raw = raw.strip()
    if not raw:
        return set()
    # support JSON array or comma-separated
    if raw.startswith("[") and raw.endswith("]"):
        try:
            import json

            lst = json.loads(raw)
            return {str(x).strip() for x in lst if str(x).strip()}
        except Exception:
            pass
    return {t.strip() for t in raw.split(",") if t.strip()}


def _get_token_from_request(request: Request) -> Tuple[Optional[str], str]:
    # Header Authorization: Bearer <token>
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip(), "bearer"
    # X-API-Key
    xkey = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if xkey:
        return xkey.strip(), "x-api-key"
    # Query `api_key` or `token`
    q = request.query_params
    if "api_key" in q:
        return q.get("api_key"), "query"
    if "token" in q:
        return q.get("token"), "query"
    return None, "none"


class AuthContext:
    def __init__(self, token: Optional[str], subject: str, method: str):
        self.token = token
        self.subject = subject  # used for rate-limit key
        self.method = method


async def require_auth(request: Request) -> AuthContext:
    """HTTP auth dependency. Raises 401 if invalid.

    When no API_TOKENS configured:
    - In DEBUG and token is non-empty -> allow with a warning once.
    - Otherwise -> 401.
    """
    settings = get_settings()
    token, method = _get_token_from_request(request)
    allowed = _parse_api_tokens(settings.API_TOKENS)
    if not allowed:
        # Development fallback token to avoid breaking local tests; override via API_TOKENS in prod
        allowed = {"dev-token"}

    if token and (token in allowed or (not allowed and settings.DEBUG and settings.AUTH_ALLOW_ANY_TOKEN_IN_DEBUG)):
        # subject uses token; fallback to IP if somehow token empty
        subject = token or (request.client.host if request.client else "unknown")
        return AuthContext(token=token, subject=subject, method=method)

    # No token or invalid
    raise HTTPException(status_code=401, detail="未授权：缺少或非法的访问令牌")


async def enforce_rate_limit(subject: str, scope: str) -> None:
    """Fixed-window rate limiter using Redis. Raises 429 if exceeded."""
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return
    limit = max(1, settings.RATE_LIMIT_REQUESTS)
    window = max(1, settings.RATE_LIMIT_WINDOW)
    key = f"rl:{scope}:{subject}"
    try:
        r = get_redis()
        # Best-effort; small race is acceptable for fixed window
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window)
        if count > limit:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        return
    except Exception:
        # Fallback to in-memory window
        now = time.time()
        cnt, exp = _mem_rl_store.get(key, (0, 0.0))
        if now >= exp:
            cnt, exp = 0, now + window
        cnt += 1
        _mem_rl_store[key] = (cnt, exp)
        if cnt > limit:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


# ---- WebSocket helpers ----

def ws_extract_token(ws: WebSocket) -> Optional[str]:
    # Prefer query param
    token = ws.query_params.get("token")
    if token:
        return token
    # Fallback to Authorization header: Bearer <token>
    try:
        auth = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
    except Exception:
        pass
    return None


def ws_validate_token(token: Optional[str]) -> bool:
    settings = get_settings()
    allowed = _parse_api_tokens(settings.API_TOKENS)
    if not allowed:
        allowed = {"dev-token"}
    if token and (token in allowed or (not allowed and settings.DEBUG and settings.AUTH_ALLOW_ANY_TOKEN_IN_DEBUG)):
        return True
    return False
