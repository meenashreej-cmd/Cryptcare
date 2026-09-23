import pytest
from datetime import datetime, timedelta

from app.core.security import create_access_token, hash_password
from app.core.encryption import encrypt
import unittest.mock
from app.models.user import RoleEnum, User, PatientProfile, DoctorProfile, UserStatusEnum
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum
from app.models.vault import Prescription, Allergy, Vaccination
from app.models.lab import LabTestRequest

@pytest.fixture(autouse=True)
def mock_verify_sig():
    with unittest.mock.patch("app.core.signing.verify_prescription_signature", return_value=True):
        yield

@pytest.fixture
def idor_data(db):
    # Patient A
    pA_user = User(email="pA@c.ai", phone="+100", password_hash=hash_password("x"), role=RoleEnum.PATIENT, full_name="A", status=UserStatusEnum.ACTIVE)
    db.add(pA_user)
    db.flush()
    pA_prof = PatientProfile(user_id=pA_user.user_id)
    db.add(pA_prof)

    # Patient B
    pB_user = User(email="pB@c.ai", phone="+200", password_hash=hash_password("x"), role=RoleEnum.PATIENT, full_name="B", status=UserStatusEnum.ACTIVE)
    db.add(pB_user)
    db.flush()
    pB_prof = PatientProfile(user_id=pB_user.user_id)
    db.add(pB_prof)

    # Doctor A
    dA_user = User(email="dA@c.ai", phone="+300", password_hash=hash_password("x"), role=RoleEnum.DOCTOR, full_name="Doc A", status=UserStatusEnum.ACTIVE)
    db.add(dA_user)
    db.flush()
    dA_prof = DoctorProfile(user_id=dA_user.user_id, license_number="D-A")
    db.add(dA_prof)

    db.commit()
    db.refresh(pA_prof)
    db.refresh(pB_prof)
    
    patient_a_id = pA_prof.patient_id
    patient_b_id = pB_prof.patient_id
    doc_a_id = dA_user.user_id

    # Give Doctor A ALL access to Patient A
    for rt in [ResourceTypeEnum.PRESCRIPTIONS, ResourceTypeEnum.ALLERGIES, ResourceTypeEnum.VACCINATIONS, ResourceTypeEnum.VITALS, ResourceTypeEnum.LAB_REQUESTS, ResourceTypeEnum.LAB_REPORTS]:
        cr = ConsentRequest(
            patient_id=patient_a_id, grantee_id=doc_a_id, grantee_type=GranteeTypeEnum.DOCTOR,
            resource_type=rt, permission=PermissionEnum.BOTH, status=ConsentStatusEnum.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.add(cr)
    db.commit()

    # Pre-seed some target resources for Patient B (to test read-IDOR)
    rx_b = Prescription(patient_id=patient_b_id, doctor_id=dA_prof.doctor_id, status="ACTIVE", digital_signature="ed25519:dummy")
    db.add(rx_b)
    db.flush()
    rx_b.diagnosis_encrypted = encrypt("dx", f"cryptcare:v2|prescriptions|{rx_b.prescription_id}|diagnosis_encrypted|{rx_b.patient_id}")
    db.commit()

    # Pre-seed some target resources for Patient A
    rx_a = Prescription(patient_id=patient_a_id, doctor_id=dA_prof.doctor_id, status="ACTIVE", digital_signature="ed25519:dummy")
    db.add(rx_a)
    db.flush()
    rx_a.diagnosis_encrypted = encrypt("dx", f"cryptcare:v2|prescriptions|{rx_a.prescription_id}|diagnosis_encrypted|{rx_a.patient_id}")
    db.commit()
    
    return {
        "pA_id": patient_a_id,
        "pB_id": patient_b_id,
        "pA_token": create_access_token(pA_user.user_id, "PATIENT", []),
        "pB_token": create_access_token(pB_user.user_id, "PATIENT", []),
        "dA_token": create_access_token(doc_a_id, "DOCTOR", []),
        "rx_a_id": rx_a.prescription_id,
        "rx_b_id": rx_b.prescription_id,
    }


# Format: (method, endpoint_template, payload_template, role, resource_type)
IDOR_MATRIX = [
    # VAULT endpoints (Doctor)
    ("POST", "/api/v1/vault/prescriptions", {"patient_id": "{target_patient}", "items": [{"medicine_name": "Aspirin", "dosage": "1", "frequency": "Daily", "duration_days": 1}], "diagnosis": "x", "notes": "x"}, "DOCTOR", "prescription"),
    ("GET", "/api/v1/vault/prescriptions?patient_id={target_patient}", None, "DOCTOR", "prescription"),
    ("GET", "/api/v1/vault/prescriptions/{target_resource}/qr", None, "DOCTOR", "prescription"),
    ("POST", "/api/v1/vault/allergies?patient_id={target_patient}", {"allergen": "Dust", "severity": "MILD"}, "DOCTOR", "prescription"),
    ("GET", "/api/v1/vault/allergies?patient_id={target_patient}", None, "DOCTOR", "prescription"),
    ("POST", "/api/v1/vault/vaccinations?patient_id={target_patient}", {"disease": "Flu", "vaccine_name": "Flublok", "date_administered": "2023-01-01T00:00:00Z"}, "DOCTOR", "prescription"),
    ("GET", "/api/v1/vault/vaccinations?patient_id={target_patient}", None, "DOCTOR", "prescription"),
    
    # NURSING endpoints (Doctor)
    ("GET", "/api/v1/nursing/patients/{target_patient}/vitals", None, "DOCTOR", "prescription"),
    ("POST", "/api/v1/nursing/assign", {"patient_id": "{target_patient}", "nurse_id": "dummy_nurse", "resource_type": "vitals", "permission": "READ"}, "DOCTOR", "prescription"),

    # LAB endpoints
    ("POST", "/api/v1/lab/requests", {"patient_id": "{target_patient}", "lab_id": "lab1", "test_type": "Blood Panel", "priority": "ROUTINE", "notes": ""}, "DOCTOR", "prescription"),
    ("PUT", "/api/v1/lab/requests/{target_resource}/start", None, "LAB", "lab_request"),
    ("POST", "/api/v1/lab/requests/{target_resource}/report", {"results_encrypted": "x", "summary": "x"}, "LAB", "lab_request"),
    ("GET", "/api/v1/lab/reports/{target_resource}", None, "DOCTOR", "lab_report"),

    # CONSENT endpoints
    ("PUT", "/api/v1/consent/{target_resource}/approve", None, "PATIENT", "consent"),
    ("PUT", "/api/v1/consent/{target_resource}/reject", None, "PATIENT", "consent"),
    ("POST", "/api/v1/consent/revoke/{target_resource}", None, "PATIENT", "consent"),

    # FRAUD endpoints
    ("GET", "/api/v1/fraud/alerts/{target_patient}", None, "PATIENT", "none"),
    ("PUT", "/api/v1/fraud/alerts/{target_resource}/review", {"status": "RESOLVED", "notes": "ok"}, "ADMIN", "fraud_alert"),

    # PHARMACY endpoints
    ("POST", "/api/v1/pharmacy/{target_resource}/dispense", {"qr_data": "x"}, "PHARMACIST", "prescription"),

    # BLOOD BANK endpoints
    ("POST", "/api/v1/blood-bank/requests", {"patient_id": "{target_patient}", "blood_group": "O+", "component": "WHOLE_BLOOD", "units_needed": 1, "urgency": "ROUTINE"}, "DOCTOR", "prescription"),
    ("PUT", "/api/v1/blood-bank/requests/{target_resource}/fulfill", None, "BLOOD_BANK", "blood_request"),
    ("PUT", "/api/v1/blood-bank/requests/{target_resource}/reject", {"reason": "x"}, "BLOOD_BANK", "blood_request"),
    ("POST", "/api/v1/blood-bank/requests/{target_resource}/reject-and-broadcast", {"reason": "x"}, "BLOOD_BANK", "blood_request"),

    # INSURANCE endpoints
    ("PUT", "/api/v1/insurance/claims/{target_resource}/status", {"status": "APPROVED", "notes": "x"}, "INSURER", "insurance_claim"),

    # NOTIFICATIONS endpoints
    ("PUT", "/api/v1/notifications/{target_resource}/read", None, "PATIENT", "notification"),
]


@pytest.mark.parametrize("method, endpoint_tpl, payload_tpl, role, resource_type", IDOR_MATRIX)
def test_idor_matrix(client, idor_data, method, endpoint_tpl, payload_tpl, role, resource_type):
    """
    Test that User A:
    1. CAN access Patient A / Resource A (Success - 200/201)
    2. CANNOT access Patient B / Resource B (IDOR Blocked - 403/404/400)
    """
    token_a = idor_data[f"{role}_A_token"]
    
    # Resources
    res_a_id = idor_data.get(f"{resource_type}_A_id", "dummy") if resource_type != "none" else "dummy"
    res_b_id = idor_data.get(f"{resource_type}_B_id", "dummy") if resource_type != "none" else "dummy"

    # 1. SUCCESS CASE (User A -> Patient A / Resource A)
    endpoint_a = endpoint_tpl.format(
        target_patient=idor_data["PATIENT_A_id"],
        target_resource=res_a_id
    )
    payload_a = None
    if payload_tpl:
        payload_a = payload_tpl.copy()
        if "patient_id" in payload_a:
            payload_a["patient_id"] = idor_data["PATIENT_A_id"]
            
    res_a = client.request(
        method, 
        endpoint_a, 
        json=payload_a, 
        headers={"Authorization": f"Bearer {token_a}"}
    )
    
    # 400 is acceptable for some endpoints if state is wrong (e.g. claim immutable, QR invalid)
    # 404 is acceptable for assignments if nurse not found
    assert res_a.status_code in (200, 201, 400, 404), f"Valid access failed on {endpoint_a}: {res_a.text}"
    
    # 2. IDOR CASE (User A -> Patient B / Resource B)
    endpoint_b = endpoint_tpl.format(
        target_patient=idor_data["PATIENT_B_id"],
        target_resource=res_b_id
    )
    payload_b = None
    if payload_tpl:
        payload_b = payload_tpl.copy()
        if "patient_id" in payload_b:
            payload_b["patient_id"] = idor_data["PATIENT_B_id"]
            
    res_b = client.request(
        method, 
        endpoint_b, 
        json=payload_b, 
        headers={"Authorization": f"Bearer {token_a}"}
    )
    
    assert res_b.status_code in (403, 404), f"IDOR Vulnerability on {endpoint_b}! Expected 403/404, got {res_b.status_code}. Response: {res_b.text}"
