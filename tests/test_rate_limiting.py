"""
Phase 5 hardening — rate limiting middleware.

Uses the general/default limit rather than the tighter login-specific one so
this test doesn't have to also stand up a full registration flow — the
middleware applies the same sliding-window logic regardless of which bucket
it's enforcing, so exercising it against /health is representative.
"""

from app.core.config import settings
from app.middleware import rate_limit
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_client_key(request):
    """
    Simulate a unique client IP per test to prevent rate limit state from 
    leaking across tests without needing a global reset.
    """
    def fake_key(req):
        return f"{request.node.name}:{req.url.path}"
    with patch("app.middleware.rate_limit._client_key", side_effect=fake_key):
        yield


def test_requests_within_limit_all_succeed(client):
    for _ in range(settings.RATE_LIMIT_DEFAULT_MAX):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_requests_beyond_limit_are_throttled(client):
    for _ in range(settings.RATE_LIMIT_DEFAULT_MAX):
        client.get("/health")

    throttled = client.get("/health")
    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers


def test_login_endpoint_has_its_own_tighter_limit(client):
    assert settings.RATE_LIMIT_LOGIN_MAX <= settings.RATE_LIMIT_DEFAULT_MAX

    bad_login = {"email": "nobody@medivault.ai", "password": "wrong"}
    for _ in range(settings.RATE_LIMIT_LOGIN_MAX):
        resp = client.post("/api/v1/auth/login", json=bad_login)
        assert resp.status_code == 401  # wrong credentials, but not yet throttled

    throttled = client.post("/api/v1/auth/login", json=bad_login)
    assert throttled.status_code == 429


def test_rate_limit_state_is_isolated_per_path(client):
    for _ in range(settings.RATE_LIMIT_LOGIN_MAX):
        client.post("/api/v1/auth/login", json={"email": "nobody@medivault.ai", "password": "wrong"})

    # /health uses the separate default bucket, so it should be unaffected
    # by /auth/login having just been exhausted.
    resp = client.get("/health")
    assert resp.status_code == 200
