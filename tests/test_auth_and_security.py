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

    # 2. Extract OTP from store and verify OTP
    assert user_id in _OTP_STORE
    otp_code = _OTP_STORE[user_id]["code"]
    
    verify_resp = client.post("/api/v1/auth/verify-otp", json={"user_id": user_id, "otp_code": otp_code})
    assert verify_resp.status_code == 200, verify_resp.text
    verified_data = verify_resp.json()
    assert verified_data["status"] == "ACTIVE"

    # 3. Login Patient
    login_payload = {
        "email": "testpatient@cryptcare.ai",
        "password": "Password123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200, response.text
    login_data = response.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data


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

