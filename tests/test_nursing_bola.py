import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.user import User, PatientProfile, DoctorProfile
from app.core.security import create_access_token

@pytest.fixture
def nursing_test_data(db):
    # Patient A
    pA = User(email="pat_nurs@test.com", phone="1", password_hash="hash", role="PATIENT", full_name="Pat A", status="ACTIVE")
    db.add(pA)
    db.flush()
    pA_prof = PatientProfile(user_id=pA.user_id, patient_id="pat_nurs_1")
    db.add(pA_prof)
    
    # Doctor A (has consent for Patient A)
    dA = User(email="doc_nursA@test.com", phone="2", password_hash="hash", role="DOCTOR", full_name="Doc A", status="ACTIVE")
    db.add(dA)
    db.flush()
    dA_prof = DoctorProfile(user_id=dA.user_id, doctor_id="doc_nurs_1", license_number="L1")
    db.add(dA_prof)
    
    # Doctor B (NO consent for Patient A)
    dB = User(email="doc_nursB@test.com", phone="3", password_hash="hash", role="DOCTOR", full_name="Doc B", status="ACTIVE")
    db.add(dB)
    db.flush()
    dB_prof = DoctorProfile(user_id=dB.user_id, doctor_id="doc_nurs_2", license_number="L2")
    db.add(dB_prof)
    
    # Nurse
    nurse = User(email="nurse@test.com", phone="4", password_hash="hash", role="NURSE", full_name="Nurse A", status="ACTIVE")
    db.add(nurse)
    db.flush()
    
    # Consent for Doc A -> Pat A
    from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum
    from datetime import datetime, timedelta
    consent_dA = ConsentRequest(
        patient_id=pA_prof.patient_id,
        grantee_id=dA.user_id,
        grantee_type=GranteeTypeEnum.DOCTOR,
        resource_type=ResourceTypeEnum.VITALS,
        permission=PermissionEnum.READ,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db.add(consent_dA)
    db.commit()
    
    return {
        "pA_id": pA_prof.patient_id,
        "dA_token": create_access_token(str(dA.user_id), "DOCTOR", []),
        "dB_token": create_access_token(str(dB.user_id), "DOCTOR", []),
        "nurse_id": nurse.user_id,
    }

def test_nursing_assign_bola(nursing_test_data):
    client = TestClient(app)
    data = nursing_test_data
    
    # Doctor A can assign (has consent)
    res_a = client.post("/api/v1/nursing/assign", json={
        "patient_id": data["pA_id"],
        "nurse_id": data["nurse_id"],
        "resource_type": "vitals",
        "permission": "READ"
    }, headers={"Authorization": f"Bearer {data['dA_token']}"})
    assert res_a.status_code == 201
    assignment_id = res_a.json()["assignment_id"]
    
    # Doctor B CANNOT assign (no consent)
    res_b = client.post("/api/v1/nursing/assign", json={
        "patient_id": data["pA_id"],
        "nurse_id": data["nurse_id"],
        "resource_type": "vitals",
        "permission": "READ"
    }, headers={"Authorization": f"Bearer {data['dB_token']}"})
    assert res_b.status_code == 403
    assert "active care relationship" in res_b.text

    # Doctor B CANNOT remove (no consent)
    res_rm_b = client.post(f"/api/v1/nursing/assignments/{assignment_id}/remove", headers={"Authorization": f"Bearer {data['dB_token']}"})
    assert res_rm_b.status_code == 403
    assert "active care relationship" in res_rm_b.text
    
    # Doctor A CAN remove (has consent)
    res_rm_a = client.post(f"/api/v1/nursing/assignments/{assignment_id}/remove", headers={"Authorization": f"Bearer {data['dA_token']}"})
    assert res_rm_a.status_code == 200
