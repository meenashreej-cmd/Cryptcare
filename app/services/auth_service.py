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
from typing import Any

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import decrypt as decrypt_field
from app.core.encryption import encrypt as encrypt_field
from app.core.license_verification import verify_license_or_raise
from app.core.security import (
    create_access_token,
    create_preauth_token,
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
    HospitalAdminProfile,
    RoleEnum,
    User,
    UserStatusEnum,
)
from app.models.auth import RefreshToken, UsedJTI, MfaState, ActionRateLimit, IpRateLimit
from app.models.audit import AccessLog, AccessActionEnum
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)



import time

# Production: move to Redis (or a DB table) with TTL support.
_OTP_STORE: dict[str, dict] = {}

def _check_action_rate_limit(db: Session, target_id: str, action: str, limit: int, window_seconds: int, is_ip: bool = False) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(seconds=window_seconds)
    
    model = IpRateLimit if is_ip else ActionRateLimit
    filter_col = model.ip_address if is_ip else model.user_id
    
    record = db.query(model).filter(filter_col == target_id, model.action == action).first()
    
    if not record:
        kwargs = {"action": action, "last_attempt_at": now, "attempt_count": 1, "window_start": now}
        if is_ip:
            kwargs["ip_address"] = target_id
        else:
            kwargs["user_id"] = target_id
        new_record = model(**kwargs)
        db.add(new_record)
        try:
            db.commit()
            return
        except Exception:
            db.rollback()

    # If already exceeded AND window hasn't expired yet, reject
    if record and record.attempt_count >= limit and record.window_start > cutoff:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")

    # Try incrementing if window is valid
    updated = db.query(model).filter(
        filter_col == target_id,
        model.action == action,
        model.window_start > cutoff,
        model.attempt_count < limit
    ).update({
        "attempt_count": model.attempt_count + 1,
        "last_attempt_at": now
    }, synchronize_session=False)

    if updated == 0:
        # Try to reset the window if it's expired.
        reset = db.query(model).filter(
            filter_col == target_id,
            model.action == action,
            model.window_start <= cutoff
        ).update({
            "attempt_count": 1,
            "window_start": now,
            "last_attempt_at": now
        }, synchronize_session=False)
        
        if reset == 0:
            db.commit()
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")
            
    db.commit()

def _record_auth_event(db: Session, user_id: str | None, action: AccessActionEnum, resource_type: str, ip_address: str | None = None):
    db.add(AccessLog(
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        ip_address=ip_address
    ))
    db.commit()



def _verify_totp_monotonic(db: Session, user_id: str, secret: str, otp_code: str) -> None:
    totp = pyotp.TOTP(secret)
    current_step = int(time.time() / 30)
    
    mfa_state = db.query(MfaState).filter(MfaState.user_id == user_id).first()
    if not mfa_state:
        mfa_state = MfaState(user_id=user_id, last_step=-1)
        db.add(mfa_state)
        db.commit()
        db.refresh(mfa_state)
        
    last_step = mfa_state.last_step
    window_start = max(last_step + 1, current_step - settings.MFA_TOTP_VALID_WINDOW)
    window_end = current_step + settings.MFA_TOTP_VALID_WINDOW
    
    matched_step = None
    for step in range(window_start, window_end + 1):
        if hmac.compare_digest(totp.at(step * 30), otp_code):
            matched_step = step
            break
            
    if matched_step is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired MFA code")
        
    updated_rows = db.query(MfaState).filter(
        MfaState.user_id == user_id,
        MfaState.last_step < matched_step
    ).update({"last_step": matched_step}, synchronize_session=False)
    
    if updated_rows == 0:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This MFA code has already been used")
    db.commit()

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


