from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user, require_role
from app.db.session import get_db
from app.models.user import RoleEnum
from app.schemas.pharmacy import DispenseRequest, DispenseResponse, QRVerifyRequest, QRVerifyResponse
from app.services.pharmacy_service import dispense_prescription, verify_prescription_qr

router = APIRouter()


@router.post("/verify-qr", response_model=QRVerifyResponse)
def verify_qr(
    payload: QRVerifyRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(RoleEnum.PHARMACIST.value)),
):
    """
    Verify a patient's prescription QR code payload and return the decrypted details.
    Restricted to PHARMACIST role. The signature must verify — an invalid/tampered
    QR is rejected outright rather than returned with a warning (see pharmacy_service).
    """
    return verify_prescription_qr(db, current_user, payload)


@router.post("/{prescription_id}/dispense", response_model=DispenseResponse)
def dispense(
    prescription_id: str,
    payload: DispenseRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(RoleEnum.PHARMACIST.value)),
):
    """
    Mark a prescription as DISPENSED to prevent duplicate dispenses.
    Restricted to PHARMACIST role. Requires the same QR payload scanned in
    verify-qr so the signature can be independently re-checked immediately
    before dispensing (status alone is no longer sufficient).
    """
    return dispense_prescription(db, current_user, prescription_id, payload.qr_payload)
