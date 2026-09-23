"""
Phase 5 hardening — real TOTP MFA.

Covers: a DOCTOR account gets an MFA secret provisioned at registration,
login is rejected without a code, rejected with a wrong code, rejected on
immediate replay of the same code, and succeeds with a fresh valid code.
"""

import pyotp

from app.services.auth_service import _OTP_STORE
from app.data.license_registry import LICENSE_REGISTRY
from app.models.user import RoleEnum

_assigned_licenses = set()

def _get_unique_doctor_license():
    for lic in LICENSE_REGISTRY[RoleEnum.DOCTOR]:
        if lic not in _assigned_licenses:
            _assigned_licenses.add(lic)
            return lic
    raise Exception("Out of doctor licenses in registry for tests!")

def _register_and_activate_doctor(client, email="drtotp@cryptcare.ai"):
    payload = {
        "email": email,
        "phone": "+19995550111",
        "password": "Password123!",
        "full_name": "Dr. TOTP Test",
        "role": "DOCTOR",
        "license_number": _get_unique_doctor_license(),
        "specialization": "Cardiology",
        "hospital_name": "Test General",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    # MFA-required role: a provisioning URI must be returned exactly once.
    assert data["mfa_provisioning_uri"], "expected an MFA provisioning URI for a DOCTOR registration"
    secret = pyotp.parse_uri(data["mfa_provisioning_uri"]).secret

    user_id = data["user_id"]
    otp_code = _OTP_STORE[user_id]["code"]
    
    # Need to login to get the otp_verification preauth token
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert login_resp.status_code == 200
    preauth_token = login_resp.json()["preauth_token"]
    
    verify_resp = client.post("/api/v1/auth/verify-otp", json={"otp_code": otp_code}, headers={"Authorization": f"Bearer {preauth_token}"})
    assert verify_resp.status_code == 200, verify_resp.text

    return user_id, secret


def test_mfa_provisioning_uri_only_for_mfa_roles(client):
    patient_payload = {
        "email": "patient_no_mfa@cryptcare.ai",
        "phone": "+19995550100",
        "password": "Password123!",
        "full_name": "No MFA Patient",
        "role": "PATIENT",
    }
    response = client.post("/api/v1/auth/register", json=patient_payload)
    assert response.status_code == 201, response.text
    assert response.json()["mfa_provisioning_uri"] is None


def test_login_requires_enrollment_for_new_mfa_user(client):
    user_id, secret = _register_and_activate_doctor(client, email="drtotp_enroll@cryptcare.ai")
    
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_enroll@cryptcare.ai", "password": "Password123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("requires_mfa_enrollment") is True
    assert "preauth_token" in data
    
    protected = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['preauth_token']}"})
    assert protected.status_code == 401
    assert "token" in protected.text.lower()


def test_enroll_mfa_success_and_reuse_blocked(client):
    user_id, secret = _register_and_activate_doctor(client, email="drtotp_enroll_succ@cryptcare.ai")
    
    resp = client.post("/api/v1/auth/login", json={"email": "drtotp_enroll_succ@cryptcare.ai", "password": "Password123!"})
    preauth_token = resp.json()["preauth_token"]
    
    totp = pyotp.TOTP(secret)
    enroll_resp = client.post(
        "/api/v1/auth/enroll-mfa",
        json={"otp_code": totp.now()},
        headers={"Authorization": f"Bearer {preauth_token}"}
    )
    assert enroll_resp.status_code == 200
    
    enroll_resp2 = client.post(
        "/api/v1/auth/enroll-mfa",
        json={"otp_code": totp.now()},
        headers={"Authorization": f"Bearer {preauth_token}"}
    )
    assert enroll_resp2.status_code == 401
    assert "already used" in enroll_resp2.text.lower()


def test_login_fails_with_wrong_or_missing_code(client):
    user_id, secret = _register_and_activate_doctor(client, email="drtotp_login_fail@cryptcare.ai")
    
    resp = client.post("/api/v1/auth/login", json={"email": "drtotp_login_fail@cryptcare.ai", "password": "Password123!"})
    preauth_token = resp.json()["preauth_token"]
    
    totp = pyotp.TOTP(secret)
    client.post("/api/v1/auth/enroll-mfa", json={"otp_code": totp.now()}, headers={"Authorization": f"Bearer {preauth_token}"})
    
    resp_nocode = client.post("/api/v1/auth/login", json={"email": "drtotp_login_fail@cryptcare.ai", "password": "Password123!"})
    assert resp_nocode.status_code == 401
    assert "MFA code required" in resp_nocode.text
    
    resp_wrong = client.post("/api/v1/auth/login", json={"email": "drtotp_login_fail@cryptcare.ai", "password": "Password123!", "otp_code": "000000"})
    assert resp_wrong.status_code == 401
    assert "Invalid or expired MFA code" in resp_wrong.text


def test_login_succeeds_and_prevents_replay(client):
    user_id, secret = _register_and_activate_doctor(client, email="drtotp_login_succ@cryptcare.ai")
    
    resp = client.post("/api/v1/auth/login", json={"email": "drtotp_login_succ@cryptcare.ai", "password": "Password123!"})
    preauth_token = resp.json()["preauth_token"]
    
    totp = pyotp.TOTP(secret)
    client.post("/api/v1/auth/enroll-mfa", json={"otp_code": totp.now()}, headers={"Authorization": f"Bearer {preauth_token}"})
    
    import time
    next_code = totp.at(int(time.time()) + 30)
    
    resp_valid = client.post("/api/v1/auth/login", json={"email": "drtotp_login_succ@cryptcare.ai", "password": "Password123!", "otp_code": next_code})
    assert resp_valid.status_code == 200
    
    resp_replay = client.post("/api/v1/auth/login", json={"email": "drtotp_login_succ@cryptcare.ai", "password": "Password123!", "otp_code": next_code})
    assert resp_replay.status_code == 401
    assert "invalid or expired" in resp_replay.text.lower()
