import pytest
from datetime import datetime, timedelta
import unittest.mock
from fastapi.testclient import TestClient
from app.main import app

from app.core.security import create_access_token, hash_password
from app.core.encryption import encrypt
from app.models.user import RoleEnum, User, PatientProfile, DoctorProfile, UserStatusEnum, LabProfile, HospitalAdminProfile, PharmacistProfile, BloodBankProfile, InsurerProfile
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, ResourceTypeEnum, PermissionEnum
from app.models.vault import Prescription, Allergy, Vaccination, LabReport, SeverityEnum
from app.models.lab import LabTestRequest, LabRequestStatusEnum as LabStatusEnum
from app.models.fraud import FraudAlert, FraudAlertStatusEnum as FraudStatusEnum, FraudAlertCategoryEnum
from app.models.blood_bank import BloodRequest, BloodComponentEnum, BloodRequestUrgencyEnum as RequestUrgencyEnum, BloodRequestStatusEnum as BBRequestStatusEnum
from app.models.insurance import InsuranceClaim, ClaimStatusEnum
from app.models.notification import Notification, NotificationTypeEnum

@pytest.fixture(autouse=True)
def mock_verify_sig():
    with unittest.mock.patch("app.core.signing.verify_prescription_signature", return_value=True):
        yield

@pytest.fixture
def full_idor_data(db):
    def create_user(role, email_prefix):
        u = User(email=f"{email_prefix}@c.ai", phone=f"+{email_prefix}", password_hash=hash_password("x"), role=role, full_name=f"{email_prefix} Name", status=UserStatusEnum.ACTIVE)
        db.add(u)
        db.flush()
        return u

    pA = create_user(RoleEnum.PATIENT, "pA")
    pB = create_user(RoleEnum.PATIENT, "pB")
    dA = create_user(RoleEnum.DOCTOR, "dA")
    labA = create_user(RoleEnum.LAB, "labA")
    adminA = create_user(RoleEnum.ADMIN, "adminA")
    pharmA = create_user(RoleEnum.PHARMACIST, "pharmA")
    bbA = create_user(RoleEnum.BLOOD_BANK, "bbA")
    insA = create_user(RoleEnum.INSURER, "insA")

    db.add(PatientProfile(user_id=pA.user_id))
    db.add(PatientProfile(user_id=pB.user_id))
    db.add(DoctorProfile(user_id=dA.user_id, license_number="D-A"))
    db.add(LabProfile(user_id=labA.user_id, license_number="L-A", lab_name="Lab A"))
    db.add(HospitalAdminProfile(user_id=adminA.user_id, hospital_name="Hospital A"))
    db.add(PharmacistProfile(user_id=pharmA.user_id, license_number="P-A"))
    db.add(BloodBankProfile(user_id=bbA.user_id, facility_name="BB A", license_number="BB-A"))
    db.add(InsurerProfile(user_id=insA.user_id, company_name="Ins A", license_number="INS-A"))
    
    db.commit()

    pA_id = db.query(PatientProfile).filter_by(user_id=pA.user_id).first().patient_id
    pB_id = db.query(PatientProfile).filter_by(user_id=pB.user_id).first().patient_id
    dA_id = dA.user_id
    docA_prof = db.query(DoctorProfile).filter_by(user_id=dA.user_id).first().doctor_id
    labA_id = db.query(LabProfile).filter_by(user_id=labA.user_id).first().lab_id
    insA_id = db.query(InsurerProfile).filter_by(user_id=insA.user_id).first().insurer_id
    
    # Give Doctor A access to Patient A
    for rt in [ResourceTypeEnum.PRESCRIPTIONS, ResourceTypeEnum.ALLERGIES, ResourceTypeEnum.VACCINATIONS, ResourceTypeEnum.VITALS, ResourceTypeEnum.LAB_REQUESTS, ResourceTypeEnum.LAB_REPORTS]:
        db.add(ConsentRequest(patient_id=pA_id, grantee_id=dA_id, grantee_type=GranteeTypeEnum.DOCTOR, resource_type=rt, permission=PermissionEnum.BOTH, status=ConsentStatusEnum.ACTIVE, expires_at=datetime.utcnow() + timedelta(days=1)))
    db.commit()

    def make_resources(pid):
        rx = Prescription(patient_id=pid, doctor_id=docA_prof, status="ACTIVE", digital_signature="ed25519:dummy")
        db.add(rx)
        db.flush()
        rx.diagnosis_encrypted = encrypt("dx", f"cryptcare:v2|prescriptions|{rx.prescription_id}|diagnosis_encrypted|{pid}")
        
        lreq = LabTestRequest(patient_id=pid, assigned_lab_id=labA_id, doctor_id=docA_prof, test_name="x", status=LabStatusEnum.PENDING)
        db.add(lreq)
        db.flush()
        
        lrep = LabReport(lab_test_request_id=lreq.request_id, patient_id=pid, uploaded_by=labA_id)
        db.add(lrep)
        db.flush()
        lrep.report_summary_encrypted = encrypt("x", f"cryptcare:v2|lab_reports|{lrep.report_id}|report_summary_encrypted|{pid}")

        cons = ConsentRequest(patient_id=pid, grantee_id=dA_id, grantee_type=GranteeTypeEnum.DOCTOR, resource_type=ResourceTypeEnum.PRESCRIPTIONS, permission=PermissionEnum.READ, status=ConsentStatusEnum.PENDING)
        db.add(cons)
        db.flush()

        fraud = FraudAlert(patient_id=pid, category=FraudAlertCategoryEnum.DOCTOR_SHOPPING, severity=SeverityEnum.MILD, status=FraudStatusEnum.OPEN)
        db.add(fraud)
        db.flush()

        breq = BloodRequest(patient_id=pid, requested_by=dA_id, blood_group="O+", component=BloodComponentEnum.WHOLE_BLOOD, units_needed=1, status=BBRequestStatusEnum.PENDING, urgency=RequestUrgencyEnum.ROUTINE)
        db.add(breq)
        db.flush()

        claim = InsuranceClaim(patient_id=pid, insurer_id=insA_id, resource_type="prescription", resource_id=rx.prescription_id, amount=100.0, status=ClaimStatusEnum.PENDING)
        db.add(claim)
        db.flush()
        
        notif = Notification(recipient_id=pA.user_id if pid == pA_id else pB.user_id, type=NotificationTypeEnum.SYSTEM, message="x")
        db.add(notif)
        db.flush()

        db.commit()
        return {
            "prescription": rx.prescription_id,
            "lab_request": lreq.request_id,
            "lab_report": lrep.report_id,
            "consent": cons.consent_id,
            "fraud_alert": fraud.alert_id,
            "blood_request": breq.request_id,
            "insurance_claim": claim.claim_id,
            "notification": notif.notification_id
        }

    resA = make_resources(pA_id)
    resB = make_resources(pB_id)

    data = {
        "PATIENT_A_id": pA_id, "PATIENT_B_id": pB_id,
        "PATIENT_A_token": create_access_token(pA.user_id, "PATIENT", []),
        "PATIENT_B_token": create_access_token(pB.user_id, "PATIENT", []),
        "DOCTOR_A_token": create_access_token(dA.user_id, "DOCTOR", []),
        "LAB_A_token": create_access_token(labA.user_id, "LAB", []),
        "ADMIN_A_token": create_access_token(adminA.user_id, "ADMIN", []),
        "PHARMACIST_A_token": create_access_token(pharmA.user_id, "PHARMACIST", []),
        "BLOOD_BANK_A_token": create_access_token(bbA.user_id, "BLOOD_BANK", []),
        "INSURER_A_token": create_access_token(insA.user_id, "INSURER", []),
    }
    for k,v in resA.items(): data[f"{k}_A_id"] = v
    for k,v in resB.items(): data[f"{k}_B_id"] = v
    return data

