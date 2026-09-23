from datetime import datetime, timedelta

from app.core.qr import build_prescription_qr_payload
from app.core.security import create_access_token, hash_password
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, PermissionEnum, ResourceTypeEnum
from app.models.fraud import FraudAlertCategoryEnum
from app.models.user import DoctorProfile, InsurerProfile, PatientProfile, PharmacistProfile, RoleEnum, User, UserStatusEnum
from app.models.vault import Prescription
from app.services.auth_service import ROLE_PERMISSIONS


def get_auth_header(user_id: str, role: RoleEnum):
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}


def _make_user(db, email, phone, role, full_name):
    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password("Password123!"),
        role=role,
        full_name=full_name,
        status=UserStatusEnum.ACTIVE,
    )
    db.add(user)
    db.flush()
    return user


def _grant_doctor_consent(db, patient_id, doctor_user_id):
    db.add(
        ConsentRequest(
            patient_id=patient_id,
            grantee_id=doctor_user_id,
            grantee_type=GranteeTypeEnum.DOCTOR,
            resource_type=ResourceTypeEnum.PRESCRIPTIONS,
            permission=PermissionEnum.BOTH,
            status=ConsentStatusEnum.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    db.commit()


def test_doctor_shopping_alert_fires_across_two_doctors(client, db):
    patient_user = _make_user(db, "fraud_patient1@cryptcare.ai", "+9100000001", RoleEnum.PATIENT, "Fraud Patient 1")
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)
    db.flush()

    doctor_a = _make_user(db, "fraud_doc_a@cryptcare.ai", "+9100000002", RoleEnum.DOCTOR, "Dr. A")
    db.add(DoctorProfile(user_id=doctor_a.user_id, license_number="DOC-A"))
    doctor_b = _make_user(db, "fraud_doc_b@cryptcare.ai", "+9100000003", RoleEnum.DOCTOR, "Dr. B")
    db.add(DoctorProfile(user_id=doctor_b.user_id, license_number="DOC-B"))
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor_a.user_id)
    _grant_doctor_consent(db, patient_profile.patient_id, doctor_b.user_id)

    doctor_a_headers = get_auth_header(doctor_a.user_id, RoleEnum.DOCTOR)
    doctor_b_headers = get_auth_header(doctor_b.user_id, RoleEnum.DOCTOR)
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    rx_payload = lambda: {
        "patient_id": patient_profile.patient_id,
        "diagnosis": "Chronic pain",
        "notes": "N/A",
        "items": [{"medicine_name": "Tramadol 50mg", "dosage": "1 tablet", "frequency": "BID", "duration_days": 14}],
    }

    resp = client.post("/api/v1/vault/prescriptions", json=rx_payload(), headers=doctor_a_headers)
    assert resp.status_code == 201, resp.text

    # No alert yet — only one doctor so far
    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["alerts"] == []

    resp = client.post("/api/v1/vault/prescriptions", json=rx_payload(), headers=doctor_b_headers)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["category"] == FraudAlertCategoryEnum.DOCTOR_SHOPPING.value
    assert alerts[0]["status"] == "OPEN"
    assert "tramadol" in alerts[0]["encrypted_context"].lower() or "Tramadol" in alerts[0]["encrypted_context"]


