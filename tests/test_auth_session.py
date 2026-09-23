
import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User, RoleEnum, UserStatusEnum
from app.models.auth import RefreshToken
from app.core.security import create_refresh_token, hash_password
from app.services.auth_service import login, _OTP_STORE

def test_refresh_reuse_revokes_family(client, db):
    # Setup test user
    user = User(
        email="reuse@test.com", phone="1234567890", password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT, full_name="Test User", status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()

    # Login to get first refresh token
    resp = client.post("/api/v1/auth/login", json={"email": "reuse@test.com", "password": "Password123!"})
    rt1 = resp.cookies.get("refresh_token")
    assert rt1 is not None

    # Normal refresh (rt1 -> rt2)
    resp2 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": rt1}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp2.status_code == 200
    rt2 = resp2.cookies.get("refresh_token")

    # Reuse rt1 (should trigger revocation of all tokens)
    resp3 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": rt1}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp3.status_code == 401

    # Try to use rt2 (should fail because family is revoked)
    resp4 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": rt2}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp4.status_code == 401

def test_concurrent_refresh_race(client, db):
    # This test previously used threading.Thread with a shared SQLAlchemy session,
    # which is fundamentally not thread-safe and crashes SQLite in-memory databases.
    # The goal of this test is to verify the compare-and-set logic. We can test this
    # deterministically by mocking the exact concurrency failure mode: update() returning 0.
    
    # Setup test user
    user = User(
        email="race2@test.com", phone="5555555556", password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT, full_name="Race User", status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()

    # Login to get first refresh token
    resp = client.post("/api/v1/auth/login", json={"email": "race2@test.com", "password": "Password123!"})
    rt1 = resp.cookies.get("refresh_token")

    # We mock the SQLAlchemy Query.update method to return 0, simulating what happens
    # when another thread has already updated the token.
    from unittest.mock import patch
    
    with patch("sqlalchemy.orm.Query.update", return_value=0):
        res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": rt1}, headers={"X-Requested-With": "XMLHttpRequest"})
        
    assert res.status_code == 401
    assert "Token reuse detected" in res.json()["detail"]

def test_cookie_flags_per_environment(client, db, monkeypatch):
    user = User(
        email="cookie@test.com", phone="9876543210", password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT, full_name="Test User", status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()

    # Test DEV environment
    monkeypatch.setattr("app.api.v1.endpoints.auth.settings.ENV", "dev")
    resp_dev = client.post("/api/v1/auth/login", json={"email": "cookie@test.com", "password": "Password123!"})
    cookie_dev = resp_dev.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_dev
    assert "SameSite=lax" in cookie_dev
    assert "Secure" not in cookie_dev

    # Test PRODUCTION environment
    monkeypatch.setattr("app.api.v1.endpoints.auth.settings.ENV", "production")
    resp_prod = client.post("/api/v1/auth/login", json={"email": "cookie@test.com", "password": "Password123!"})
    cookie_prod = resp_prod.headers.get("set-cookie", "")
    assert "Secure" in cookie_prod

def test_csrf_header_enforcement(client, db):
    resp = client.post("/api/v1/auth/refresh", cookies={"refresh_token": "dummy"})
    assert resp.status_code == 403
    assert "Missing CSRF header" in resp.text

def test_resend_otp_rate_limit_and_invalidation(client, db):
    user = User(
        email="resend@test.com", phone="0987654321", password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT, full_name="Test User", status=UserStatusEnum.PENDING_VERIFICATION
    )
    db.add(user)
    db.commit()

    # Get preauth token
    resp = client.post("/api/v1/auth/login", json={"email": "resend@test.com", "password": "Password123!"})
    preauth = resp.json()["preauth_token"]

    # Clear rate limit if any
    from app.models.auth import ActionRateLimit
    db.query(ActionRateLimit).filter(ActionRateLimit.user_id == user.user_id, ActionRateLimit.action == "resend_otp").delete()
    db.commit()

    # Resend OTP 1
    r1 = client.post("/api/v1/auth/resend-otp", headers={"Authorization": f"Bearer {preauth}"})
    assert r1.status_code == 200

    # Resend OTP 2 immediately (should rate limit)
    r2 = client.post("/api/v1/auth/resend-otp", headers={"Authorization": f"Bearer {preauth}"})
    assert r2.status_code == 429
    
    # Store should have a valid OTP for this user
    assert user.user_id in _OTP_STORE

def test_change_password_requires_current(client, db):
    user = User(
        email="change@test.com", phone="1112223333", password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT, full_name="Test User", status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={"email": "change@test.com", "password": "Password123!"})
    access_token = resp.json()["access_token"]

    # Wrong current password
    r1 = client.post("/api/v1/auth/change-password-voluntary", json={
        "current_password": "WrongPassword1!",
        "new_password": "NewPassword123!"
    }, headers={"Authorization": f"Bearer {access_token}"})
    assert r1.status_code == 401

    # Right current password
    r2 = client.post("/api/v1/auth/change-password-voluntary", json={
        "current_password": "Password123!",
        "new_password": "NewPassword123!"
    }, headers={"Authorization": f"Bearer {access_token}"})
    assert r2.status_code == 200


