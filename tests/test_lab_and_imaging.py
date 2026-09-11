import io
import pytest
from datetime import datetime, timedelta
from app.core.security import create_access_token
from app.services.auth_service import ROLE_PERMISSIONS
from app.models.user import RoleEnum, User, PatientProfile, DoctorProfile, LabProfile, UserStatusEnum
from app.core.security import hash_password
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum

def setup_lab_environment(db):
    # Patient User
    patient_user = User(
        email="lab_patient@cryptcare.ai",
        phone="+1555555555",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT,
        full_name="Lab Patient",
        status=UserStatusEnum.ACTIVE
    )
    db.add(patient_user)
    db.flush()
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)

    # Doctor User
    doctor_user = User(
        email="lab_doctor@cryptcare.ai",
        phone="+2555555555",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. LabRequester",
        status=UserStatusEnum.ACTIVE
    )
    db.add(doctor_user)
    db.flush()
    doctor_profile = DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-LAB-1")
    db.add(doctor_profile)

    # Lab Tech User
    lab_user = User(
        email="lab_tech@cryptcare.ai",
        phone="+3555555555",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.LAB,
        full_name="Lab Technician",
        status=UserStatusEnum.ACTIVE
    )
    db.add(lab_user)
    db.flush()
    lab_profile = LabProfile(user_id=lab_user.user_id, license_number="LAB-TECH-1")
    db.add(lab_profile)

    # Doctor consent for lab_requests
    doc_consent = ConsentRequest(
        patient_id=patient_profile.patient_id,
        grantee_id=doctor_user.user_id,
        grantee_type=GranteeTypeEnum.DOCTOR,
        resource_type=ResourceTypeEnum.LAB_REQUESTS,
        permission=PermissionEnum.BOTH,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    # Lab consent for lab_reports
    lab_consent = ConsentRequest(
        patient_id=patient_profile.patient_id,
        grantee_id=lab_user.user_id,
        grantee_type=GranteeTypeEnum.LAB,
        resource_type=ResourceTypeEnum.LAB_REPORTS,
        permission=PermissionEnum.BOTH,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    # Patient consent for reading lab reports
    patient_report_consent = ConsentRequest(
        patient_id=patient_profile.patient_id,
        grantee_id=patient_user.user_id,
        grantee_type=GranteeTypeEnum.CAREGIVER, # or self
        resource_type=ResourceTypeEnum.LAB_REPORTS,
        permission=PermissionEnum.READ,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )

    db.add_all([doc_consent, lab_consent, patient_report_consent])
    db.commit()

    return patient_profile.patient_id, patient_user.user_id, doctor_user.user_id, lab_user.user_id

def get_auth_header(user_id: str, role: RoleEnum):
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}

def test_lab_request_and_encrypted_imaging_upload(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)

    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    patient_headers = get_auth_header(patient_user_id, RoleEnum.PATIENT)

    # 1. Doctor creates lab test request
    req_payload = {
        "patient_id": patient_id,
        "test_name": "Chest X-Ray / CT Imaging"
    }
    resp = client.post("/api/v1/lab/requests", json=req_payload, headers=doctor_headers)
    assert resp.status_code == 201, resp.text
    lab_req_data = resp.json()
    request_id = lab_req_data["request_id"]
    assert lab_req_data["status"] == "REQUESTED"

    # 2. Lab technician starts processing
    resp = client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "IN_PROGRESS"

    # 3. Lab technician uploads encrypted imaging report (PDF / DICOM mock) [NEW imaging feature]
    file_content = b"%PDF-1.4 Mock Encrypted Imaging Report Data Binary"
    files = {"file": ("chest_xray.dcm", io.BytesIO(file_content), "application/dicom")}
    data = {
        "summary_text": "Clear lung fields, no infiltrates or effusion.",
        "document_type": "XRAY"
    }
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=lab_headers)
    assert resp.status_code == 201, resp.text
    report_data = resp.json()
    report_id = report_data["report_id"]
    assert report_data["document_type"] == "XRAY"

    # 4. Patient reads report and decrypts summary
    resp = client.get(f"/api/v1/lab/reports/{report_id}", headers=patient_headers)
    assert resp.status_code == 200, resp.text
    res_report = resp.json()
    assert res_report["summary"] == "Clear lung fields, no infiltrates or effusion."


def test_lab_upload_rejects_disallowed_extensions(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    
    files = {"file": ("malicious.exe", b"fake data", "application/x-msdownload")}
    data = {"summary_text": "...", "document_type": "PDF_REPORT"}
    
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=lab_headers)
    assert resp.status_code == 400
    assert "File extension" in resp.text


def test_lab_upload_rejects_mismatched_mime_types(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    
    # PDF extension but text/html MIME type
    files = {"file": ("report.pdf", b"<html>fake pdf</html>", "text/html")}
    data = {"summary_text": "...", "document_type": "PDF_REPORT"}
    
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=lab_headers)
    assert resp.status_code == 400
    assert "MIME type" in resp.text


def test_lab_upload_rejects_path_traversal(client, db):
    patient_id, patient_user_id, doctor_user_id, lab_user_id = setup_lab_environment(db)
    doctor_headers = get_auth_header(doctor_user_id, RoleEnum.DOCTOR)
    lab_headers = get_auth_header(lab_user_id, RoleEnum.LAB)
    
    resp = client.post("/api/v1/lab/requests", json={"patient_id": patient_id, "test_name": "Test"}, headers=doctor_headers)
    request_id = resp.json()["request_id"]
    client.put(f"/api/v1/lab/requests/{request_id}/start", headers=lab_headers)
    
    # Path traversal attempt in filename
    files = {"file": ("../../../secret_report.pdf", b"%PDF-fake", "application/pdf")}
    data = {"summary_text": "...", "document_type": "PDF_REPORT"}
    
    resp = client.post(f"/api/v1/lab/requests/{request_id}/report", data=data, files=files, headers=lab_headers)
    assert resp.status_code == 400
    assert "Invalid filename" in resp.text
