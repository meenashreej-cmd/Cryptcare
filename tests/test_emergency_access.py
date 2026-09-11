from app.core.qr import build_emergency_qr_payload, parse_emergency_qr_payload
from app.core.security import create_access_token, hash_password
from app.models.user import DoctorProfile, PatientProfile, RoleEnum, User, UserStatusEnum
from app.models.vault import SeverityEnum
from app.services.auth_service import ROLE_PERMISSIONS


def get_auth_header(user_id: str, role: RoleEnum):
    permissions = ROLE_PERMISSIONS.get(role, [])
    token = create_access_token(user_id=user_id, role=role.value, permissions=permissions)
    return {"Authorization": f"Bearer {token}"}


def _make_patient(db, email, phone, full_name):
    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password("Password123!"),
        role=RoleEnum.PATIENT,
        full_name=full_name,
        status=UserStatusEnum.ACTIVE,
    )
    db.add(user)
    db.flush()
    profile = PatientProfile(user_id=user.user_id)
    db.add(profile)
    db.commit()
    return user, profile


def test_qr_payload_helpers_roundtrip():
    payload = build_emergency_qr_payload("abc123token")
    assert payload == "cryptcare:emergency:abc123token"
    assert parse_emergency_qr_payload(payload) == "abc123token"


def test_emergency_qr_lifecycle_and_public_scan(client, db):
    patient_user, patient_profile = _make_patient(db, "emerg_patient1@cryptcare.ai", "+9300000001", "Emergency Patient 1")
    patient_headers = get_auth_header(patient_user.user_id, RoleEnum.PATIENT)

    # No token yet
    resp = client.get("/api/v1/emergency/qr/status", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["has_active_token"] is False

    # Set emergency contact + blood group
    resp = client.put(
        "/api/v1/emergency/contact",
        json={"blood_group": "O+", "emergency_contact_name": "Jane Doe", "emergency_contact_phone": "+9199999999"},
        headers=patient_headers,
    )
    assert resp.status_code == 200

    # Add an allergy
    resp = client.post(
        f"/api/v1/vault/allergies?patient_id={patient_profile.patient_id}",
        json={"allergen": "Penicillin", "severity": "SEVERE"},
        headers=patient_headers,
    )
    assert resp.status_code in (200, 201), resp.text

    # Doctor prescribes an active medication
    doctor_user = User(
        email="emerg_doc1@cryptcare.ai",
        phone="+9300000002",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. Emerg",
        status=UserStatusEnum.ACTIVE,
    )
    db.add(doctor_user)
    db.flush()
    db.add(DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-EMERG"))
    db.commit()

    from datetime import datetime, timedelta
    from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, PermissionEnum, ResourceTypeEnum
    db.add(
        ConsentRequest(
            patient_id=patient_profile.patient_id,
            grantee_id=doctor_user.user_id,
            grantee_type=GranteeTypeEnum.DOCTOR,
            resource_type=ResourceTypeEnum.PRESCRIPTIONS,
            permission=PermissionEnum.BOTH,
            status=ConsentStatusEnum.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    db.commit()
    doctor_headers = get_auth_header(doctor_user.user_id, RoleEnum.DOCTOR)
    resp = client.post(
        "/api/v1/vault/prescriptions",
        json={
            "patient_id": patient_profile.patient_id,
            "diagnosis": "Hypertension",
            "notes": "Confidential notes that must NOT appear on the emergency card",
            "items": [{"medicine_name": "Lisinopril 10mg", "dosage": "1 tablet", "frequency": "OD", "duration_days": 90}],
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 201, resp.text

    # Generate the emergency QR — returns a PNG
    resp = client.post("/api/v1/emergency/qr", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0

    resp = client.get("/api/v1/emergency/qr/status", headers=patient_headers)
    assert resp.json()["has_active_token"] is True

    # Simulate scanning: decode the QR to get the raw token (we can't
    # decode a PNG here, so pull the token via the same helper the QR
    # encodes, sourced from a fresh token — verify the DB-hash lookup path
    # by generating the token the same way the service does isn't possible
    # without decoding the PNG, so instead assert via revoke/regenerate
    # behavior and use the public endpoint end-to-end through a full
    # regenerate+scan cycle using the qrcode library's own decode is out of
    # scope; we validate the contract using the internal service directly.
    from app.services import emergency_service
    from unittest.mock import MagicMock

    class DummyRequest:
        client = MagicMock(host="203.0.113.5")

    # Regenerate again to get a token this test can capture in plaintext
    import secrets as _secrets
    original_token_urlsafe = _secrets.token_urlsafe
    captured = {}

    def _capture(*args, **kwargs):
        val = original_token_urlsafe(*args, **kwargs)
        captured["token"] = val
        return val

    _secrets.token_urlsafe = _capture
    try:
        resp = client.post("/api/v1/emergency/qr", headers=patient_headers)
        assert resp.status_code == 200
    finally:
        _secrets.token_urlsafe = original_token_urlsafe

    raw_token = captured["token"]

    # PUBLIC scan — no auth header at all
    resp = client.get(f"/api/v1/emergency/access/{raw_token}")
    assert resp.status_code == 200, resp.text
    card = resp.json()
    assert card["full_name"] == "Emergency Patient 1"
    assert card["blood_group"] == "O+"
    assert card["emergency_contact_name"] == "Jane Doe"
    assert any(a["allergen"] == "Penicillin" for a in card["allergies"])
    assert any(m["medicine_name"] == "Lisinopril 10mg" for m in card["current_medications"])
    # Confidential prescription notes must never appear on the card
    assert "Confidential" not in resp.text
    assert "Hypertension" not in resp.text

    # Patient is notified of the scan
    from app.models.notification import Notification, NotificationTypeEnum
    notifs = db.query(Notification).filter(
        Notification.recipient_id == patient_user.user_id,
        Notification.type == NotificationTypeEnum.EMERGENCY_QR_ACCESS,
    ).all()
    assert len(notifs) == 1

    # Distinct audit action logged
    from app.models.audit import AccessLog, AccessActionEnum
    logs = db.query(AccessLog).filter(
        AccessLog.patient_id == patient_profile.patient_id,
        AccessLog.action == AccessActionEnum.EMERGENCY_QR_ACCESS,
    ).all()
    assert len(logs) == 1

    # Revoke — old token stops working
    resp = client.delete("/api/v1/emergency/qr", headers=patient_headers)
    assert resp.status_code == 200
    assert resp.json()["has_active_token"] is False

    resp = client.get(f"/api/v1/emergency/access/{raw_token}")
    assert resp.status_code == 404


def test_emergency_access_invalid_token_is_denied_and_logged(client, db):
    resp = client.get("/api/v1/emergency/access/not-a-real-token")
    assert resp.status_code == 404

    from app.models.audit import AccessLog, AccessActionEnum
    logs = db.query(AccessLog).filter(
        AccessLog.resource_type == "emergency_qr",
        AccessLog.action == AccessActionEnum.DENIED,
    ).all()
    assert len(logs) >= 1


def test_only_patient_can_manage_own_emergency_qr(client, db):
    doctor_user = User(
        email="emerg_doc2@cryptcare.ai",
        phone="+9300000003",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. NotAPatient",
        status=UserStatusEnum.ACTIVE,
    )
    db.add(doctor_user)
    db.flush()
    db.add(DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-NOPE"))
    db.commit()
    doctor_headers = get_auth_header(doctor_user.user_id, RoleEnum.DOCTOR)

    resp = client.post("/api/v1/emergency/qr", headers=doctor_headers)
    assert resp.status_code == 403


def test_break_glass_expiration_blocks_access(client, db):
    # Test that Break-Glass consent grants expire after their window and subsequent access is blocked.
    patient_user, patient_profile = _make_patient(db, "bg_expire@cryptcare.ai", "+9300000004", "BG Expire Patient")
    
    doctor_user = User(
        email="bg_expire_doc@cryptcare.ai",
        phone="+9300000005",
        password_hash=hash_password("Password123!"),
        role=RoleEnum.DOCTOR,
        full_name="Dr. BG Expire",
        status=UserStatusEnum.ACTIVE,
    )
    db.add(doctor_user)
    db.flush()
    db.add(DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-BGEXPIRE"))
    db.commit()
    
    doctor_headers = get_auth_header(doctor_user.user_id, RoleEnum.DOCTOR)
    
    # 1. Doctor invokes break glass
    resp = client.post(
        "/api/v1/consent/break-glass",
        json={
            "patient_id": patient_profile.patient_id,
            "resource_type": "prescriptions",
            "permission": "READ",
            "reason": "Patient is unresponsive in ER",
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 201
    
    # Verify access works while active
    resp = client.get(f"/api/v1/vault/prescriptions?patient_id={patient_profile.patient_id}", headers=doctor_headers)
    assert resp.status_code == 200
    
    # 2. Fast forward the expiration in DB
    from datetime import datetime, timedelta
    from app.models.consent import ConsentRequest
    
    consent = db.query(ConsentRequest).filter(
        ConsentRequest.patient_id == patient_profile.patient_id,
        ConsentRequest.grantee_id == doctor_user.user_id,
        ConsentRequest.is_break_glass.is_(True)
    ).first()
    
    # Expire it manually
    consent.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    
    # 3. Verify access is now blocked
    resp = client.get(f"/api/v1/vault/prescriptions?patient_id={patient_profile.patient_id}", headers=doctor_headers)
    assert resp.status_code == 403

