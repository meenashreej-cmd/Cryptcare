from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfileResponse,
    VerifyOtpRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Phase 1 — Identity"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user, mfa_provisioning_uri, license_verified = auth_service.register_user(db, payload)
    return RegisterResponse(
        user_id=user.user_id,
        status=user.status,
        license_verified=license_verified,
        mfa_provisioning_uri=mfa_provisioning_uri,
    )


@router.post("/verify-otp", response_model=UserProfileResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = auth_service.verify_otp(db, payload.user_id, payload.otp_code)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    access_token, refresh_token = auth_service.login(db, payload.email, payload.password, payload.otp_code)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    access_token = auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=payload.refresh_token)


@router.put("/verify-license/{target_user_id}", response_model=UserProfileResponse)
def verify_license(
    target_user_id: str,
    approve: bool,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    Manual admin override for license verification.

    Phase 1 automatic verification handles the normal path — this endpoint
    is only needed for edge cases (newly issued licenses not yet in the
    registry, disputed accounts, reinstatement after suspension).

    approve=True  → sets profile.verified=True and user.status=ACTIVE.
    approve=False → sets user.status=SUSPENDED.
    """
    return auth_service.admin_verify_license(db, target_user_id, approve)


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.models.user import User
    user = db.query(User).filter(User.user_id == current_user.id).first()
    return user
