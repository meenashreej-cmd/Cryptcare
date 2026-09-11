"""
Phase 1 — User Registration & Digital Identity.

Implements: register_user, verify_otp, admin_verify_license, login, refresh_token.
"""

import hmac
import logging
import secrets
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import decrypt as decrypt_field
from app.core.encryption import encrypt as encrypt_field
from app.core.license_verification import verify_license_or_raise
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
    TokenError,
)
from app.models.user import (
    DoctorProfile,
    InsurerProfile,
    BloodBankProfile,
    LabProfile,
    NurseProfile,
    PatientProfile,
    PharmacistProfile,
    RoleEnum,
    User,
    UserStatusEnum,
)
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)



# Production: move to Redis (or a DB table) with TTL support.
_OTP_STORE: dict[str, dict] = {}

# Tracks the last TOTP code accepted per user so the *same* 30s code can't be
# replayed twice (e.g. an attacker who shoulder-surfs/intercepts one valid
# code shouldn't get a second login out of it). 
# PRODUCTION WARNING (Multi-pod limitation): This is currently an in-memory 
# dict. In a horizontally scaled deployment, this MUST be moved to a shared 
# cache (e.g., Redis). Otherwise, an attacker can replay a captured TOTP code 
# against a different pod that hasn't seen the code yet, bypassing this protection.
_LAST_ACCEPTED_TOTP: dict[str, str] = {}

ROLE_PERMISSIONS: dict[RoleEnum, list[str]] = {
    RoleEnum.PATIENT: ["vault:read:own", "vault:write:own", "consent:approve", "sos:trigger"],
    RoleEnum.DOCTOR: ["vault:read:consented", "vault:write:consented", "consent:request", "lab:request"],
    RoleEnum.NURSE: ["vault:read:consented", "vault:write:vitals", "consent:request"],
    RoleEnum.LAB: ["lab:process", "vault:write:lab_reports"],
    RoleEnum.PHARMACIST: ["pharmacy:validate", "pharmacy:dispense"],
    RoleEnum.INSURER: ["consent:request", "fraud:view_own_claims"],
    RoleEnum.BLOOD_BANK: ["blood_bank:manage_inventory", "blood_bank:fulfill_requests"],
    RoleEnum.ADMIN: ["admin:*"],
}


def _generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _generate_mfa_secret() -> str:
    return pyotp.random_base32()


def _build_mfa_provisioning_uri(email: str, secret: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.MFA_ISSUER_NAME)


def register_user(db: Session, payload: RegisterRequest) -> tuple[User, str | None, bool]:
    existing = db.query(User).filter(
        (User.email == payload.email) | (User.phone == payload.phone)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone already exists",
        )

    # ------------------------------------------------------------------ #
    # License check — runs before any DB writes so an invalid license is  #
    # rejected cleanly with HTTP 422. For PATIENT/ADMIN this is a no-op.  #
    # ------------------------------------------------------------------ #
    verify_license_or_raise(payload.role, payload.license_number or "")

    mfa_required = payload.role in (RoleEnum.DOCTOR, RoleEnum.NURSE, RoleEnum.PHARMACIST, RoleEnum.ADMIN)

    # Generated up front (not lazily on first login) so mfa_enabled is never
    # True without a matching secret already in place — see login()'s check.
    # Encrypted at rest via the same AES-256-GCM field encryption as PHI,
    # per the mfa_secret column comment in app/models/user.py.
    raw_mfa_secret = _generate_mfa_secret() if mfa_required else None

    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        status=UserStatusEnum.PENDING_VERIFICATION,
        mfa_enabled=mfa_required,
        mfa_secret=encrypt_field(raw_mfa_secret) if raw_mfa_secret else None,
    )
    db.add(user)
    db.flush()  # get user.user_id before commit

    # Each branch builds the role-specific profile row.
    # Professional profiles are set verified=True immediately because
    # verify_license_or_raise() above already confirmed the license exists
    # in the registry — no separate admin approval step is needed.
    license_verified = False
    if payload.role == RoleEnum.PATIENT:
        db.add(PatientProfile(
            user_id=user.user_id,
            dob=payload.dob,
            gender=payload.gender,
            blood_group=payload.blood_group,
        ))
    elif payload.role == RoleEnum.DOCTOR:
        db.add(DoctorProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            specialization=payload.specialization,
            hospital_name=payload.hospital_name,
            verified=True,
        ))
        license_verified = True
    elif payload.role == RoleEnum.NURSE:
        db.add(NurseProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            hospital_name=payload.hospital_name,
            department=payload.department,
            verified=True,
        ))
        license_verified = True
    elif payload.role == RoleEnum.LAB:
        db.add(LabProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            lab_name=payload.organization_name,
            verified=True,
        ))
        license_verified = True
    elif payload.role == RoleEnum.PHARMACIST:
        db.add(PharmacistProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            pharmacy_name=payload.organization_name,
            verified=True,
        ))
        license_verified = True
    elif payload.role == RoleEnum.INSURER:
        db.add(InsurerProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            company_name=payload.organization_name,
            verified=True,
        ))
        license_verified = True
    elif payload.role == RoleEnum.BLOOD_BANK:
        db.add(BloodBankProfile(
            user_id=user.user_id,
            license_number=payload.license_number,
            facility_name=payload.organization_name,
            verified=True,
        ))
        license_verified = True
    # ADMIN accounts are provisioned out-of-band, not via public self-registration —
    # no profile row is created here and (below) no OTP is sent for this role.

    # OTP is mandatory for every SELF-REGISTERED role. ADMIN is excluded because
    # admin accounts never go through this public endpoint in the first place
    # (see the comment above) — this check is a deliberate second guard, not
    # redundant, in case an ADMIN row is ever created here in the future.
    if payload.role != RoleEnum.ADMIN:
        _send_otp(user)

    db.commit()
    db.refresh(user)

    # Returned exactly once, at registration — same principle as GitHub/AWS
    # showing MFA/recovery secrets only at setup time, never retrievable
    # again afterward. Losing it means re-provisioning (not implemented here;
    # flagged as a follow-up alongside the other Phase 5 hardening notes in
    # the README, same category as real SMS/email OTP delivery).
    mfa_provisioning_uri = (
        _build_mfa_provisioning_uri(user.email, raw_mfa_secret) if raw_mfa_secret else None
    )
    return user, mfa_provisioning_uri, license_verified


