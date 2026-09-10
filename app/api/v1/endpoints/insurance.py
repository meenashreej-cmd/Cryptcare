from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.insurance import ClaimCreateRequest, ClaimResponse, ClaimStatusUpdateRequest
from app.services import insurance_service

router = APIRouter(prefix="/insurance", tags=["Phase 12 — Insurance Provider Claims"])


@router.post("/claims", response_model=ClaimResponse, status_code=201)
def create_claim(
    payload: ClaimCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """
    Submit a new insurance claim.
    Restricted to PATIENT. The patient_id is derived from the authenticated session,
    ensuring a patient cannot file a claim under another patient's ID.
    """
    claim = insurance_service.create_claim(db, current_user, payload)
    return claim


@router.get("/claims", response_model=list[ClaimResponse])
def list_claims(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT", "INSURER")),
):
    """
    List claims. 
    PATIENTs see their own claims.
    INSURERs see only claims submitted to their specific insurer profile.
    Returns metadata only, no PHI.
    """
    return insurance_service.list_claims(db, current_user)


@router.put("/claims/{claim_id}/status", response_model=ClaimResponse)
def update_claim_status(
    claim_id: str,
    payload: ClaimStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("INSURER")),
):
    """
    Update the status of a claim (APPROVED or REJECTED).
    Transitions out of a terminal state are rejected.
    Generates a NotificationTypeEnum.INSURANCE_UPDATE for the patient.
    """
    return insurance_service.update_claim_status(db, current_user, claim_id, payload.status)