IDOR_MATRIX = [
    # LAB
    ("PUT", "/api/v1/lab/requests/{target_resource}/start", None, "LAB", "lab_request"),
    ("GET", "/api/v1/lab/reports/{target_resource}", None, "DOCTOR", "lab_report"),

    # CONSENT
    ("PUT", "/api/v1/consent/{target_resource}/approve", None, "PATIENT", "consent"),
    ("PUT", "/api/v1/consent/{target_resource}/reject", None, "PATIENT", "consent"),
    ("POST", "/api/v1/consent/revoke/{target_resource}", None, "PATIENT", "consent"),

    # FRAUD
    ("GET", "/api/v1/fraud/alerts/{target_patient}", None, "PATIENT", "none"),
    ("PUT", "/api/v1/fraud/alerts/{target_resource}/review", {"status": "RESOLVED", "notes": "ok"}, "ADMIN", "fraud_alert"),

    # PHARMACY
    ("POST", "/api/v1/pharmacy/{target_resource}/dispense", {"qr_data": "x"}, "PHARMACIST", "prescription"),

    # BLOOD BANK
    ("POST", "/api/v1/blood-bank/requests", {"patient_id": "{target_patient}", "blood_group": "O+", "component": "WHOLE_BLOOD", "units_needed": 1, "urgency": "ROUTINE"}, "DOCTOR", "prescription"),
    ("PUT", "/api/v1/blood-bank/requests/{target_resource}/fulfill", None, "BLOOD_BANK", "blood_request"),
    ("PUT", "/api/v1/blood-bank/requests/{target_resource}/reject", {"reason": "x"}, "BLOOD_BANK", "blood_request"),
    ("POST", "/api/v1/blood-bank/requests/{target_resource}/reject-and-broadcast", {"reason": "x"}, "BLOOD_BANK", "blood_request"),

    # INSURANCE
    ("PUT", "/api/v1/insurance/claims/{target_resource}/status", {"status": "APPROVED", "notes": "x"}, "INSURER", "insurance_claim"),

    # NOTIFICATIONS
    ("PUT", "/api/v1/notifications/{target_resource}/read", None, "PATIENT", "notification"),
]

