from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.utils.network import get_client_ip
from app.services.auth_service import _check_action_rate_limit
from app.schemas.consent import (
    BreakGlassRequest,
    CaregiverGrantRequest,
    ConsentApproveRequest,
    ConsentListResponse,
    ConsentRequestCreate,
    ConsentResponse,
    TimelineResponse,
)
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["Phase 4 — Consent Management"])


# --------------------------------------------------------------------------
# DOCTOR / NURSE / LAB — request access, view own requests (cannot grant/revoke)
# --------------------------------------------------------------------------

@router.post("/request", response_model=ConsentResponse, status_code=201)
def request_consent(
    payload: ConsentRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR", "NURSE", "LAB", "INSURER")),
):
    client_ip = get_client_ip(request)
    _check_action_rate_limit(db, current_user.id, "consent_request", limit=20, window_seconds=3600, is_ip=False)
    _check_action_rate_limit(db, client_ip, "consent_request", limit=100, window_seconds=3600, is_ip=True)
    return consent_service.request_consent(db, current_user, payload)


@router.get("/my-requests", response_model=ConsentListResponse)
def list_my_requests(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR", "NURSE", "LAB", "INSURER")),
):
    rows = consent_service.list_my_requests(db, current_user)
    return ConsentListResponse(consents=rows)


# --------------------------------------------------------------------------
# PATIENT — approve, reject, revoke, view own consents
# --------------------------------------------------------------------------

@router.put("/{consent_id}/approve", response_model=ConsentResponse)
def approve_consent(
    consent_id: str,
    payload: ConsentApproveRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    return consent_service.approve_consent(db, current_user, consent_id, payload)


@router.put("/{consent_id}/reject", response_model=ConsentResponse)
def reject_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    return consent_service.reject_consent(db, current_user, consent_id)


@router.post("/revoke/{consent_id}", response_model=ConsentResponse)
def revoke_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    return consent_service.revoke_consent(db, current_user, consent_id)


@router.get("/my-consents", response_model=ConsentListResponse)
def my_consents(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    rows = consent_service.list_active_consents(db, current_user)
    return ConsentListResponse(consents=rows)


@router.get("/history", response_model=ConsentListResponse)
def consent_history(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    rows = consent_service.list_consent_history(db, current_user)
    return ConsentListResponse(consents=rows)


@router.post("/caregiver/grant", response_model=ConsentResponse, status_code=201)
def grant_caregiver_access(
    payload: CaregiverGrantRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """Patient delegates scoped access to a named caregiver/family member —
    immediately active, no approval step (the patient IS the approver).
    Revoke it the same way as any other grant: POST /consent/revoke/{consent_id}."""
    return consent_service.grant_caregiver_access(db, current_user, payload)


@router.get("/timeline", response_model=TimelineResponse)
def activity_timeline(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """Chronological feed of every access/action concerning the patient's own
    records — reads, writes, consent events, break-glass events, caregiver
    grants — drawn from the existing immutable audit log."""
    entries = consent_service.get_patient_timeline(db, current_user)
    return TimelineResponse(entries=entries)


# --------------------------------------------------------------------------
# DOCTOR / LAB — emergency break-glass access
# --------------------------------------------------------------------------

@router.post("/break-glass", response_model=ConsentResponse, status_code=201)
def break_glass_access(
    payload: BreakGlassRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(*settings.BREAK_GLASS_ALLOWED_ROLES)),
):
    """Emergency override — bypasses patient approval entirely. Time-boxed,
    distinctly logged, and always triggers an immediate patient notification.
    See consent_service.break_glass_access for the full rationale."""
    client_ip = get_client_ip(request)
    _check_action_rate_limit(db, current_user.id, "break_glass", limit=3, window_seconds=3600, is_ip=False)
    _check_action_rate_limit(db, client_ip, "break_glass", limit=10, window_seconds=60, is_ip=True)
    return consent_service.break_glass_access(db, current_user, payload)


# --------------------------------------------------------------------------
# ADMIN — read-only, everything
# --------------------------------------------------------------------------

@router.get("/all", response_model=ConsentListResponse)
def all_consents(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    rows = consent_service.list_all_consents(db)
    return ConsentListResponse(consents=rows)
