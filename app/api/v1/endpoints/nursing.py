"""
Phase 6 — Nurse: Vitals & Care Team.

Route-level role guards (Phase 2 Step 4 — deny-by-default):
  - POST /vitals                      → NURSE, PATIENT
  - GET  /patients/{id}/vitals        → DOCTOR, NURSE, PATIENT
  - POST /assign                      → DOCTOR
  - POST /assignments/{id}/remove     → DOCTOR
  - GET  /assignments                 → DOCTOR
  - GET  /my-patients                 → NURSE
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.nursing import (
    VitalSignCreateRequest,
    VitalSignListResponse,
    VitalSignResponse,
    NurseAssignmentRequest,
    NurseAssignmentResponse,
)
from app.services import nursing_service

router = APIRouter(prefix="/nursing", tags=["Phase 6 — Nurse: Vitals"])


@router.post("/vitals", response_model=VitalSignResponse, status_code=201)
def record_vitals(
    payload: VitalSignCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("NURSE", "PATIENT")),
):
    """Nurse (or patient themselves) records a vitals observation.
    Requires an ACTIVE consent grant covering vitals:write — enforced in service."""
    return nursing_service.record_vitals(db, current_user, payload)


@router.get("/patients/{patient_id}/vitals", response_model=VitalSignListResponse)
def list_vitals(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR", "NURSE", "PATIENT")),
):
    """Read a patient's vitals history — consent-gated in service layer."""
    rows = nursing_service.list_vitals(db, current_user, patient_id)
    return VitalSignListResponse(vitals=rows)


@router.post("/assign", response_model=NurseAssignmentResponse, status_code=201)
def assign_nurse(
    payload: NurseAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR")),
):
    """Supervising doctor assigns a nurse to a patient's care team."""
    return nursing_service.assign_nurse(db, current_user, payload)


@router.post("/assignments/{assignment_id}/remove", response_model=NurseAssignmentResponse)
def remove_nurse(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR")),
):
    """Supervising doctor removes a nurse from a patient's care team."""
    return nursing_service.remove_nurse(db, current_user, assignment_id)


@router.get("/assignments", response_model=list[NurseAssignmentResponse])
def get_assignments(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("DOCTOR")),
):
    """Doctor retrieves their active care team assignments."""
    return nursing_service.get_assignments(db, current_user)


@router.get("/my-patients")
def get_nurse_patients(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("NURSE")),
):
    """Nurse retrieves their active assigned patients."""
    return nursing_service.get_nurse_patients(db, current_user)
