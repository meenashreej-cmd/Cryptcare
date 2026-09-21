from datetime import date, datetime, timedelta

from app.core.security import create_access_token, hash_password
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, PermissionEnum, ResourceTypeEnum
from app.models.user import BloodBankProfile, DoctorProfile, PatientProfile, RoleEnum, User, UserStatusEnum
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
            resource_type=ResourceTypeEnum.BLOOD_REQUESTS,
            permission=PermissionEnum.BOTH,
            status=ConsentStatusEnum.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
    )
    db.commit()


def _setup(db):
    patient_user = _make_user(db, "bb_patient@cryptcare.ai", "+9200000001", RoleEnum.PATIENT, "BB Patient")
    patient_profile = PatientProfile(user_id=patient_user.user_id, blood_group="A+")
    db.add(patient_profile)
    db.flush()

    doctor_user = _make_user(db, "bb_doctor@cryptcare.ai", "+9200000002", RoleEnum.DOCTOR, "Dr. Transfusion")
    db.add(DoctorProfile(user_id=doctor_user.user_id, license_number="DOC-BB-1"))

    bb_user = _make_user(db, "bb_staff@cryptcare.ai", "+9200000003", RoleEnum.BLOOD_BANK, "City Blood Bank")
    db.add(BloodBankProfile(user_id=bb_user.user_id, license_number="BB-LIC-1", facility_name="City Blood Bank"))
    db.commit()

    _grant_doctor_consent(db, patient_profile.patient_id, doctor_user.user_id)

    return {
        "patient_id": patient_profile.patient_id,
        "patient_headers": get_auth_header(patient_user.user_id, RoleEnum.PATIENT),
        "doctor_headers": get_auth_header(doctor_user.user_id, RoleEnum.DOCTOR),
        "bb_headers": get_auth_header(bb_user.user_id, RoleEnum.BLOOD_BANK),
    }


def _add_unit(client, bb_headers, blood_group, component="PACKED_RBC", days_to_expiry=30):
    payload = {
        "blood_group": blood_group,
        "component": component,
        "collection_date": str(date.today() - timedelta(days=5)),
        "expiry_date": str(date.today() + timedelta(days=days_to_expiry)),
    }
    resp = client.post("/api/v1/blood-bank/units", json=payload, headers=bb_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_full_blood_request_lifecycle_with_exact_match(client, db):
    ctx = _setup(db)

    _add_unit(client, ctx["bb_headers"], "A+")
    _add_unit(client, ctx["bb_headers"], "A+")

    resp = client.get("/api/v1/blood-bank/inventory", headers=ctx["bb_headers"])
    assert resp.status_code == 200
    summary = resp.json()
    assert any(row["blood_group"] == "A+" and row["available_units"] == 2 for row in summary)

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 2, "urgency": "URGENT"},
        headers=ctx["doctor_headers"],
    )
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["request_id"]
    assert resp.json()["status"] == "PENDING"

    resp = client.put(f"/api/v1/blood-bank/requests/{request_id}/fulfill", headers=ctx["bb_headers"])
    assert resp.status_code == 200, resp.text
    fulfilled = resp.json()
    assert fulfilled["status"] == "FULFILLED"
    assert len(fulfilled["matched_unit_ids"]) == 2

    # Inventory now shows 0 available A+ units
    resp = client.get("/api/v1/blood-bank/inventory", headers=ctx["bb_headers"])
    summary = resp.json()
    assert not any(row["blood_group"] == "A+" and row["available_units"] > 0 for row in summary)

    # Patient sees their own resolved request
    resp = client.get(f"/api/v1/blood-bank/requests?patient_id={ctx['patient_id']}", headers=ctx["patient_headers"])
    assert resp.status_code == 200
    assert resp.json()[0]["status"] == "FULFILLED"


