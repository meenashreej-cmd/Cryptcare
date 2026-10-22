from unittest.mock import MagicMock, patch
import pytest
import smtplib
from app.models.user import RoleEnum, UserStatusEnum, User
from app.services.auth_service import _OTP_STORE
from app.core.config import settings


@pytest.fixture
def mock_smtp():
    with patch("app.services.auth_service._connect_smtp") as mock_connect:
        mock_server = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_server
        yield mock_server, mock_connect


def test_registration_otp_email_success(client, db, mock_smtp, monkeypatch):
    mock_server, _ = mock_smtp
    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    payload = {
        "email": "smtp_success@cryptcare.ai",
        "phone": "+1999888401",
        "password": "Password123!",
        "full_name": "SMTP Success",
        "role": "PATIENT",
        "dob": "1995-05-05"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    user_id = data["user_id"]
    assert data["status"] == "PENDING_VERIFICATION"

    # Verify SMTP was called
    assert mock_server.sendmail.called
    call_args = mock_server.sendmail.call_args[0]
    to_addrs = call_args[1]
    msg_raw = call_args[2]

    assert to_addrs == ["smtp_success@cryptcare.ai"]
    assert "Your CryptCare verification code:" in msg_raw
    assert user_id in _OTP_STORE
    otp_code = _OTP_STORE[user_id]["code"]
    assert otp_code in msg_raw


def test_registration_otp_email_failure_rolls_back(client, db, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    with patch("app.services.auth_service._connect_smtp", side_effect=smtplib.SMTPConnectError(421, b"Connection refused")):
        payload = {
            "email": "smtp_fail@cryptcare.ai",
            "phone": "+1999888402",
            "password": "Password123!",
            "full_name": "SMTP Fail",
            "role": "PATIENT",
            "dob": "1995-05-05"
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert "Unable to send verification email" in detail

        # Verify DB transaction was not committed for this user
        existing = db.query(User).filter(User.email == "smtp_fail@cryptcare.ai").first()
        assert existing is None


def test_patient_login_otp_email_success(client, db, mock_smtp, monkeypatch):
    mock_server, _ = mock_smtp

    # Setup active patient
    email = "active_patient_smtp@cryptcare.ai"
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888403",
        "password": "Password123!",
        "full_name": "Active Patient",
        "role": "PATIENT",
        "dob": "1992-02-02"
    })
    assert reg_resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    user.status = UserStatusEnum.ACTIVE
    db.commit()

    # Enable SMTP and reset mock
    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    mock_server.reset_mock()

    # Patient login step 1 (generates OTP email)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["requires_otp"] is True
    assert login_data.get("preauth_token") is not None

    # Verify sendmail was called for patient login OTP
    assert mock_server.sendmail.called
    call_args = mock_server.sendmail.call_args[0]
    assert call_args[1] == [email]
    assert "Your CryptCare verification code:" in call_args[2]


def test_patient_login_otp_email_failure(client, db, monkeypatch):
    email = "patient_smtp_fail@cryptcare.ai"
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888404",
        "password": "Password123!",
        "full_name": "Active Patient 2",
        "role": "PATIENT",
        "dob": "1992-02-02"
    })
    assert reg_resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    user.status = UserStatusEnum.ACTIVE
    db.commit()

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    with patch("app.services.auth_service._connect_smtp", side_effect=smtplib.SMTPAuthenticationError(535, b"Auth failed")):
        login_resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "Password123!"
        })
        assert login_resp.status_code == 503
        assert "Unable to send verification email" in login_resp.json()["detail"]


def test_patient_resend_otp_success_and_rate_limit(client, db, mock_smtp, monkeypatch):
    mock_server, _ = mock_smtp
    email = "resend_patient_smtp@cryptcare.ai"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888405",
        "password": "Password123!",
        "full_name": "Resend Patient",
        "role": "PATIENT",
        "dob": "1992-02-02"
    })

    user = db.query(User).filter(User.email == email).first()
    user.status = UserStatusEnum.ACTIVE
    db.commit()

    # Login to obtain preauth_token
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    preauth_token = login_resp.json()["preauth_token"]

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    mock_server.reset_mock()

    headers = {"Authorization": f"Bearer {preauth_token}"}
    resend_resp = client.post("/api/v1/auth/resend-patient-otp", headers=headers)
    assert resend_resp.status_code == 200
    assert resend_resp.json()["detail"] == "OTP resent successfully"
    assert mock_server.sendmail.called

    # Rate limiting prevents immediate second resend
    resend_resp2 = client.post("/api/v1/auth/resend-patient-otp", headers=headers)
    assert resend_resp2.status_code == 429


def test_patient_resend_otp_failure(client, db, monkeypatch):
    email = "resend_fail_smtp@cryptcare.ai"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888406",
        "password": "Password123!",
        "full_name": "Resend Fail Patient",
        "role": "PATIENT",
        "dob": "1992-02-02"
    })

    user = db.query(User).filter(User.email == email).first()
    user.status = UserStatusEnum.ACTIVE
    db.commit()

    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    preauth_token = login_resp.json()["preauth_token"]

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    with patch("app.services.auth_service._connect_smtp", side_effect=TimeoutError("SMTP timed out")):
        headers = {"Authorization": f"Bearer {preauth_token}"}
        resend_resp = client.post("/api/v1/auth/resend-patient-otp", headers=headers)
        assert resend_resp.status_code == 503
        assert "Unable to send verification email" in resend_resp.json()["detail"]


def test_registration_resend_otp_failure(client, db, monkeypatch):
    email = "pending_resend_fail@cryptcare.ai"
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "phone": "+1999888407",
        "password": "Password123!",
        "full_name": "Pending Resend Fail",
        "role": "PATIENT",
        "dob": "1992-02-02"
    })
    assert reg_resp.status_code == 201

    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    preauth_token = login_resp.json()["preauth_token"]

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    with patch("app.services.auth_service._connect_smtp", side_effect=smtplib.SMTPException("Relay error")):
        headers = {"Authorization": f"Bearer {preauth_token}"}
        resend_resp = client.post("/api/v1/auth/resend-otp", headers=headers)
        assert resend_resp.status_code == 503
        assert "Unable to send verification email" in resend_resp.json()["detail"]


def test_production_safeguard_when_smtp_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "SMTP_ENABLED", False)

    payload = {
        "email": "prod_disabled@cryptcare.ai",
        "phone": "+1999888408",
        "password": "Password123!",
        "full_name": "Prod Disabled",
        "role": "PATIENT",
        "dob": "1990-01-01"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 503
    assert "Email delivery service is disabled in production" in resp.json()["detail"]


def test_no_credentials_leaked_in_error_detail(client, monkeypatch):
    secret_pass = "SECRET_APP_KEY_VALUE_12345"
    monkeypatch.setattr(settings, "SMTP_PASSWORD", secret_pass)
    monkeypatch.setattr(settings, "SMTP_ENABLED", True)

    with patch("app.services.auth_service._connect_smtp", side_effect=Exception(f"Failed auth for user with pass {secret_pass}")):
        payload = {
            "email": "leak_test@cryptcare.ai",
            "phone": "+1999888409",
            "password": "Password123!",
            "full_name": "Leak Test",
            "role": "PATIENT",
            "dob": "1990-01-01"
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 503
        assert secret_pass not in resp.text
