from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.emergency import EmergencyCardResponse, EmergencyContactUpdateRequest, EmergencyQRStatusResponse
from app.services import emergency_service

router = APIRouter(prefix="/emergency", tags=["Phase 10 — Emergency QR Access"])


# --------------------------------------------------------------------------
# PATIENT — manage their own emergency card + QR
# --------------------------------------------------------------------------

@router.put("/contact", response_model=EmergencyQRStatusResponse)
def update_emergency_contact(
    payload: EmergencyContactUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """Set/update the blood group and emergency contact shown on the emergency card."""
    emergency_service.update_emergency_contact(db, current_user, payload)
    return emergency_service.get_emergency_qr_status(db, current_user)


from app.utils.network import get_client_ip
from app.services.auth_service import _check_action_rate_limit

@router.post("/qr", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def generate_emergency_qr(
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """
    Generates (or regenerates) the patient's emergency QR code as a PNG.
    Regenerating immediately invalidates any QR issued before it — print or
    save the new image, the old one stops working.
    """
    client_ip = get_client_ip(request)
    _check_action_rate_limit(db, current_user.id, "generate_qr", limit=3, window_seconds=86400, is_ip=False)
    _check_action_rate_limit(db, client_ip, "generate_qr", limit=10, window_seconds=60, is_ip=True)
    
    png_bytes = emergency_service.generate_emergency_qr(db, current_user)
    return Response(content=png_bytes, media_type="image/png")


@router.delete("/qr", response_model=EmergencyQRStatusResponse)
def revoke_emergency_qr(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """Deactivates the current emergency QR without issuing a replacement (e.g. a lost card)."""
    emergency_service.revoke_emergency_qr(db, current_user)
    return emergency_service.get_emergency_qr_status(db, current_user)


@router.get("/qr/status", response_model=EmergencyQRStatusResponse)
def emergency_qr_status(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    return emergency_service.get_emergency_qr_status(db, current_user)


# --------------------------------------------------------------------------
# PUBLIC — no authentication. See app/models/emergency.py for why this is
# safe: narrow field set, distinct audit action, mandatory notification,
# unguessable hashed token, tight per-IP rate limit.
# --------------------------------------------------------------------------

@router.get("/access/{token}", response_model=EmergencyCardResponse)
def access_emergency_card(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Scanned by a first responder — no login required. Returns only safety-critical fields."""
    return emergency_service.access_emergency_card(db, token, request)
