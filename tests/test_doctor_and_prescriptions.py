import pytest
from datetime import datetime, timedelta
from app.core.security import create_access_token
from app.services.auth_service import ROLE_PERMISSIONS
from app.models.user import RoleEnum, User, PatientProfile, DoctorProfile, UserStatusEnum
from app.core.security import hash_password
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum

def setup_doctor_and_patient(db):
    # Patient User
    patient_user = User(
        email="rx_patient@cryptcare.ai",
        phone="+1000000001",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT,
        full_name="Rx Patient",
        status=UserStatusEnum.ACTIVE
    )
    db.add(patient_user)
    db.flush()
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)

    # Doctor User
    doctor_user = User(
        email="rx_doctor@cryptcare.ai",
        phone="+2000000002",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. Prescriber",
        status=UserStatusEnum.ACTIVE
    )
    db.add(doctor_user)
    db.flush()
    doctor_profile = DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-9999")
    db.add(doctor_profile)

    # Active consent from Patient to Doctor (BOTH read and write)
    consent = ConsentRequest(
        patient_id=patient_profile.patient_id,
        grantee_id=doctor_user.user_id,
        grantee_type=GranteeTypeEnum.DOCTOR,
        resource_type=ResourceTypeEnum.PRESCRIPTIONS,
        permission=PermissionEnum.BOTH,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(consent)
    db.commit()

    return patient_profile.patient_id, patient_user.user_id, doctor_user.user_id

def get_auth_header(user_id: str, role: RoleEnum):
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}

def test_prescription_creation_and_qr(client, db):
    patient_id, patient_user_id, doctor_user_id = setup_doctor_and_patient(db)

    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    patient_headers = get_auth_header(patient_user_id, RoleEnum.PATIENT)

    # 1. Doctor creates prescription
    rx_payload = {
        "patient_id": patient_id,
        "diagnosis": "Acute Bronchitis",
        "notes": "Rest and drink plenty of fluids.",
        "items": [
            {
                "medicine_name": "Amoxicillin 500mg",
                "dosage": "1 capsule 3x daily",
                "frequency": "TID",
                "duration_days": 7
            }
        ]
    }
    resp = client.post("/api/v1/vault/prescriptions", json=rx_payload, headers=doctor_headers)
    assert resp.status_code == 201, resp.text
    rx_data = resp.json()
    prescription_id = rx_data["prescription_id"]
    # Verify diagnosis field returned on creation is encrypted ciphertext blob
    assert rx_data["diagnosis"].startswith("v1:")

    # 2. Patient lists prescriptions (reads decrypted diagnosis)
    resp = client.get(f"/api/v1/vault/prescriptions?patient_id={patient_id}", headers=patient_headers)
    assert resp.status_code == 200, resp.text
    rx_list = resp.json()
    assert len(rx_list) == 1
    assert rx_list[0]["prescription_id"] == prescription_id
    assert rx_list[0]["diagnosis"] == "Acute Bronchitis"

    # 3. Patient downloads prescription QR code [NEW feature]
    resp = client.get(f"/api/v1/vault/prescriptions/{prescription_id}/qr", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0