def test_prescription_tampering_alert_after_two_failed_scans(client, db):
    patient_user = _make_user(db, "fraud_patient2@cryptcare.ai", "+9100000004", RoleEnum.PATIENT, "Fraud Patient 2")
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)
    db.flush()

    doctor = _make_user(db, "fraud_doc2@cryptcare.ai", "+9100000005", RoleEnum.DOCTOR, "Dr. Tamper")
    db.add(DoctorProfile(user_id=doctor.user_id, license_number="DOC-TAMPER"))
    pharmacist = _make_user(db, "fraud_pharm2@cryptcare.ai", "+9100000006", RoleEnum.PHARMACIST, "Ph. Tamper")
    db.add(PharmacistProfile(user_id=pharmacist.user_id, license_number="PHARM-TAMPER"))
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor.user_id)

    doctor_headers = get_auth_header(doctor.user_id, RoleEnum.DOCTOR)
    pharmacist_headers = get_auth_header(pharmacist.user_id, RoleEnum.PHARMACIST)
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    resp = client.post(
        "/api/v1/vault/prescriptions",
        json={
            "patient_id": patient_profile.patient_id,
            "diagnosis": "Sinus infection",
            "notes": "N/A",
            "items": [{"medicine_name": "Augmentin 500mg", "dosage": "1 tablet", "frequency": "BID", "duration_days": 7}],
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 201
    prescription_id = resp.json()["prescription_id"]

    tampered = build_prescription_qr_payload(prescription_id, "not_the_real_signature")

    for _ in range(2):
        resp = client.post("/api/v1/pharmacy/verify-qr", json={"qr_payload": tampered}, headers=pharmacist_headers)
        assert resp.status_code == 403

    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    tampering_alerts = [a for a in alerts if a["category"] == FraudAlertCategoryEnum.PRESCRIPTION_TAMPERING.value]
    assert len(tampering_alerts) == 1
    assert tampering_alerts[0]["severity"] == "SEVERE"
    assert prescription_id in tampering_alerts[0]["related_resource_ids"]


def test_break_glass_abuse_flagged_across_three_patients(client, db):
    doctor = _make_user(db, "fraud_doc3@cryptcare.ai", "+9100000007", RoleEnum.DOCTOR, "Dr. Breakglass")
    db.add(DoctorProfile(user_id=doctor.user_id, license_number="DOC-BREAKGLASS"))
    db.commit()
    doctor_headers = get_auth_header(doctor.user_id, RoleEnum.DOCTOR)

    patient_ids = []
    patient_headers_list = []
    for i in range(3):
        patient_user = _make_user(db, f"fraud_bg_patient{i}@cryptcare.ai", f"+920000000{i}", RoleEnum.PATIENT, f"BG Patient {i}")
        patient_profile = PatientProfile(user_id=patient_user.user_id)
        db.add(patient_profile)
        db.commit()
        patient_ids.append(patient_profile.patient_id)
        patient_headers_list.append(get_auth_header(patient_user.user_id, RoleEnum.PATIENT))

    for pid in patient_ids:
        resp = client.post(
            "/api/v1/consent/break-glass",
            json={
                "patient_id": pid,
                "resource_type": "prescriptions",
                "permission": "READ",
                "reason": "Unresponsive patient in the ER, need history immediately",
            },
            headers=doctor_headers,
        )
        assert resp.status_code == 201, resp.text

    # Every one of the 3 patients should see a BREAK_GLASS_ABUSE alert
    for pid, headers in zip(patient_ids, patient_headers_list):
        resp = client.get(f"/api/v1/fraud/alerts/{pid}", headers=headers)
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        abuse_alerts = [a for a in alerts if a["category"] == FraudAlertCategoryEnum.BREAK_GLASS_ABUSE.value]
        assert len(abuse_alerts) == 1
        assert abuse_alerts[0]["severity"] == "SEVERE"


def test_admin_can_view_and_review_alerts(client, db):
    patient_user = _make_user(db, "fraud_patient4@cryptcare.ai", "+9100000010", RoleEnum.PATIENT, "Fraud Patient 4")
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)
    db.flush()

    doctor_a = _make_user(db, "fraud_doc4a@cryptcare.ai", "+9100000011", RoleEnum.DOCTOR, "Dr. 4A")
    db.add(DoctorProfile(user_id=doctor_a.user_id, license_number="DOC-4A"))
    doctor_b = _make_user(db, "fraud_doc4b@cryptcare.ai", "+9100000012", RoleEnum.DOCTOR, "Dr. 4B")
    db.add(DoctorProfile(user_id=doctor_b.user_id, license_number="DOC-4B"))
    admin_user = _make_user(db, "fraud_admin4@cryptcare.ai", "+9100000013", RoleEnum.ADMIN, "Admin 4")
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor_a.user_id)
    _grant_doctor_consent(db, patient_profile.patient_id, doctor_b.user_id)

    doctor_a_headers = get_auth_header(doctor_a.user_id, RoleEnum.DOCTOR)
    doctor_b_headers = get_auth_header(doctor_b.user_id, RoleEnum.DOCTOR)
    admin_headers = get_auth_header(admin_user.user_id, RoleEnum.ADMIN)
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    rx_payload = lambda: {
        "patient_id": patient_profile.patient_id,
        "diagnosis": "Anxiety",
        "notes": "N/A",
        "items": [{"medicine_name": "Sertraline 50mg", "dosage": "1 tablet", "frequency": "OD", "duration_days": 30}],
    }
    client.post("/api/v1/vault/prescriptions", json=rx_payload(), headers=doctor_a_headers)
    client.post("/api/v1/vault/prescriptions", json=rx_payload(), headers=doctor_b_headers)

    # Admin cannot view patient-specific alerts endpoint (restricted to PATIENT)
    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=admin_headers)
    assert resp.status_code == 403

    # Admin uses the global queue instead
    resp = client.get(f"/api/v1/fraud/alerts", headers=admin_headers)
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert len(alerts) >= 1
    alert_id = alerts[0]["alert_id"]
    assert alerts[0]["status"] == "OPEN"
    # Admin gets sanitized view
    assert "encrypted_context" not in alerts[0]
    assert "patient_id" not in alerts[0]

    # Admin reviews (dismisses) the alert
    resp = client.put(f"/api/v1/fraud/alerts/{alert_id}/review", json={"status": "DISMISSED"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "DISMISSED"
    assert resp.json()["reviewed_by"] == admin_user.user_id

    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["status"] == "DISMISSED"


def test_doctor_shopping_boundary_one_doctor_multiple_prescriptions(client, db):
    patient_user = _make_user(db, "fraud_patient5@cryptcare.ai", "+9100000015", RoleEnum.PATIENT, "Fraud Patient 5")
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)
    db.flush()

    doctor_a = _make_user(db, "fraud_doc5a@cryptcare.ai", "+9100000016", RoleEnum.DOCTOR, "Dr. 5A")
    db.add(DoctorProfile(user_id=doctor_a.user_id, license_number="DOC-5A"))
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor_a.user_id)
    doctor_a_headers = get_auth_header(doctor_a.user_id, RoleEnum.DOCTOR)
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    rx_payload = {
        "patient_id": patient_profile.patient_id,
        "diagnosis": "Chronic pain",
        "notes": "N/A",
        "items": [{"medicine_name": "Tramadol 50mg", "dosage": "1 tablet", "frequency": "BID", "duration_days": 14}],
    }

    # Two prescriptions for the same medicine, but from the SAME doctor (below threshold)
    client.post("/api/v1/vault/prescriptions", json=rx_payload, headers=doctor_a_headers)
    client.post("/api/v1/vault/prescriptions", json=rx_payload, headers=doctor_a_headers)

    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["alerts"] == []


