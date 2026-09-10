import pytest
from app.core.security import create_access_token
from app.services.auth_service import ROLE_PERMISSIONS
from app.models.user import RoleEnum, User, PatientProfile, DoctorProfile, UserStatusEnum
from app.core.security import hash_password

def setup_users(db):
    # Patient User
    patient_user = User(
        email="patient@medivault.ai",
        phone="+1111111111",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT,
        full_name="Patient Zero",
        status=UserStatusEnum.ACTIVE
    )
    db.add(patient_user)
    db.flush()
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)

    # Caregiver User
    caregiver_user = User(
        email="caregiver@medivault.ai",
        phone="+3333333333",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT,
        full_name="Caregiver Family",
        status=UserStatusEnum.ACTIVE
    )
    db.add(caregiver_user)

    # Doctor User
    doctor_user = User(
        email="doctor@medivault.ai",
        phone="+2222222222",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. House",
        status=UserStatusEnum.ACTIVE
    )
    db.add(doctor_user)
    db.flush()
    doctor_profile = DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-1234")
    db.add(doctor_profile)

    db.commit()
    return patient_profile.patient_id, patient_user.user_id, doctor_user.user_id, caregiver_user.email

def get_auth_header(user_id: str, role: RoleEnum):
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def env(db):
    patient_id, patient_user_id, doctor_user_id, caregiver_email = setup_users(db)
    return {
        "patient_id": patient_id,
        "patient_user_id": patient_user_id,
        "doctor_user_id": doctor_user_id,
        "caregiver_email": caregiver_email,
        "patient_headers": get_auth_header(patient_user_id, RoleEnum.PATIENT),
        "doctor_headers": get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    }

def test_consent_request_and_approval(client, env):
    # 1. Doctor requests consent
    req_payload = {
        "patient_id": env["patient_id"],
        "resource_type": "prescriptions",
        "permission": "READ"
    }
    resp = client.post("/api/v1/consent/request", json=req_payload, headers=env["doctor_headers"])
    assert resp.status_code == 201, resp.text
    consent_id = resp.json()["consent_id"]
    
    # 2. Patient views requests
    resp = client.get("/api/v1/consent/history", headers=env["patient_headers"])
    history = resp.json()["consents"]
    assert any(c["consent_id"] == consent_id for c in history)
    
    # 3. Patient approves consent
    resp = client.put(f"/api/v1/consent/{consent_id}/approve", json={"duration_days": 30}, headers=env["patient_headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"


def test_caregiver_grant(client, env):
    caregiver_payload = {
        "caregiver_email": env["caregiver_email"],
        "resource_type": "prescriptions",
        "permission": "READ",
        "duration_days": 90
    }
    resp = client.post("/api/v1/consent/caregiver/grant", json=caregiver_payload, headers=env["patient_headers"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["grantee_type"] == "CAREGIVER"


def test_break_glass_emergency_access(client, env):
    break_glass_payload = {
        "patient_id": env["patient_id"],
        "resource_type": "all",
        "permission": "READ",
        "reason": "Severe ER trauma emergency requiring instant record access"
    }
    resp = client.post("/api/v1/consent/break-glass", json=break_glass_payload, headers=env["doctor_headers"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_break_glass"] is True


def test_consent_timeline(client, env):
    # Perform an action to create a timeline entry
    req_payload = {
        "patient_id": env["patient_id"],
        "resource_type": "prescriptions",
        "permission": "READ"
    }
    client.post("/api/v1/consent/request", json=req_payload, headers=env["doctor_headers"])
    
    resp = client.get("/api/v1/consent/timeline", headers=env["patient_headers"])
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["entries"]) >= 1


def test_consent_revocation(client, env):
    req_payload = {
        "patient_id": env["patient_id"],
        "resource_type": "prescriptions",
        "permission": "READ"
    }
    resp = client.post("/api/v1/consent/request", json=req_payload, headers=env["doctor_headers"])
    consent_id = resp.json()["consent_id"]
    
    client.put(f"/api/v1/consent/{consent_id}/approve", json={"duration_days": 30}, headers=env["patient_headers"])
    
    resp = client.post(f"/api/v1/consent/revoke/{consent_id}", headers=env["patient_headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REVOKED"