def test_compatible_but_not_exact_match_is_used(client, db):
    """O- is the universal RBC donor — an A+ request should be fulfillable from O- stock."""
    ctx = _setup(db)
    _add_unit(client, ctx["bb_headers"], "O-")

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    resp = client.put(f"/api/v1/blood-bank/requests/{request_id}/fulfill", headers=ctx["bb_headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "FULFILLED"


def test_incompatible_stock_is_not_used_and_insufficient_inventory_returns_409(client, db):
    """AB+ stock is NOT compatible for an O- recipient — request must fail with 409, not silently substitute."""
    ctx = _setup(db)
    _add_unit(client, ctx["bb_headers"], "AB+")

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "O-", "component": "PACKED_RBC", "units_needed": 1},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    resp = client.put(f"/api/v1/blood-bank/requests/{request_id}/fulfill", headers=ctx["bb_headers"])
    assert resp.status_code == 409, resp.text

    # request remains PENDING, not silently marked fulfilled with wrong stock
    resp = client.get(f"/api/v1/blood-bank/requests?patient_id={ctx['patient_id']}", headers=ctx["patient_headers"])
    assert resp.json()[0]["status"] == "PENDING"


def test_reject_request_sets_reason_and_notifies(client, db):
    ctx = _setup(db)
    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PLASMA", "units_needed": 1},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    resp = client.put(
        f"/api/v1/blood-bank/requests/{request_id}/reject",
        json={"reason": "No compatible stock available at this time"},
        headers=ctx["bb_headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["rejection_reason"] == "No compatible stock available at this time"


def test_doctor_without_consent_cannot_create_blood_request(client, db):
    ctx = _setup(db)
    stranger_doctor = _make_user(db, "bb_stranger_doc@cryptcare.ai", "+9200000004", RoleEnum.DOCTOR, "Dr. Stranger")
    db.add(DoctorProfile(user_id=stranger_doctor.user_id, license_number="DOC-BB-STRANGER"))
    db.commit()
    stranger_headers = get_auth_header(stranger_doctor.user_id, RoleEnum.DOCTOR)

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=stranger_headers,
    )
    assert resp.status_code == 403


def test_non_blood_bank_role_cannot_add_inventory_or_fulfill(client, db):
    ctx = _setup(db)
    resp = client.post(
        "/api/v1/blood-bank/units",
        json={
            "blood_group": "A+",
            "component": "PACKED_RBC",
            "collection_date": str(date.today()),
            "expiry_date": str(date.today() + timedelta(days=30)),
        },
        headers=ctx["doctor_headers"],
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    resp = client.put(f"/api/v1/blood-bank/requests/{request_id}/fulfill", headers=ctx["doctor_headers"])
    assert resp.status_code == 403


def test_expired_units_excluded_from_matching(client, db):
    ctx = _setup(db)
    # Add a unit that's already past expiry
    _add_unit(client, ctx["bb_headers"], "A+", days_to_expiry=-1)

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    resp = client.put(f"/api/v1/blood-bank/requests/{request_id}/fulfill", headers=ctx["bb_headers"])
    assert resp.status_code == 409, resp.text


def test_patient_cannot_access_other_patient_blood_requests(client, db):
    ctx = _setup(db)
    stranger_patient_user = _make_user(db, "bb_stranger_patient@cryptcare.ai", "+9200000099", RoleEnum.PATIENT, "Stranger Patient")
    stranger_profile = PatientProfile(user_id=stranger_patient_user.user_id, blood_group="B+")
    db.add(stranger_profile)
    db.commit()
    stranger_headers = get_auth_header(stranger_patient_user.user_id, RoleEnum.PATIENT)

    resp = client.get(f"/api/v1/blood-bank/requests?patient_id={ctx['patient_id']}", headers=stranger_headers)
    assert resp.status_code == 403


def test_doctor_no_consent_and_nonexistent_patient_return_identical_403(client, db):
    ctx = _setup(db)
    stranger_doctor = _make_user(db, "bb_doc2@cryptcare.ai", "+9200000010", RoleEnum.DOCTOR, "Dr. No Consent")
    db.add(DoctorProfile(user_id=stranger_doctor.user_id, license_number="DOC-BB-2"))
    db.commit()
    headers = get_auth_header(stranger_doctor.user_id, RoleEnum.DOCTOR)

    # 1. Real patient, but no consent
    resp1 = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=headers,
    )
    
    # 2. Non-existent patient
    resp2 = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": "00000000-0000-0000-0000-000000000000", "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=headers,
    )
    
    assert resp1.status_code == 403
    assert resp2.status_code == 403
    assert resp1.json() == resp2.json()


