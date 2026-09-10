from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.nursing import VitalSignCreateRequest, VitalSignListResponse, VitalSignResponse
from app.services import nursing_service

router = APIRouter(prefix="/nursing", tags=["Phase 6 — Nurse: Vitals"])


@router.post("/vitals", response_model=VitalSignResponse, status_code=201)
def record_vitals(
    payload: VitalSignCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Nurse records a vitals observation for a patient — requires an ACTIVE
    consent grant covering vitals:write for that patient, same as every
    other cross-role vault write in this system. (Role check happens inside
    nursing_service, consistent with vault_service's pattern.)"""
    return nursing_service.record_vitals(db, current_user, payload)


@router.get("/patients/{patient_id}/vitals", response_model=VitalSignListResponse)
def list_vitals(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Read a patient's vitals history. The patient always sees their own;
    anyone else needs an ACTIVE consent grant covering vitals:read — same
    consent-gated choke point as every other vault read, no role allowlist."""
    rows = nursing_service.list_vitals(db, current_user, patient_id)
    return VitalSignListResponse(vitals=rows)
