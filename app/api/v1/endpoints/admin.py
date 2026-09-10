from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.admin import PendingVerificationResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Hospital Admin"])


@router.get("/pending-verifications", response_model=list[PendingVerificationResponse])
def get_pending_verifications(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    Get a list of users whose accounts are PENDING_VERIFICATION.
    Returns safe metadata only (no encrypted fields) to help admins find users
    that need to be verified via the /auth/verify-license endpoint.
    """
    return admin_service.get_pending_verifications(db, current_user)