def register_user(db: Session, payload: RegisterRequest, client_ip: str) -> tuple[User, str | None, bool]:
    _check_action_rate_limit(db, client_ip, 'register', limit=3, window_seconds=60, is_ip=True)
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

    if payload.role not in [
        RoleEnum.PATIENT, RoleEnum.DOCTOR, RoleEnum.NURSE, RoleEnum.PHARMACIST, 
        RoleEnum.LAB, RoleEnum.BLOOD_BANK, RoleEnum.INSURER, RoleEnum.HOSPITAL_ADMIN
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role not permitted for self-registration"
        )

    mfa_required = payload.role.value in settings.MFA_REQUIRED_ROLES

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
        mfa_enabled=False,  # Enrolled later via /enroll-mfa
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
            patient_id=user.user_id,
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
    elif payload.role == RoleEnum.HOSPITAL_ADMIN:
        db.add(HospitalAdminProfile(
            user_id=user.user_id,
            hospital_name=payload.hospital_name or payload.organization_name,
            verified=False,
        ))
        license_verified = False
    else:
        raise ValueError(f"Unhandled role during registration: {payload.role}")
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


def verify_otp(db: Session, user_id: str, jti: str, otp_code: str, client_ip: str) -> User:
    _check_action_rate_limit(db, user_id, "verify_otp", limit=5, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "verify_otp", limit=20, window_seconds=60, is_ip=True)
    if db.query(UsedJTI).filter(UsedJTI.jti == jti).first():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token already used")

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

    if user.role == RoleEnum.PATIENT:
        user.status = UserStatusEnum.ACTIVE
    else:
        # For professional roles, check if the mock registry already verified them
        profile = (
            db.query(DoctorProfile).filter(DoctorProfile.user_id == user.user_id).first()
            or db.query(NurseProfile).filter(NurseProfile.user_id == user.user_id).first()
            or db.query(LabProfile).filter(LabProfile.user_id == user.user_id).first()
            or db.query(PharmacistProfile).filter(PharmacistProfile.user_id == user.user_id).first()
            or db.query(InsurerProfile).filter(InsurerProfile.user_id == user.user_id).first()
            or db.query(BloodBankProfile).filter(BloodBankProfile.user_id == user.user_id).first()
            or db.query(HospitalAdminProfile).filter(HospitalAdminProfile.user_id == user.user_id).first()
        )
            
        if profile and getattr(profile, 'verified', False):
            user.status = UserStatusEnum.ACTIVE
        else:
            # Stays PENDING_VERIFICATION (e.g. HOSPITAL_ADMIN)
            pass

    db.add(UsedJTI(jti=jti))
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
        or db.query(HospitalAdminProfile).filter(HospitalAdminProfile.user_id == user.user_id).first()
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


