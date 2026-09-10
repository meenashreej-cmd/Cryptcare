from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.vault import (
    AllergyCreateRequest,
    AllergyResponse,
    PrescriptionCreateRequest,
    PrescriptionResponse,
    VaccinationCreateRequest,
    VaccinationResponse,
)
from app.services import vault_service

router = APIRouter(prefix="/vault", tags=["Phase 2 — Health Vault"])


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(
    payload: PrescriptionCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    prescription, safety = vault_service.create_prescription(db, current_user, payload)
    return _to_prescription_response(prescription, safety)


@router.get("/prescriptions/{prescription_id}/qr")
def get_prescription_qr(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Returns a PNG QR code — a signed reference to this prescription, not its
    contents. Access-gated identically to reading the prescription itself."""
    png_bytes = vault_service.generate_prescription_qr(db, current_user, prescription_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/prescriptions", response_model=list[PrescriptionResponse])
def list_prescriptions(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = vault_service.get_prescriptions(db, current_user, patient_id)
    return [_to_prescription_response(r) for r in rows]


def _to_prescription_response(p, safety: dict | None = None) -> PrescriptionResponse:
    safety_warnings = None
    if safety and (
        safety["interactions"]["results"] or safety["duplicates"]["duplicates"] or safety["unmatched_drugs"]
    ):
        # "blocking" is always False here — a blocking check raises before
        # this function is ever reached — so it's dropped to avoid implying
        # otherwise in a successful-creation response.
        safety_warnings = {k: v for k, v in safety.items() if k != "blocking"}

    return PrescriptionResponse(
        prescription_id=p.prescription_id,
        patient_id=p.patient_id,
        doctor_id=p.doctor_id,
        diagnosis=p.diagnosis_encrypted,  # already decrypted upstream in the service layer
        notes=p.notes_encrypted,
        status=p.status,
        created_at=p.created_at,
        items=[
            {
                "item_id": i.item_id,
                "medicine_name": i.medicine_name,
                "dosage": i.dosage,
                "frequency": i.frequency,
                "duration_days": i.duration_days,
            }
            for i in p.items
        ],
        safety_warnings=safety_warnings,
    )


@router.post("/allergies", response_model=AllergyResponse, status_code=201)
def add_allergy(
    patient_id: str,
    payload: AllergyCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return vault_service.add_allergy(db, current_user, patient_id, payload)


@router.get("/allergies", response_model=list[AllergyResponse])
def list_allergies(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return vault_service.get_allergies(db, current_user, patient_id)


@router.post("/vaccinations", response_model=VaccinationResponse, status_code=201)
def add_vaccination(
    patient_id: str,
    payload: VaccinationCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return vault_service.add_vaccination(db, current_user, patient_id, payload)


@router.get("/vaccinations", response_model=list[VaccinationResponse])
def list_vaccinations(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return vault_service.get_vaccinations(db, current_user, patient_id)
