"""
Phase 6 — Nurse role & vital signs.

Follows the same db-fixture + direct-token pattern as
tests/test_patient_and_consent.py (setup_users/get_auth_header) rather than
driving full register/login/MFA flows here — those are already covered by
tests/test_mfa_totp.py. This file focuses on the new RBAC + consent-gating
behavior: a nurse can request consent, record vitals once approved, is
blocked without approval, and a patient can always read their own vitals.
"""

from app.core.security import create_access_token
from app.core.security import hash_password
from app.models.user import DoctorProfile, NurseProfile, PatientProfile, RoleEnum, User, UserStatusEnum
from app.services.auth_service import ROLE_PERMISSIONS


def _make_user(db, email, role, **profile_kwargs):
    user = User(
        email=email,
        phone=f"+1{abs(hash(email)) % 10**9:09d}",
        password_hash=hash_password("Password123!"),
        role=role,
        full_name=f"Test {role.value.title()}",
        status=UserStatusEnum.ACTIVE,
    )
    db.add(user)
    db.flush()

    if role == RoleEnum.PATIENT:
        profile = PatientProfile(user_id=user.user_id, **profile_kwargs)
        db.add(profile)
        db.commit()
        return user, profile
    if role == RoleEnum.NURSE:
        profile = NurseProfile(user_id=user.user_id, license_number="RN-TEST-001", **profile_kwargs)
        db.add(profile)
        db.commit()
        return user, profile
    if role == RoleEnum.DOCTOR:
        profile = DoctorProfile(user_id=user.user_id, license_number="DOC-TEST-001", **profile_kwargs)
        db.add(profile)
        db.commit()
        return user, profile

    db.commit()
    return user, None


def _auth_header(user_id: str, role: RoleEnum) -> dict:
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}


def test_nurse_role_appears_in_role_permissions():
    assert "vault:write:vitals" in ROLE_PERMISSIONS[RoleEnum.NURSE]


def test_nurse_blocked_from_recording_vitals_without_consent(client, db):
    patient_user, patient_profile = _make_user(db, "vitals_patient_1@medivault.ai", RoleEnum.PATIENT)
    nurse_user, _ = _make_user(db, "vitals_nurse_1@medivault.ai", RoleEnum.NURSE)
    nurse_headers = _auth_header(nurse_user.user_id, RoleEnum.NURSE)

    resp = client.post(
        "/api/v1/nursing/vitals",
        json={"patient_id": patient_profile.patient_id, "heart_rate_bpm": 78},
        headers=nurse_headers,
    )
    assert resp.status_code == 403
    assert "No active consent" in resp.text


