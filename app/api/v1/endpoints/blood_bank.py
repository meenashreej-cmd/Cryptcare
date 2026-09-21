from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.blood_bank import (
    BloodInventorySummaryResponse,
    BloodRequestCreateRequest,
    BloodRequestRejectRequest,
    BloodRequestResponse,
    BloodUnitCreateRequest,
    BloodUnitResponse,
)
from app.services import blood_bank_service

router = APIRouter(prefix="/blood-bank", tags=["Phase 11 — Blood Bank"])


@router.post("/units", response_model=BloodUnitResponse, status_code=201)
def add_unit(
    payload: BloodUnitCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK")),
):
    return blood_bank_service.add_unit(db, current_user, payload)


@router.get("/inventory", response_model=list[BloodInventorySummaryResponse])
def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK", "ADMIN")),
):
    """Grouped counts of AVAILABLE units by blood_group + component — what an inventory dashboard needs."""
    return blood_bank_service.list_inventory_summary(db, current_user)


@router.post("/requests", response_model=BloodRequestResponse, status_code=201)
def create_request(
    payload: BloodRequestCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR", "PATIENT")),
):
    """Requires an ACTIVE consent grant if requested by DOCTOR. Nurses disabled until strict-consent delegation."""
    request = blood_bank_service.create_blood_request(db, current_user, payload)
    return BloodRequestResponse.model_validate(request)


@router.get("/requests", response_model=list[BloodRequestResponse])
def list_requests(
    patient_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK", "DOCTOR", "NURSE", "PATIENT", "ADMIN")),
):
    """BLOOD_BANK/ADMIN see the full queue. DOCTOR/NURSE see requests they created. PATIENT sees their own."""
    rows = blood_bank_service.list_requests(db, current_user, patient_id)
    return [BloodRequestResponse.model_validate(r) for r in rows]


@router.put("/requests/{request_id}/fulfill", response_model=BloodRequestResponse)
def fulfill_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK")),
):
    """Matches compatible AVAILABLE units (FEFO order) against the request. 409 if inventory can't cover it."""
    request, matched_ids = blood_bank_service.fulfill_request(db, current_user, request_id)
    response = BloodRequestResponse.model_validate(request)
    response.matched_unit_ids = matched_ids
    return response


@router.put("/requests/{request_id}/reject", response_model=BloodRequestResponse)
def reject_request(
    request_id: str,
    payload: BloodRequestRejectRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK")),
):
    request = blood_bank_service.reject_request(db, current_user, request_id, payload.reason)
    return BloodRequestResponse.model_validate(request)


@router.post("/requests/{request_id}/reject-and-broadcast", response_model=BloodRequestResponse)
def reject_and_broadcast_shortage(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("BLOOD_BANK")),
):
    """Rejects request and broadcasts a shortage notification, enforcing cooldown."""
    request = blood_bank_service.reject_and_broadcast_shortage(db, current_user, request_id)
    return BloodRequestResponse.model_validate(request)
