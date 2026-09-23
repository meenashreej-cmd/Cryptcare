
import pytest
from app.core.security import create_preauth_token
from app.models.user import RoleEnum

def test_verify_otp_security(client, db):
    # 1. Setup a user
    resp = client.post("/api/v1/auth/register", json={
        "email": "otp_test@cryptcare.ai",
        "phone": "+1999888777",
        "password": "Password123!",
        "role": "PATIENT",
        "full_name": "OTP Test",
        "dob": "1990-01-01"
    })
    assert resp.status_code == 201
    user_id = resp.json()["user_id"]

    # Try login to get preauth token
    resp = client.post("/api/v1/auth/login", json={
        "email": "otp_test@cryptcare.ai",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    preauth_token = resp.json()["preauth_token"]

    # Preauth token cannot be used for access
    headers = {"Authorization": f"Bearer {preauth_token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
    assert "invalid or expired" in resp.json()["detail"].lower() or "expected access" in resp.json()["detail"].lower()

    # Get OTP from store for testing
    from app.services.auth_service import _OTP_STORE
    otp_code = _OTP_STORE[user_id]["code"]

    # Verify OTP successfully
    resp = client.post("/api/v1/auth/verify-otp", json={"otp_code": otp_code}, headers=headers)
    assert resp.status_code == 200

    # Try to verify OTP again with the SAME preauth token (reused challenge)
    from datetime import datetime, timezone, timedelta
    _OTP_STORE[user_id] = {
        "code": "123456",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0
    }
    
    resp = client.post("/api/v1/auth/verify-otp", json={"otp_code": "123456"}, headers=headers)
    assert resp.status_code == 401
    assert "token already used" in resp.json()["detail"].lower()