def _send_otp(user: User) -> None:
    otp = _generate_otp()
    _OTP_STORE[user.user_id] = {
        "code": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
        "attempts": 0,
    }
    if settings.SMTP_ENABLED:
        _dispatch_otp_email(user.email, user.full_name, otp)
    else:
        # Dev / CI fallback — visible in server logs, never in API responses.
        logger.info("[DEV] OTP for %s (%s): %s", user.email, user.phone, otp)
        print(f"[DEV] OTP for {user.email}: {otp}")


def _dispatch_otp_email(to_email: str, full_name: str, otp: str) -> None:
    """Send a one-time passcode to *to_email* via SMTP (TLS on port 587).

    Failures are logged and swallowed so a transient SMTP outage never blocks
    registration — the caller can re-request a new OTP once the issue clears.
    The OTP is already stored in _OTP_STORE before this is called, so a
    delivery failure doesn't corrupt state.
    """
    from_addr = settings.SMTP_FROM_ADDRESS or settings.SMTP_USERNAME
    expiry_minutes = settings.OTP_EXPIRY_SECONDS // 60

    # Plain-text body (fallback for clients that don't render HTML)
    text_body = (
        f"Hi {full_name},\n\n"
        f"Your CryptCare verification code is: {otp}\n\n"
        f"It expires in {expiry_minutes} minutes. Do not share it with anyone.\n\n"
        f"If you did not request this, you can safely ignore this message.\n\n"
        f"-- The CryptCare Team"
    )

    # HTML body - styled to match the CryptCare brand palette
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#EEF4F7;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#EEF4F7;padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:18px;border:1px solid rgba(15,40,60,0.10);
                    box-shadow:0 10px 30px -15px rgba(0,0,0,0.15);overflow:hidden;">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0FB6AA,#2F6FE0);padding:28px 32px;text-align:center;">
            <span style="font-size:28px;">&#x1F510;</span>
            <h1 style="margin:8px 0 0;color:#ffffff;font-size:20px;font-weight:700;
                       font-family:'Sora',Arial,sans-serif;letter-spacing:-0.3px;">
              CryptCare
            </h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.75);font-size:11px;
                      font-family:'JetBrains Mono',monospace;letter-spacing:0.06em;">
              SOVEREIGN RX NETWORK
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px 36px;">
            <p style="margin:0 0 6px;font-size:15px;color:#0B1E33;">Hi <strong>{full_name}</strong>,</p>
            <p style="margin:0 0 24px;font-size:14px;color:#5B7184;line-height:1.6;">
              Use the code below to verify your CryptCare account.
              It expires in <strong>{expiry_minutes}&nbsp;minutes</strong>.
            </p>
            <!-- OTP code box -->
            <div style="background:#EEF4F7;border:1px solid rgba(15,182,170,0.30);
                        border-radius:14px;padding:22px 0;text-align:center;margin-bottom:24px;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:38px;
                           font-weight:700;letter-spacing:10px;color:#0A8A82;
                           text-shadow:0 2px 8px rgba(15,182,170,0.18);">
                {otp}
              </span>
            </div>
            <p style="margin:0 0 8px;font-size:13px;color:#5B7184;line-height:1.6;">
              <strong>Never share this code</strong> with anyone &mdash; CryptCare staff
              will never ask for it.
            </p>
            <p style="margin:0;font-size:12px;color:#8CA1B0;">
              If you didn't create a CryptCare account, you can safely ignore this email.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#F4F9FB;border-top:1px solid rgba(15,40,60,0.08);
                     padding:16px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#8CA1B0;">
              This is an automated message from CryptCare &mdash; please do not reply.
            </p>
            <p style="margin:4px 0 0;font-size:11px;color:#8CA1B0;">
              All records protected with AES-256-GCM encryption.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your CryptCare verification code: {otp}"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{from_addr}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(from_addr, [to_email], msg.as_string())
        logger.info("OTP email dispatched to %s", to_email)
    except Exception as exc:  # noqa: BLE001
        # Log the failure but don't raise — a failed email must not 500 the
        # registration response. The OTP is in _OTP_STORE; the user can
        # re-request once the delivery issue is resolved.
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)


