"""
Rate limiting middleware — Phase 5 hardening.

In-memory sliding-window limiter, keyed by (client IP, path). Tighter limits
apply to the auth endpoints most attractive to brute-forcing (login, OTP
verification); everything else falls back to a generous default so normal
API usage isn't affected.

Production note: this is a per-process in-memory store, same tradeoff as
_OTP_STORE in auth_service.py — correct for a single instance, but a
horizontally-scaled deployment needs a shared backend (Redis INCR+EXPIRE is
the standard pattern) so limits are enforced across instances rather than
reset per-pod. Flagged here as the production follow-up, not implemented for
this academic build.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

# path -> (max requests, window seconds). Matched by exact path, not prefix —
# deliberate, so a change to one auth route's limit can't accidentally loosen
# another's.
_SENSITIVE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (settings.RATE_LIMIT_LOGIN_MAX, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS),
    "/api/v1/auth/verify-otp": (settings.RATE_LIMIT_OTP_MAX, settings.RATE_LIMIT_OTP_WINDOW_SECONDS),
}
_SENSITIVE_PREFIXES: dict[str, tuple[int, int]] = {
    "/api/v1/emergency/access/": (
        settings.RATE_LIMIT_EMERGENCY_ACCESS_MAX,
        settings.RATE_LIMIT_EMERGENCY_ACCESS_WINDOW_SECONDS,
    ),
}
_DEFAULT_LIMIT: tuple[int, int] = (
    settings.RATE_LIMIT_DEFAULT_MAX,
    settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS,
)

# Module-level so it survives across requests within the process; exposed for
# tests to reset between cases (see tests/conftest.py's autouse fixture).
hit_log: dict[str, deque] = defaultdict(deque)


def reset() -> None:
    """Clear all rate-limit state. Used by tests for isolation between cases."""
    hit_log.clear()


def _client_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.url.path}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit, window = _DEFAULT_LIMIT
        for prefix, (p_limit, p_window) in _SENSITIVE_PREFIXES.items():
            if request.url.path.startswith(prefix):
                limit, window = p_limit, p_window
                break
        else:
            limit, window = _SENSITIVE_LIMITS.get(request.url.path, _DEFAULT_LIMIT)
        key = _client_key(request)
        now = time.monotonic()
        bucket = hit_log[key]

        # Evict timestamps that have aged out of the sliding window.
        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, int(window - (now - bucket[0])) + 1)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests — please slow down and try again shortly."},
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