def login(db: Session, email: str, password: str, otp_code: str | None, client_ip: str) -> dict[str, Any]:
    # 1. IP-level rate limit
    _check_action_rate_limit(
        db, client_ip, 'login', 
        limit=settings.RATE_LIMIT_LOGIN_MAX, 
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS, 
        is_ip=True
    )
    user = db.query(User).filter(User.email == email).first()

    # 2. Account-level lockout check before verifying password
    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc).replace(tzinfo=None):
        # We don't want to leak that the account is locked vs wrong password easily, but HTTP 401 is appropriate
        # Actually, let's return identical 401 to prevent enumeration. Wait, no, returning identical 401 doesn't tell the user they are locked out.
        # But wait! To prevent account enumeration, "login returns identical responses for 'no such user' vs 'wrong password'". 
        # A locked account is a valid user, so returning "Account locked" leaks that the user exists. 
        # BUT a real user needs to know they are locked out! Let's return "Invalid email or password" but internally log it. 
        # Actually, if we return 401 "Invalid email or password" for locked accounts, they won't know when they can login. Let's return 401. 
        # Let's run a dummy verify_password just for timing.
        verify_password("dummy", _dummy_password_hash())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    password_ok = verify_password(password, user.password_hash if user else _dummy_password_hash())
    
    if not user or not password_ok:
        if user:
            # Increment failed attempt count and maybe lock out
            try:
                _check_action_rate_limit(db, user.user_id, 'login_failed', limit=5, window_seconds=60, is_ip=False)
            except HTTPException as e:
                if e.status_code == 429:
                    user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
                    _record_auth_event(db, user.user_id, AccessActionEnum.AUTH_SUSPICIOUS, f"auth_lockout:attempts={5}", client_ip)
                    # Return 401 instead of 429 to prevent enumeration
                    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
            _record_auth_event(db, user.user_id, AccessActionEnum.AUTH_FAILED, "auth_login_failed", client_ip)
        else:
            _record_auth_event(db, None, AccessActionEnum.AUTH_FAILED, f"auth_login_failed:email={email}", client_ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.status == UserStatusEnum.PENDING_VERIFICATION:
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        preauth_token = create_preauth_token(user.user_id, user.role.value, permissions, purpose="otp_verification")
        return {"preauth_token": preauth_token, "requires_otp": True}
        
    if user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Account is {user.status.value.lower()}, cannot log in")

    if user.must_change_password:
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return {
            "requires_password_change": True, 
            "user_id": user.user_id, 
            "preauth_token": create_preauth_token(user.user_id, user.role.value, permissions, purpose="password_change")
        }

    requires_mfa = user.role.value in settings.MFA_REQUIRED_ROLES

    if requires_mfa and not user.mfa_enabled:
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        return {
            "requires_mfa_enrollment": True,
            "preauth_token": create_preauth_token(user.user_id, user.role.value, permissions, purpose="mfa_enrollment")
        }

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

        _verify_totp_monotonic(db, user.user_id, decrypt_field(user.mfa_secret), otp_code)

    permissions = ROLE_PERMISSIONS.get(user.role, [])
    access_token = create_access_token(user.user_id, user.role.value, permissions)
    refresh_token = create_refresh_token(user.user_id, user.role.value, permissions)
    
    rt_payload = verify_refresh_token(refresh_token)
    db.add(RefreshToken(
        jti=rt_payload["jti"],
        user_id=user.user_id,
        expires_at=datetime.fromtimestamp(rt_payload["exp"], timezone.utc).replace(tzinfo=None)
    ))
    _record_auth_event(db, user.user_id, AccessActionEnum.AUTH_LOGIN, "auth_login_success", client_ip)

    return {"access_token": access_token, "refresh_token": refresh_token}


def refresh_access_token(db: Session, refresh_token: str, client_ip: str) -> dict[str, str]:
    try:
        payload = verify_refresh_token(refresh_token)
    except TokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    # Additive protection: 10 refreshes per minute ceiling per account
    _check_action_rate_limit(db, payload["sub"], 'refresh', limit=10, window_seconds=60, is_ip=False)

    rt_record = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if not rt_record:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token not found in registry")
        
    if rt_record.revoked:
        # Reuse Detected! Revoke all tokens for this user.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == rt_record.user_id,
            RefreshToken.revoked == False
        ).update({"revoked": True})
        _record_auth_event(db, payload["sub"], AccessActionEnum.AUTH_SUSPICIOUS, "auth_token_reuse_detected", client_ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token reuse detected — session terminated")

    user = db.query(User).filter(User.user_id == payload["sub"]).first()
    if not user or user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer active")

    # Issue new tokens
    permissions = ROLE_PERMISSIONS.get(user.role, [])
    new_access_token = create_access_token(user.user_id, user.role.value, permissions)
    new_refresh_token = create_refresh_token(user.user_id, user.role.value, permissions)
    
    new_rt_payload = verify_refresh_token(new_refresh_token)
    
    # Use compare-and-set atomic update to prevent concurrent refreshes
    updated_rows = db.query(RefreshToken).filter(
        RefreshToken.jti == payload["jti"],
        RefreshToken.revoked == False
    ).update({
        "revoked": True, 
        "replaced_by_jti": new_rt_payload["jti"]
    }, synchronize_session=False)
    
    if updated_rows == 0:
        # Another request already consumed this token concurrently.
        # Treat as reuse and revoke the family.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == rt_record.user_id,
            RefreshToken.revoked == False
        ).update({"revoked": True}, synchronize_session=False)
        _record_auth_event(db, user.user_id, AccessActionEnum.AUTH_SUSPICIOUS, "auth_token_concurrent_reuse_detected", client_ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token reuse detected — session terminated")
    
    
    db.add(RefreshToken(
        jti=new_rt_payload["jti"],
        user_id=user.user_id,
        expires_at=datetime.fromtimestamp(new_rt_payload["exp"], timezone.utc).replace(tzinfo=None)
    ))
    db.commit()

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}

