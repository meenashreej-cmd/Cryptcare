from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.admin import PendingVerificationResponse
from app.schemas.auth import UserProfileResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Hospital Admin"])


@router.get("/pending-verifications", response_model=list[PendingVerificationResponse])
def get_pending_verifications(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    List users whose accounts are still in PENDING_VERIFICATION status.

    NOTE — Phase 1 license verification is now automatic:
    When a professional registers, their license_number is matched against
    the in-process LICENSE_REGISTRY dataset. A valid license sets
    profile.verified=True immediately at registration time; no admin action
    is required for those accounts.

    This endpoint (and PUT /auth/verify-license/{user_id}) now serves as a
    **manual override** for edge cases only — for example:
      - A professional whose license was recently issued and is not yet in
        the dataset.
      - Disputed or flagged accounts that need a human review.
      - Accounts suspended by the system that an admin wants to reinstate.

    Returns safe metadata only (no encrypted fields).
    """
    return admin_service.get_pending_verifications(db, current_user)


@router.get("/users", response_model=list[UserProfileResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    List all users in the system - admin only.
    Returns safe metadata only (no encrypted fields).
    """
    return admin_service.get_all_users(db, current_user)
