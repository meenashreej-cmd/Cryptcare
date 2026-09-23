
import pytest
from app.core.security import create_access_token
from app.models.user import UserStatusEnum, User, RoleEnum

def test_suspended_user_mid_session(client, db):
    # Create an active user
    user = User(
        email="suspended@cryptcare.ai",
        phone="+1234567899",
        password_hash="dummy",
        role=RoleEnum.PATIENT,
        full_name="Suspended User",
        status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()

    # Generate token
    token = create_access_token(user.user_id, "PATIENT", ["vault:read:own"])
    headers = {"Authorization": f"Bearer {token}"}

    # /auth/me should work
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200

    # Suspend user mid-session
    user.status = UserStatusEnum.SUSPENDED
    db.commit()

    # /auth/me should now fail because get_current_user reloads from DB
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
    assert "not active" in resp.json()["detail"].lower()

