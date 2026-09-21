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
    verify_resp = client.post("/api/v1/auth/verify-otp", json={"user_id": user_id, "otp_code": otp_code})
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


def test_login_rejected_without_mfa_code(client):
    _, secret = _register_and_activate_doctor(client, email="drtotp_nocode@cryptcare.ai")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_nocode@cryptcare.ai", "password": "Password123!"},
    )
    assert resp.status_code == 401
    assert "MFA code required" in resp.text


def test_login_rejected_with_wrong_mfa_code(client):
    _, secret = _register_and_activate_doctor(client, email="drtotp_wrong@cryptcare.ai")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_wrong@cryptcare.ai", "password": "Password123!", "otp_code": "000000"},
    )
    assert resp.status_code == 401
    assert "Invalid MFA code" in resp.text


def test_login_succeeds_with_valid_totp_code(client):
    _, secret = _register_and_activate_doctor(client, email="drtotp_valid@cryptcare.ai")
    totp = pyotp.TOTP(secret)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_valid@cryptcare.ai", "password": "Password123!", "otp_code": totp.now()},
    )
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


def test_totp_code_cannot_be_replayed(client):
    _, secret = _register_and_activate_doctor(client, email="drtotp_replay@cryptcare.ai")
    totp = pyotp.TOTP(secret)
    code = totp.now()

    first = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_replay@cryptcare.ai", "password": "Password123!", "otp_code": code},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/v1/auth/login",
        json={"email": "drtotp_replay@cryptcare.ai", "password": "Password123!", "otp_code": code},
    )
    assert second.status_code == 401
    assert "already been used" in second.text
