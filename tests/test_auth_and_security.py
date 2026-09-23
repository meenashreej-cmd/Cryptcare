import pytest
from app.core.encryption import encrypt, decrypt
from app.core.security import (
    create_access_token,
    verify_access_token,
    verify_password,
    hash_password,
)
from app.services.auth_service import _OTP_STORE

def test_encryption_decryption_flow():
    plaintext = "Patient Medical Record Secret Data"
    
    blob = encrypt(plaintext)
    assert blob is not None
    assert blob.count(":") == 2
    
    decrypted_text = decrypt(blob)
    assert decrypted_text == plaintext

def test_security_token_generation():
    token = create_access_token(user_id="user_test_id", role="PATIENT", permissions=["read:own"])
    assert token is not None
    
    payload = verify_access_token(token)
    assert payload["sub"] == "user_test_id"
    assert payload["role"] == "PATIENT"

def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_auth_registration_otp_and_login(client):
    # 1. Register Patient
    patient_payload = {
        "email": "testpatient@cryptcare.ai",
        "phone": "+1234567890",
        "password": "Password123!",
        "full_name": "Test Patient",
        "role": "PATIENT"
    }
    response = client.post("/api/v1/auth/register", json=patient_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "user_id" in data
    user_id = data["user_id"]
    assert data["status"] == "PENDING_VERIFICATION"

    # 1.5. Login to get preauth_token
    login_payload = {
        "email": "testpatient@cryptcare.ai",
        "password": "Password123!"
    }
    login_resp = client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    print("LOGIN DATA:", login_data)
    assert login_data["requires_otp"] is True
    preauth_token = login_data["preauth_token"]

    # 2. Extract OTP from store and verify OTP
    from app.services.auth_service import _OTP_STORE
    assert user_id in _OTP_STORE
    otp_code = _OTP_STORE[user_id]["code"]
    
    verify_resp = client.post(
        "/api/v1/auth/verify-otp", 
        json={"otp_code": otp_code},
        headers={"Authorization": f"Bearer {preauth_token}"}
    )
    assert verify_resp.status_code == 200, verify_resp.text
    verified_data = verify_resp.json()
    assert verified_data["status"] == "ACTIVE"

    # 3. Login Patient
    login_resp2 = client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp2.status_code == 200, login_resp2.text
    login_data2 = login_resp2.json()
    assert "access_token" in login_data2
    assert "refresh_token" in login_resp2.cookies


def test_jwt_tampering_fails():
    import base64
    import json
    from fastapi import HTTPException
    
    # Generate a valid token
    token = create_access_token(user_id="user_test_id", role="PATIENT", permissions=["read:own"])
    
    # Split token into parts
    header_b64, payload_b64, signature_b64 = token.split('.')
    
    # Decode payload
    def decode_b64(b64_str):
        padded = b64_str + '=' * (4 - len(b64_str) % 4)
        return base64.urlsafe_b64decode(padded).decode('utf-8')
    
    payload_str = decode_b64(payload_b64)
    payload_dict = json.loads(payload_str)
    
    # Tamper with the role
    payload_dict["role"] = "ADMIN"
    
    # Re-encode payload
    tampered_payload_str = json.dumps(payload_dict)
    tampered_payload_b64 = base64.urlsafe_b64encode(tampered_payload_str.encode('utf-8')).decode('utf-8').rstrip('=')
    
    # Reconstruct token with original signature
    tampered_token = f"{header_b64}.{tampered_payload_b64}.{signature_b64}"
    
    # Verification should fail due to signature mismatch
    from app.core.security import TokenError
    with pytest.raises(TokenError) as exc_info:
        verify_access_token(tampered_token)
    
    assert "Signature verification failed" in str(exc_info.value)


def test_registration_allowlist(client):
    admin_payload = {
        "email": "admin@cryptcare.com",
        "phone": "+10000000001",
        "password": "SuperSecretPassword123!",
        "full_name": "Admin User",
        "role": "ADMIN"
    }
    response = client.post("/api/v1/auth/register", json=admin_payload)
    assert response.status_code == 400
    assert "Role not permitted for self-registration" in response.json()["detail"]

def test_mass_assignment_and_token_omission(client):
    payload = {
        "email": "hospadmin@cryptcare.com",
        "phone": "+10000000002",
        "password": "SuperSecretPassword123!",
        "full_name": "Hospital Admin",
        "role": "HOSPITAL_ADMIN",
        "hospital_name": "General Hospital",
        "status": "ACTIVE",
        "is_active": True,
        "is_verified": True
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert data["status"] == "PENDING_VERIFICATION"
    assert data["license_verified"] is False


def test_account_lockout_expires_after_15_minutes(client, db):
    print("STARTING TEST")
    import time
    unique_email = f"lockout_test_{int(time.time())}@cryptcare.ai"
    patient_payload = {
        "email": unique_email,
        "phone": f"+1{int(time.time())%10000000000:010d}",
        "password": "Password123!",
        "full_name": "Lockout Test",
        "role": "PATIENT"
    }
    client.post("/api/v1/auth/register", json=patient_payload)
    print("REGISTERED")

    bad_login = {"email": unique_email, "password": "WrongPassword!"}
    for i in range(6):
        print(f"BAD LOGIN {i}")
        resp = client.post("/api/v1/auth/login", json=bad_login, headers={"X-Forwarded-For": f"10.1.1.{i}"})
        print(f"BAD LOGIN {i} DONE, status: {resp.status_code}")
        assert resp.status_code == 401
        
    print("GOOD LOGIN (SHOULD FAIL)")
    good_login = {"email": unique_email, "password": "Password123!"}
    
    import app.services.auth_service as auth_service
    from datetime import datetime, timezone, timedelta
    from unittest.mock import patch
    
    future_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=16)
    
    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return future_time
            
    print("PATCHING DATETIME AND GOOD LOGIN")
    with patch("app.services.auth_service.datetime", new=MockDatetime):
        resp = client.post("/api/v1/auth/login", json=good_login, headers={"X-Forwarded-For": "10.0.0.100"})
        print(f"GOOD LOGIN DONE, status: {resp.status_code}")
        assert resp.status_code == 200
    print("TEST DONE")

