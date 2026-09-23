
import pytest
from app.models.user import UserStatusEnum, RoleEnum

def test_admin_pending_verifications_excludes_patients(client, db):
    # Setup admin
    resp = client.post("/api/v1/auth/register", json={
        "email": "admin22@cryptcare.ai",
        "phone": "+1999888999",
        "password": "Password123!",
        "role": "HOSPITAL_ADMIN",
        "full_name": "Admin",
        "hospital_name": "Test Hospital"
    })
    assert resp.status_code == 201

    # Force admin to ACTIVE and role ADMIN in DB
    from app.models.user import User
    admin = db.query(User).filter(User.email == "admin22@cryptcare.ai").first()
    admin.status = UserStatusEnum.ACTIVE
    admin.role = RoleEnum.ADMIN
    db.commit()

    from app.core.security import create_access_token
    admin_token = create_access_token(admin.user_id, RoleEnum.ADMIN.value, [])

    # Register a patient
    resp = client.post("/api/v1/auth/register", json={
        "email": "pending_patient@cryptcare.ai",
        "phone": "+1999888123",
        "password": "Password123!",
        "role": "PATIENT",
        "full_name": "Pending Patient",
        "dob": "1990-01-01"
    })
    assert resp.status_code == 201

    # Check admin pending list
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/v1/admin/pending-verifications", headers=admin_headers)
    assert resp.status_code == 200
    pending_users = resp.json()

    # Patient should not be in the list
    for user in pending_users:
        assert user["role"] != "PATIENT"
        assert user["email"] != "pending_patient@cryptcare.ai"

def test_patient_cannot_access_protected_routes_before_otp(client, db):
    email = "before_otp@cryptcare.ai"
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888124",
        "password": "Password123!",
        "role": "PATIENT",
        "full_name": "Before OTP Patient",
        "dob": "1990-01-01"
    })
    assert resp.status_code == 201

    # Login returns preauth_token, NOT access_token
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("access_token") is None
    assert data.get("preauth_token") is not None
    assert data["requires_otp"] is True

    # Attempt to hit protected route with preauth token
    headers = {"Authorization": f"Bearer {data['preauth_token']}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
    assert "invalid or expired token" in resp.json()["detail"].lower()

def test_otp_verification_promotes_patient_to_active(client, db):
    email = "promote@cryptcare.ai"
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888125",
        "password": "Password123!",
        "role": "PATIENT",
        "full_name": "Promote Patient",
        "dob": "1990-01-01"
    })
    assert resp.status_code == 201
    user_id = resp.json()["user_id"]

    # Login returns preauth_token
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert resp.status_code == 200
    preauth_token = resp.json()["preauth_token"]

    # Fetch real OTP from internal store
    from app.services.auth_service import _OTP_STORE
    otp_code = _OTP_STORE[user_id]["code"]

    # Verify OTP
    headers = {"Authorization": f"Bearer {preauth_token}"}
    resp = client.post("/api/v1/auth/verify-otp", json={"otp_code": otp_code}, headers=headers)
    assert resp.status_code == 200

    # User should now be ACTIVE
    from app.models.user import User
    user = db.query(User).filter(User.email == email).first()
    assert user.status == UserStatusEnum.ACTIVE

    # Login again should now return full access_token
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("access_token") is not None
    assert data.get("preauth_token") is None