def verify_otp(db: Session, user_id: str, otp_code: str) -> User:
    record = _OTP_STORE.get(user_id)
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No OTP pending for this user")

    if record["attempts"] >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed OTP attempts")

    if datetime.now(timezone.utc) > record["expires_at"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP expired, please request a new one")

    if not hmac.compare_digest(record["code"], otp_code):
        record["attempts"] += 1
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect OTP")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.status = UserStatusEnum.ACTIVE
    db.commit()
    db.refresh(user)
    del _OTP_STORE[user_id]
    return user


def admin_verify_license(db: Session, target_user_id: str, approve: bool) -> User:
    user = db.query(User).filter(User.user_id == target_user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    profile = (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == user.user_id).first()
        or db.query(NurseProfile).filter(NurseProfile.user_id == user.user_id).first()
        or db.query(LabProfile).filter(LabProfile.user_id == user.user_id).first()
        or db.query(PharmacistProfile).filter(PharmacistProfile.user_id == user.user_id).first()
        or db.query(InsurerProfile).filter(InsurerProfile.user_id == user.user_id).first()
        or db.query(BloodBankProfile).filter(BloodBankProfile.user_id == user.user_id).first()
    )
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User has no professional profile requiring verification")

    if approve:
        profile.verified = True
        user.status = UserStatusEnum.ACTIVE
    else:
        user.status = UserStatusEnum.SUSPENDED

    db.commit()
    db.refresh(user)
    return user


_dummy_password_hash_cache: list[str] = []


def _dummy_password_hash() -> str:
    # Computed lazily (once, then cached) rather than at import time — a
    # bcrypt call as a module-level side effect makes import failures
    # (e.g. bcrypt/passlib version mismatches) harder to trace.
    if not _dummy_password_hash_cache:
        _dummy_password_hash_cache.append(hash_password("dummy-password-for-timing-parity"))
    return _dummy_password_hash_cache[0]


def login(db: Session, email: str, password: str, otp_code: str | None) -> tuple[str, str]:
    user = db.query(User).filter(User.email == email).first()

    # Always run verify_password, even when no user was found, so a
    # nonexistent email doesn't return measurably faster than a wrong
    # password does (bcrypt dominates response time either way).
    password_ok = verify_password(password, user.password_hash if user else _dummy_password_hash())
    if not user or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account is {user.status.value.lower()}, cannot log in")

    if user.mfa_enabled:
        if not otp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
        if not user.mfa_secret:
            # Shouldn't happen — register_user() always provisions a secret
            # alongside mfa_enabled=True — but fail closed and loudly rather
            # than silently skipping the check if data ever gets out of sync.
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "MFA is enabled for this account but no authenticator is enrolled — contact support",
            )

        totp = pyotp.TOTP(decrypt_field(user.mfa_secret))
        if not totp.verify(otp_code, valid_window=settings.MFA_TOTP_VALID_WINDOW):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

        # A valid code is only usable once — reject an immediate replay of
        # the same code even though it's still inside its 30s validity window.
        if _LAST_ACCEPTED_TOTP.get(user.user_id) == otp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This MFA code has already been used")
        _LAST_ACCEPTED_TOTP[user.user_id] = otp_code

    permissions = ROLE_PERMISSIONS.get(user.role, [])
    access_token = create_access_token(user.user_id, user.role.value, permissions)
    refresh_token = create_refresh_token(user.user_id, user.role.value, permissions)
    return access_token, refresh_token


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = verify_refresh_token(refresh_token)
    except TokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    user = db.query(User).filter(User.user_id == payload["sub"]).first()
    if not user or user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer active")

    permissions = ROLE_PERMISSIONS.get(user.role, [])
    return create_access_token(user.user_id, user.role.value, permissions)
