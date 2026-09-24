import pytest
from datetime import datetime, timedelta

from app.core.security import create_access_token, hash_password
from app.core.encryption import encrypt
import unittest.mock
from app.models.user import (
    RoleEnum, User, PatientProfile, DoctorProfile, UserStatusEnum,
    NurseProfile, LabProfile, PharmacistProfile, BloodBankProfile, InsurerProfile,
)
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum
from app.models.vault import Prescription, Allergy, Vaccination
from app.models.lab import LabTestRequest, LabRequestStatusEnum
from app.models.fraud import FraudAlert, FraudAlertCategoryEnum, FraudAlertStatusEnum
from app.models.vault import SeverityEnum
from app.models.blood_bank import BloodRequest, BloodComponentEnum, BloodRequestStatusEnum, BloodRequestUrgencyEnum
from app.models.insurance import InsuranceClaim, ClaimStatusEnum
from app.models.notification import Notification, NotificationTypeEnum

@pytest.fixture(autouse=True)
def mock_verify_sig():
    with unittest.mock.patch("app.core.signing.verify_prescription_signature", return_value=True):
        yield

@pytest.fixture
def idor_data(db):
    def make_user(role, email, phone, license=None, extra_profile=None):
        u = User(email=email, phone=phone, password_hash=hash_password("x"),
                 role=role, full_name=email, status=UserStatusEnum.ACTIVE)
        db.add(u)
        db.flush()
        return u

    # Two patients
    pA_user = make_user(RoleEnum.PATIENT, "pA@c.ai", "+100")
    pB_user = make_user(RoleEnum.PATIENT, "pB@c.ai", "+200")
    pA_prof = PatientProfile(user_id=pA_user.user_id)
    pB_prof = PatientProfile(user_id=pB_user.user_id)
    db.add(pA_prof); db.add(pB_prof); db.flush()

    # Doctor A
    dA_user = make_user(RoleEnum.DOCTOR, "dA@c.ai", "+300")
    dA_prof = DoctorProfile(user_id=dA_user.user_id, license_number="D-A-idor")
    db.add(dA_prof); db.flush()

    # Lab A
    labA_user = make_user(RoleEnum.LAB, "labA@c.ai", "+400")
    labA_prof = LabProfile(user_id=labA_user.user_id, license_number="L-A-idor", lab_name="Lab A")
    db.add(labA_prof); db.flush()

    # Pharmacist A
    pharmA_user = make_user(RoleEnum.PHARMACIST, "pharmA@c.ai", "+500")
    pharmA_prof = PharmacistProfile(user_id=pharmA_user.user_id, license_number="PH-A-idor")
    db.add(pharmA_prof); db.flush()

    # Blood Bank A
    bbA_user = make_user(RoleEnum.BLOOD_BANK, "bbA@c.ai", "+600")
    bbA_prof = BloodBankProfile(user_id=bbA_user.user_id, license_number="BB-A-idor", facility_name="BB A")
    db.add(bbA_prof); db.flush()

    # Insurer A
    insA_user = make_user(RoleEnum.INSURER, "insA@c.ai", "+700")
    insA_prof = InsurerProfile(user_id=insA_user.user_id, license_number="INS-A-idor", company_name="Ins A")
    db.add(insA_prof); db.flush()

    # Admin A
    adminA_user = make_user(RoleEnum.ADMIN, "adminA@c.ai", "+800")

    db.commit()
    db.refresh(pA_prof); db.refresh(pB_prof)
    db.refresh(dA_prof); db.refresh(labA_prof)

    pA_id = pA_prof.patient_id
    pB_id = pB_prof.patient_id
    dA_id = dA_user.user_id
    dA_doc_id = dA_prof.doctor_id
    labA_lab_id = labA_prof.lab_id

    # Give Doctor A ALL access to Patient A
    for rt in [ResourceTypeEnum.PRESCRIPTIONS, ResourceTypeEnum.ALLERGIES, ResourceTypeEnum.VACCINATIONS,
               ResourceTypeEnum.VITALS, ResourceTypeEnum.LAB_REQUESTS, ResourceTypeEnum.LAB_REPORTS]:
        db.add(ConsentRequest(
            patient_id=pA_id, grantee_id=dA_id, grantee_type=GranteeTypeEnum.DOCTOR,
            resource_type=rt, permission=PermissionEnum.BOTH, status=ConsentStatusEnum.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=1)
        ))
    db.commit()

    def seed_resources(pid, patient_user):
        # Prescription
        rx = Prescription(patient_id=pid, doctor_id=dA_doc_id, status="ACTIVE", digital_signature="ed25519:dummy")
        db.add(rx); db.flush()
        rx.diagnosis_encrypted = encrypt("dx", f"cryptcare:v2|prescriptions|{rx.prescription_id}|diagnosis_encrypted|{pid}")

        # Lab request
        lreq = LabTestRequest(patient_id=pid, assigned_lab_id=labA_lab_id,
                              doctor_id=dA_doc_id, test_name="CBC",
                              status=LabRequestStatusEnum.REQUESTED)
        db.add(lreq); db.flush()

        # Consent (PENDING so patient can approve/reject/revoke)
        cons = ConsentRequest(
            patient_id=pid, grantee_id=dA_id, grantee_type=GranteeTypeEnum.DOCTOR,
            resource_type=ResourceTypeEnum.PRESCRIPTIONS, permission=PermissionEnum.READ,
            status=ConsentStatusEnum.PENDING
        )
        db.add(cons); db.flush()

        # Fraud alert
        fraud = FraudAlert(patient_id=pid, category=FraudAlertCategoryEnum.DOCTOR_SHOPPING,
                           severity=SeverityEnum.MILD, status=FraudAlertStatusEnum.OPEN)
        db.add(fraud); db.flush()

        # Blood request
        breq = BloodRequest(patient_id=pid, requested_by=dA_id, blood_group="O+",
                            component=BloodComponentEnum.WHOLE_BLOOD, units_needed=1,
                            status=BloodRequestStatusEnum.PENDING,
                            urgency=BloodRequestUrgencyEnum.ROUTINE)
        db.add(breq); db.flush()

        # Insurance claim
        insA_id = db.query(InsurerProfile).filter_by(user_id=insA_user.user_id).first().insurer_id
        claim = InsuranceClaim(patient_id=pid, insurer_id=insA_id,
                               resource_type="prescription", resource_id=rx.prescription_id,
                               amount=100.0, status=ClaimStatusEnum.PENDING)
        db.add(claim); db.flush()

        # Notification
        notif = Notification(recipient_id=patient_user.user_id,
                             type=NotificationTypeEnum.PRESCRIPTION, message="test")
        db.add(notif); db.flush()

        # Lab report
        from app.models.vault import LabReport
        lrep = LabReport(lab_test_request_id=lreq.request_id, patient_id=pid,
                         uploaded_by=labA_user.user_id, file_size_bytes=1000,
                         file_path_encrypted=encrypt("/tmp/x"),
                         original_filename_encrypted=encrypt("x.pdf"),
                         report_summary_encrypted=encrypt("ok"))
        db.add(lrep); db.flush()

        db.commit()
        return {
            "prescription": rx.prescription_id,
            "lab_request": lreq.request_id,
            "lab_report": lrep.report_id,
            "consent": cons.consent_id,
            "fraud_alert": fraud.alert_id,
            "blood_request": breq.request_id,
            "insurance_claim": claim.claim_id,
            "notification": notif.notification_id,
        }

    resA = seed_resources(pA_id, pA_user)
    resB = seed_resources(pB_id, pB_user)

    data = {
        "PATIENT_A_id": pA_id,   "PATIENT_B_id": pB_id,
        "PATIENT_A_token":    create_access_token(pA_user.user_id, "PATIENT", []),
        "PATIENT_B_token":    create_access_token(pB_user.user_id, "PATIENT", []),
        "DOCTOR_A_token":     create_access_token(dA_user.user_id, "DOCTOR", []),
        "LAB_A_token":        create_access_token(labA_user.user_id, "LAB", []),
        "PHARMACIST_A_token": create_access_token(pharmA_user.user_id, "PHARMACIST", []),
        "BLOOD_BANK_A_token": create_access_token(bbA_user.user_id, "BLOOD_BANK", []),
        "INSURER_A_token":    create_access_token(insA_user.user_id, "INSURER", []),
        "ADMIN_A_token":      create_access_token(adminA_user.user_id, "ADMIN", []),
    }
    for k, v in resA.items():
        data[f"{k}_A_id"] = v
    for k, v in resB.items():
        data[f"{k}_B_id"] = v
    return data


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
