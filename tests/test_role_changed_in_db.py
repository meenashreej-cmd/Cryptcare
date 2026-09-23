
import pytest
from app.models.user import RoleEnum, UserStatusEnum
from app.core.security import create_access_token
from tests.test_lab_and_imaging import setup_lab_environment, get_auth_header

def test_role_changed_in_db(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    
    from app.models.user import User
    doctor = db.query(User).filter(User.user_id == doctor_user_id).first()
    doctor.role = RoleEnum.PATIENT
    db.commit()

    resp = client.post("/api/v1/consent/request", json={
        "patient_id": patient_id,
        "resource_type": "prescriptions"
    }, headers=doctor_headers)
    assert resp.status_code == 403
    assert "not permitted" in resp.json()["detail"].lower()

def test_pending_user_with_old_jwt(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    
    patient_headers = get_auth_header(patient_user_id, RoleEnum.PATIENT)
    
    from app.models.user import User
    patient = db.query(User).filter(User.user_id == patient_user_id).first()
    patient.status = UserStatusEnum.PENDING_VERIFICATION
    db.commit()

    resp = client.get("/api/v1/auth/me", headers=patient_headers)
    assert resp.status_code == 401
    assert "not active" in resp.json()["detail"].lower()

