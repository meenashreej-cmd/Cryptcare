
import pytest
from app.core.security import create_preauth_token
from app.models.user import RoleEnum, User, UserStatusEnum
from app.core.security import hash_password

def test_preauth_token_purposes(client, db):
    # Setup test user for change-password
    user = User(
        user_id="test-user-123", email="change@test.com", phone="1234567890", 
        password_hash=hash_password("OldPassword123!"),
        role=RoleEnum.PATIENT, full_name="Test User", status=UserStatusEnum.ACTIVE
    )
    db.add(user)
    db.commit()
    # 1. Create a password_change token
    pw_token = create_preauth_token(
        user_id="test-user-123",
        role=RoleEnum.PATIENT.value,
        permissions=[],
        purpose="password_change"
    )

    # 2. Try to use it on /verify-otp
    resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"otp_code": "123456"},
        headers={"Authorization": f"Bearer {pw_token}"}
    )
    assert resp.status_code == 401
    assert "Wrong preauth purpose" in resp.json()["detail"]

    # 3. Create an otp_verification token
    otp_token = create_preauth_token(
        user_id="test-user-123",
        role=RoleEnum.PATIENT.value,
        permissions=[],
        purpose="otp_verification"
    )

    # 4. Try to use it on /change-password
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"new_password": "NewPassword123"},
        headers={"Authorization": f"Bearer {otp_token}"}
    )
    assert resp.status_code == 401
    assert "Wrong preauth purpose" in resp.json()["detail"]

    # 5. Correct usage on /change-password
    resp2 = client.post(
        "/api/v1/auth/change-password",
        json={"new_password": "NewPassword123"},
        headers={"Authorization": f"Bearer {pw_token}"}
    )
    assert resp2.status_code == 200

    # 6. Second usage should fail (single-use jti enforcement)
    resp3 = client.post(
        "/api/v1/auth/change-password",
        json={"new_password": "NewPassword1234"},
        headers={"Authorization": f"Bearer {pw_token}"}
    )
    assert resp3.status_code == 401
    assert "already used" in resp3.json()["detail"].lower()

