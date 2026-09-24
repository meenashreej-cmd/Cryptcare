
import pytest
from app.core.security import create_access_token
from app.models.user import RoleEnum
from tests.test_lab_and_imaging import setup_lab_environment, get_auth_header
import io

def test_patient_cannot_upload_report(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    patient_headers = get_auth_header(patient_user_id, RoleEnum.PATIENT)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    
    # 1. Doctor creates lab test request
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    
    client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    
    # 2. Patient tries to upload report
    file_content = b"%PDF-1.4 Mock Encrypted Imaging Report Data Binary"
    files = {"file": ("chest_xray.dcm", io.BytesIO(file_content), "application/dicom")}
    data = {"summary_text": "...", "document_type": "XRAY"}
    
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=patient_headers)
    assert resp.status_code == 403
    assert "not permitted" in resp.json()["detail"] or "Only lab staff" in resp.json()["detail"]

def test_lab_concurrent_claim(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    
    # lab starts
    resp = client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    assert resp.status_code == 200
    
    # second lab (same user for now, but trying to start again)
    resp2 = client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    assert resp2.status_code == 409
    assert "already IN_PROGRESS" in resp2.json()["detail"]

def test_lab_b_cannot_upload_to_lab_a(client, db):
    from app.models.user import User, LabProfile, UserStatusEnum
    from app.core.security import hash_password
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    
    # Create LAB B
    lab_b = User(
        email="lab_b@cryptcare.ai",
        phone="+9999999999",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.LAB,
        full_name="Lab B",
        status=UserStatusEnum.ACTIVE
    )
    db.add(lab_b)
    db.flush()
    lab_b_profile = LabProfile(user_id=lab_b.user_id, license_number="LAB-B-1")
    db.add(lab_b_profile)
    db.commit()
    
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_a_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    lab_b_headers = get_auth_header(lab_b.user_id, RoleEnum.LAB)
    
    # Doctor creates request
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    
    # Lab A starts it
    client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_a_headers)
    
    # Lab B tries to upload report
    file_content = b"Mock"
    files = {"file": ("report.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {"summary_text": "...", "document_type": "PDF_REPORT"}
    
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=lab_b_headers)
    assert resp.status_code == 403
    assert "assigned to a different lab technician" in resp.json()["detail"]