def test_nurse_cannot_request_blood(client, db):
    ctx = _setup(db)
    nurse_user = _make_user(db, "bb_nurse@cryptcare.ai", "+9200000011", RoleEnum.NURSE, "Nurse Jackie")
    db.commit()
    headers = get_auth_header(nurse_user.user_id, RoleEnum.NURSE)

    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "A+", "component": "PACKED_RBC", "units_needed": 1},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "not permitted" in resp.json()["detail"]


def test_reject_and_broadcast_shortage_no_phi_and_cooldown(client, db):
    ctx = _setup(db)
    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "O-", "component": "WHOLE_BLOOD", "units_needed": 10},
        headers=ctx["doctor_headers"],
    )
    request_id = resp.json()["request_id"]

    # Reject and broadcast URGENT SHORTAGE
    resp = client.post(f"/api/v1/blood-bank/requests/{request_id}/reject-and-broadcast", headers=ctx["bb_headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    # Check notification content for no PHI
    notifs_resp = client.get("/api/v1/notifications", headers=ctx["patient_headers"])
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()["notifications"]
    
    urgent_notif = next((n for n in notifs if n["type"] == "URGENT_BLOOD_SHORTAGE"), None)
    assert urgent_notif is not None
    assert "O- WHOLE_BLOOD" in urgent_notif["message"]
    assert request_id not in urgent_notif["message"]
    assert ctx["patient_id"] not in urgent_notif["message"]
    assert urgent_notif["resource_id"] is None
    assert urgent_notif["resource_type"] is None

    # Test cooldown: another request for same group shouldn't spam URGENT_BLOOD_SHORTAGE
    resp = client.post(
        "/api/v1/blood-bank/requests",
        json={"patient_id": ctx["patient_id"], "blood_group": "O-", "component": "WHOLE_BLOOD", "units_needed": 5},
        headers=ctx["doctor_headers"],
    )
    request_id_2 = resp.json()["request_id"]
    
    resp = client.post(f"/api/v1/blood-bank/requests/{request_id_2}/reject-and-broadcast", headers=ctx["bb_headers"])
    assert resp.status_code == 200
    
    notifs_resp2 = client.get("/api/v1/notifications", headers=ctx["patient_headers"])
    urgent_notifs_count = sum(1 for n in notifs_resp2.json()["notifications"] if n["type"] == "URGENT_BLOOD_SHORTAGE")
    assert urgent_notifs_count == 1  # Cooldown prevented second broadcast


import threading
import pytest

def test_reject_and_broadcast_concurrency(client, db):
    if db.bind.dialect.name == "sqlite":
        pytest.skip("SQLite threading model does not support this concurrency test. Run with MariaDB.")
        
    from app.main import app
    from app.db.session import get_db
    from tests.conftest import TestingSessionLocal
    
    def override_get_db_thread_safe():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db_thread_safe
    
    try:
        ctx = _setup(db)
        
        # VERY IMPORTANT: SQLite handles transactions implicitly, but MariaDB might not see
        # the uncommitted data created by _setup(db) in the threads since the main thread 
        # keeps the transaction open. We must commit here.
        db.commit()

        resp = client.post(
            "/api/v1/blood-bank/requests",
            json={"patient_id": ctx["patient_id"], "blood_group": "B-", "component": "PACKED_RBC", "units_needed": 2},
            headers=ctx["doctor_headers"],
        )
        assert resp.status_code == 201
        request_id = resp.json()["request_id"]

        results = []
        
        def reject_req():
            res = client.post(f"/api/v1/blood-bank/requests/{request_id}/reject-and-broadcast", headers=ctx["bb_headers"])
            results.append(res.status_code)

        threads = [threading.Thread(target=reject_req) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed (200), rest should be 409
        assert results.count(200) == 1
        assert results.count(409) == 4
    finally:
        app.dependency_overrides.clear()