def test_prescription_tampering_boundary_one_attempt(client, db):
    patient_user = _make_user(db, "fraud_patient6@cryptcare.ai", "+9100000017", RoleEnum.PATIENT, "Fraud Patient 6")
    patient_profile = PatientProfile(user_id=patient_user.user_id)
    db.add(patient_profile)
    db.flush()

    doctor = _make_user(db, "fraud_doc6@cryptcare.ai", "+9100000018", RoleEnum.DOCTOR, "Dr. 6")
    db.add(DoctorProfile(user_id=doctor.user_id, license_number="DOC-6"))
    pharmacist = _make_user(db, "fraud_pharm6@cryptcare.ai", "+9100000019", RoleEnum.PHARMACIST, "Ph. 6")
    db.add(PharmacistProfile(user_id=pharmacist.user_id, license_number="PHARM-6"))
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor.user_id)

    doctor_headers = get_auth_header(doctor.user_id, RoleEnum.DOCTOR)
    pharmacist_headers = get_auth_header(pharmacist.user_id, RoleEnum.PHARMACIST)
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    resp = client.post(
        "/api/v1/vault/prescriptions",
        json={
            "patient_id": patient_profile.patient_id,
            "diagnosis": "Sinus infection",
            "notes": "N/A",
            "items": [{"medicine_name": "Augmentin 500mg", "dosage": "1 tablet", "frequency": "BID", "duration_days": 7}],
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 201
    prescription_id = resp.json()["prescription_id"]

    tampered = build_prescription_qr_payload(prescription_id, "not_the_real_signature")

    # Only 1 failed scan (below threshold)
    resp = client.post("/api/v1/pharmacy/verify-qr", json={"qr_payload": tampered}, headers=pharmacist_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/v1/fraud/alerts/{patient_profile.patient_id}", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["alerts"] == []


def test_break_glass_abuse_boundary_two_patients(client, db):
    doctor = _make_user(db, "fraud_doc7@cryptcare.ai", "+9100000020", RoleEnum.DOCTOR, "Dr. 7")
    db.add(DoctorProfile(user_id=doctor.user_id, license_number="DOC-7"))
    db.commit()
    doctor_headers = get_auth_header(doctor.user_id, RoleEnum.DOCTOR)

    patient_ids = []
    patient_headers_list = []
    # Only 2 patients (below threshold)
    for i in range(2):
        patient_user = _make_user(db, f"fraud_bg_patient_b{i}@cryptcare.ai", f"+920000001{i}", RoleEnum.PATIENT, f"BG Patient B{i}")
        patient_profile = PatientProfile(user_id=patient_user.user_id)
        db.add(patient_profile)
        db.commit()
        patient_ids.append(patient_profile.patient_id)
        patient_headers_list.append(get_auth_header(patient_user.user_id, RoleEnum.PATIENT))

    for pid in patient_ids:
        resp = client.post(
            "/api/v1/consent/break-glass",
            json={
                "patient_id": pid,
                "resource_type": "prescriptions",
                "permission": "READ",
                "reason": "Emergency situation",
            },
            headers=doctor_headers,
        )
        assert resp.status_code == 201

    # Neither patient should have an alert
    for pid, headers in zip(patient_ids, patient_headers_list):
        resp = client.get(f"/api/v1/fraud/alerts/{pid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["alerts"] == []