def logout(db: Session, refresh_token: str) -> None:
    try:
        payload = verify_refresh_token(refresh_token)
    except TokenError:
        return  # If token is invalid or expired, nothing to revoke
        
    _check_action_rate_limit(db, payload["sub"], "logout", limit=20, window_seconds=60, is_ip=False)
    
    db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).update({"revoked": True})
    _record_auth_event(db, payload["sub"], AccessActionEnum.AUTH_LOGOUT, "auth_logout")


def logout_all(db: Session, user_id: str) -> None:
    _check_action_rate_limit(db, user_id, "logout", limit=20, window_seconds=60, is_ip=False)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    _record_auth_event(db, user_id, AccessActionEnum.AUTH_LOGOUT, "auth_logout_all")


def change_password(db: Session, user_id: str, jti: str | None, new_password: str, client_ip: str) -> None:
    _check_action_rate_limit(db, user_id, "change_password", limit=5, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "change_password", limit=20, window_seconds=60, is_ip=True)
    
    if jti and db.query(UsedJTI).filter(UsedJTI.jti == jti).first():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token already used")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    if jti:
        db.add(UsedJTI(jti=jti))
    _record_auth_event(db, user_id, AccessActionEnum.AUTH_PASSWORD_CHANGED, "auth_password_changed", client_ip)
    logout_all(db, user_id)


def enroll_mfa(db: Session, user_id: str, jti: str, otp_code: str, client_ip: str) -> dict[str, str]:
    if db.query(UsedJTI).filter(UsedJTI.jti == jti).first():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token already used")

    _check_action_rate_limit(db, user_id, "enroll_mfa", limit=3, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "enroll_mfa", limit=10, window_seconds=60, is_ip=True)

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        
    if user.mfa_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA is already enrolled")
        
    if not user.mfa_secret:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No MFA secret provisioned to enroll")

    _verify_totp_monotonic(db, user.user_id, decrypt_field(user.mfa_secret), otp_code)
    
    user.mfa_enabled = True
    db.add(UsedJTI(jti=jti))
    _record_auth_event(db, user.user_id, AccessActionEnum.AUTH_MFA_ENROLLED, "auth_mfa_enrolled", client_ip)
    
    permissions = ROLE_PERMISSIONS.get(user.role, [])
    access_token = create_access_token(user.user_id, user.role.value, permissions)
    refresh_token = create_refresh_token(user.user_id, user.role.value, permissions)
    
    rt_payload = verify_refresh_token(refresh_token)
    db.add(RefreshToken(
        jti=rt_payload["jti"],
        user_id=user.user_id,
        expires_at=datetime.fromtimestamp(rt_payload["exp"], timezone.utc).replace(tzinfo=None)
    ))
    db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token}


def resend_otp(db: Session, user_id: str, client_ip: str) -> None:
    _check_action_rate_limit(db, user_id, "resend_otp", limit=1, window_seconds=60, is_ip=False)
    _check_action_rate_limit(db, client_ip, "resend_otp", limit=5, window_seconds=60, is_ip=True)
        
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or user.status != UserStatusEnum.PENDING_VERIFICATION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not in pending verification state")
        
    _send_otp(user)