def test_nurse_records_vitals_after_consent_flow(client, db):
    patient_user, patient_profile = _make_user(db, "vitals_patient_2@medivault.ai", RoleEnum.PATIENT)
    nurse_user, _ = _make_user(db, "vitals_nurse_2@medivault.ai", RoleEnum.NURSE)
    patient_headers = _auth_header(patient_user.user_id, RoleEnum.PATIENT)
    nurse_headers = _auth_header(nurse_user.user_id, RoleEnum.NURSE)

    # 1. Nurse requests WRITE access to vitals.
    req = client.post(
        "/api/v1/consent/request",
        json={"patient_id": patient_profile.patient_id, "resource_type": "vitals", "permission": "BOTH"},
        headers=nurse_headers,
    )
    assert req.status_code == 201, req.text
    consent_id = req.json()["consent_id"]

    # 2. Patient approves.
    approve = client.put(
        f"/api/v1/consent/{consent_id}/approve",
        json={"duration_days": 7},
        headers=patient_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "ACTIVE"

    # 3. Nurse records vitals.
    record = client.post(
        "/api/v1/nursing/vitals",
        json={
            "patient_id": patient_profile.patient_id,
            "heart_rate_bpm": 72,
            "blood_pressure_systolic": 118,
            "blood_pressure_diastolic": 76,
            "temperature_celsius": 36.9,
            "spo2_percent": 98,
            "notes": "Patient resting comfortably, no acute distress.",
        },
        headers=nurse_headers,
    )
    assert record.status_code == 201, record.text
    body = record.json()
    assert body["heart_rate_bpm"] == 72
    assert body["notes"] == "Patient resting comfortably, no acute distress."  # decrypted round-trip

    # 4. Nurse reads it back.
    listing = client.get(f"/api/v1/nursing/patients/{patient_profile.patient_id}/vitals", headers=nurse_headers)
    assert listing.status_code == 200, listing.text
    assert len(listing.json()["vitals"]) == 1

    # 5. Patient can always read their own vitals too, no separate grant needed.
    patient_view = client.get(f"/api/v1/nursing/patients/{patient_profile.patient_id}/vitals", headers=patient_headers)
    assert patient_view.status_code == 200, patient_view.text
    assert len(patient_view.json()["vitals"]) == 1


def test_non_nurse_role_cannot_record_vitals_even_with_consent(client, db):
    """A DOCTOR with an active BOTH-permission vitals grant still can't hit
    the nurse-only write path — role check inside nursing_service.record_vitals
    is a second, independent gate on top of the consent check."""
    patient_user, patient_profile = _make_user(db, "vitals_patient_3@medivault.ai", RoleEnum.PATIENT)
    doctor_user, _ = _make_user(db, "vitals_doctor_3@medivault.ai", RoleEnum.DOCTOR)
    patient_headers = _auth_header(patient_user.user_id, RoleEnum.PATIENT)
    doctor_headers = _auth_header(doctor_user.user_id, RoleEnum.DOCTOR)

    req = client.post(
        "/api/v1/consent/request",
        json={"patient_id": patient_profile.patient_id, "resource_type": "vitals", "permission": "BOTH"},
        headers=doctor_headers,
    )
    consent_id = req.json()["consent_id"]
    client.put(f"/api/v1/consent/{consent_id}/approve", json={"duration_days": 7}, headers=patient_headers)

    resp = client.post(
        "/api/v1/nursing/vitals",
        json={"patient_id": patient_profile.patient_id, "heart_rate_bpm": 70},
        headers=doctor_headers,
    )
    assert resp.status_code == 403
    assert "Only nurses" in resp.text


def test_negative_vitals_blocked(client, db):
    patient_user, patient_profile = _make_user(db, "vitals_patient_4@medivault.ai", RoleEnum.PATIENT)
    nurse_user, _ = _make_user(db, "vitals_nurse_4@medivault.ai", RoleEnum.NURSE)
    patient_headers = _auth_header(patient_user.user_id, RoleEnum.PATIENT)
    nurse_headers = _auth_header(nurse_user.user_id, RoleEnum.NURSE)

    req = client.post(
        "/api/v1/consent/request",
        json={"patient_id": patient_profile.patient_id, "resource_type": "vitals", "permission": "BOTH"},
        headers=nurse_headers,
    )
    consent_id = req.json()["consent_id"]
    client.put(f"/api/v1/consent/{consent_id}/approve", json={"duration_days": 7}, headers=patient_headers)

    # Negative heart rate
    resp = client.post(
        "/api/v1/nursing/vitals",
        json={"patient_id": patient_profile.patient_id, "heart_rate_bpm": -10},
        headers=nurse_headers,
    )
    assert resp.status_code == 422
    
    # Out of bounds temperature
    resp = client.post(
        "/api/v1/nursing/vitals",
        json={"patient_id": patient_profile.patient_id, "temperature_celsius": 10.0},
        headers=nurse_headers,
    )
    assert resp.status_code == 422


def test_patient_cannot_access_other_patient_vitals(client, db):
    patient_a, profile_a = _make_user(db, "vitals_patient_a@medivault.ai", RoleEnum.PATIENT)
    patient_b, profile_b = _make_user(db, "vitals_patient_b@medivault.ai", RoleEnum.PATIENT)
    patient_a_headers = _auth_header(patient_a.user_id, RoleEnum.PATIENT)

    resp = client.get(f"/api/v1/nursing/patients/{profile_b.patient_id}/vitals", headers=patient_a_headers)
    assert resp.status_code == 403
