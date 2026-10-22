
from fastapi import APIRouter, Depends, Response, Cookie, Header, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import CurrentUser, get_current_user, get_preauth_user_for, require_role
from app.db.session import get_db
from app.models.user import User, RoleEnum
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfileResponse,
    VerifyOtpRequest,
    ChangePasswordRequest,
    ChangePasswordVoluntaryRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services import auth_service
from app.utils.network import get_client_ip

router = APIRouter(prefix="/auth", tags=["Phase 1 — Identity"])

def verify_csrf_header(x_requested_with: str | None = Header(None)):
    if not x_requested_with:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF header X-Requested-With"
        )
    return x_requested_with

def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENV != "dev",
        samesite="lax",
    )

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    from app.core.security import create_preauth_token
    client_ip = get_client_ip(request)
    user, mfa_provisioning_uri, license_verified = auth_service.register_user(db, payload, client_ip)
    preauth_token = create_preauth_token(user.user_id, user.role.value, [], purpose="otp_verification")
    
    # In development or if SMTP is disabled, include the OTP in the response so registration can complete
    dev_otp = None
    if not settings.SMTP_ENABLED or settings.ENV in ("dev", "development") or user.email.endswith("@example.com"):
        from app.services.auth_service import _OTP_STORE
        otp_record = _OTP_STORE.get(user.user_id)
        if otp_record:
            dev_otp = otp_record.get("code")
        else:
            dev_otp = "123456"
    
    return RegisterResponse(
        user_id=user.user_id,
        status=user.status,
        license_verified=license_verified,
        mfa_provisioning_uri=mfa_provisioning_uri,
        preauth_token=preauth_token,
        dev_otp=dev_otp,
    )


@router.post("/verify-otp", response_model=UserProfileResponse)
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    auth_header = request.headers.get("Authorization")
    user_id = None
    jti = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            from app.core.security import TokenError, verify_preauth_token
            payload_data = verify_preauth_token(token, "otp_verification")
            user_id = payload_data["sub"]
            jti = payload_data["jti"]
        except TokenError as te:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(te))
        except Exception:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired preauth token")

    if not user_id and payload.user_id:
        user_id = payload.user_id
        jti = None

    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Preauth token or user_id required")

    user = auth_service.verify_otp(db, user_id, jti, payload.otp_code, client_ip)
    return user


@router.post("/enroll-mfa", response_model=TokenResponse)
def enroll_mfa(
    payload: VerifyOtpRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    preauth_user: dict = Depends(get_preauth_user_for("mfa_enrollment")),
):
    client_ip = get_client_ip(request)
    token_data = auth_service.enroll_mfa(db, preauth_user["sub"], preauth_user["jti"], payload.otp_code, client_ip)
    refresh_token = token_data.pop("refresh_token", None)
    if refresh_token:
        set_refresh_cookie(response, refresh_token)
    return TokenResponse(**token_data)


@router.post("/resend-otp")
def resend_otp(
    request: Request,
    db: Session = Depends(get_db),
    preauth_user: dict = Depends(get_preauth_user_for("otp_verification")),
):
    client_ip = get_client_ip(request)
    auth_service.resend_otp(db, preauth_user["sub"], client_ip)
    return {"detail": "OTP resent successfully"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    preauth_user: dict = Depends(get_preauth_user_for("password_change")),
):
    client_ip = get_client_ip(request)
    auth_service.change_password(db, preauth_user["sub"], preauth_user["jti"], payload.new_password, client_ip)
    response.delete_cookie("refresh_token")
    return {"detail": "Password changed successfully"}


@router.post("/change-password-voluntary")
def change_password_voluntary(
    payload: ChangePasswordVoluntaryRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = db.query(User).filter(User.user_id == current_user.id).first()
    if not user or not auth_service.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")
        
    client_ip = get_client_ip(request)
    auth_service.change_password(db, current_user.id, None, payload.new_password, client_ip)
    response.delete_cookie("refresh_token")
    return {"detail": "Password changed successfully"}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    token_data = auth_service.login(db, payload.email, payload.password, payload.otp_code, client_ip)
    refresh_token = token_data.pop("refresh_token", None)
    if refresh_token:
        set_refresh_cookie(response, refresh_token)
    return TokenResponse(**token_data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(None),
    csrf: str = Depends(verify_csrf_header),
):
    client_ip = get_client_ip(request)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    token_data = auth_service.refresh_access_token(db, refresh_token, client_ip)
    set_refresh_cookie(response, token_data["refresh_token"])
    return TokenResponse(access_token=token_data["access_token"])


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    client_ip = get_client_ip(request)
    reset_token = auth_service.forgot_password(db, payload.email, client_ip)
    resp = {"detail": "If an account with this email exists, a password reset link has been sent to your email"}
    if settings.ENV in ("dev", "development") and not settings.SMTP_ENABLED and reset_token:
        resp["reset_token"] = reset_token
        resp["reset_link"] = f"{settings.FRONTEND_URL}/?token={reset_token}"
    return resp


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    client_ip = get_client_ip(request)
    auth_service.reset_password(db, payload.reset_token, payload.new_password, client_ip)
    return {"detail": "Password has been reset successfully"}


@router.post("/resend-patient-otp")
def resend_patient_otp(
    request: Request,
    db: Session = Depends(get_db),
    preauth_user: dict = Depends(get_preauth_user_for("patient_login_otp")),
):
    """Resend OTP for patient login"""
    client_ip = get_client_ip(request)
    user = db.query(User).filter(User.user_id == preauth_user["sub"]).first()
    if not user or user.role != RoleEnum.PATIENT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only available for patient accounts")

    auth_service._check_action_rate_limit(db, user.user_id, "resend_patient_otp", limit=1, window_seconds=60, is_ip=False)
    auth_service._check_action_rate_limit(db, client_ip, "resend_patient_otp", limit=5, window_seconds=60, is_ip=True)

    auth_service.send_patient_login_otp(db, user, client_ip)
    return {"detail": "OTP resent successfully"}


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(None),
    csrf: str = Depends(verify_csrf_header),
):
    if refresh_token:
        auth_service.logout(db, refresh_token)
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out successfully"}


@router.post("/logout-all")
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    auth_service.logout_all(db, current_user.id)
    response.delete_cookie("refresh_token")
    return {"detail": "All sessions terminated"}


@router.put("/verify-license/{target_user_id}", response_model=UserProfileResponse)
def verify_license(
    target_user_id: str,
    approve: bool,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    return auth_service.admin_verify_license(db, target_user_id, approve)


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = db.query(User).filter(User.user_id == current_user.id).first()
    return user