@pytest.mark.parametrize("method, endpoint_tpl, payload_tpl, role, resource_type", IDOR_MATRIX)
def test_idor_matrix_full(full_idor_data, method, endpoint_tpl, payload_tpl, role, resource_type):
    client = TestClient(app)
    token_a = full_idor_data[f"{role}_A_token"]
    
    res_a_id = full_idor_data.get(f"{resource_type}_A_id", "dummy") if resource_type != "none" else "dummy"
    res_b_id = full_idor_data.get(f"{resource_type}_B_id", "dummy") if resource_type != "none" else "dummy"

    # SUCCESS
    endpoint_a = endpoint_tpl.format(target_patient=full_idor_data["PATIENT_A_id"], target_resource=res_a_id)
    payload_a = payload_tpl.copy() if payload_tpl else None
    if payload_a and "patient_id" in payload_a: payload_a["patient_id"] = full_idor_data["PATIENT_A_id"]
    res_a = client.request(method, endpoint_a, json=payload_a, headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code in (200, 201, 400, 404, 422), f"Valid access failed on {endpoint_a}: {res_a.text}"
    
    # IDOR
    endpoint_b = endpoint_tpl.format(target_patient=full_idor_data["PATIENT_B_id"], target_resource=res_b_id)
    payload_b = payload_tpl.copy() if payload_tpl else None
    if payload_b and "patient_id" in payload_b: payload_b["patient_id"] = full_idor_data["PATIENT_B_id"]
    res_b = client.request(method, endpoint_b, json=payload_b, headers={"Authorization": f"Bearer {token_a}"})
    assert res_b.status_code in (403, 404, 422, 400), f"IDOR Vulnerability on {endpoint_b}! Expected 403/404, got {res_b.status_code}. Response: {res_b.text}"
