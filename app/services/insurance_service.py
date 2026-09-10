from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.rbac import CurrentUser
from app.models.insurance import ClaimStatusEnum, InsuranceClaim
from app.models.notification import Notification, NotificationTypeEnum
from app.models.user import InsurerProfile, PatientProfile, RoleEnum
from app.schemas.insurance import ClaimCreateRequest


def _get_patient_id(db: Session, user_id: str) -> str:
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return profile.patient_id


def _get_insurer_id(db: Session, user_id: str) -> str:
    profile = db.query(InsurerProfile).filter(InsurerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Insurer profile not found.")
    return profile.insurer_id


def create_claim(db: Session, current_user: CurrentUser, payload: ClaimCreateRequest) -> InsuranceClaim:
    # Ensure only PATIENT can call this (already checked at router, but extra safety)
    if current_user.role != RoleEnum.PATIENT.value:
        raise HTTPException(status_code=403, detail="Only patients can create claims.")

    # Derive patient_id directly from the authenticated session
    patient_id = _get_patient_id(db, current_user.id)

    # Verify insurer exists
    insurer = db.query(InsurerProfile).filter(InsurerProfile.insurer_id == payload.insurer_id).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="Insurer not found.")

    claim = InsuranceClaim(
        patient_id=patient_id,
        insurer_id=payload.insurer_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        amount=payload.amount,
        status=ClaimStatusEnum.PENDING,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def list_claims(db: Session, current_user: CurrentUser) -> list[InsuranceClaim]:
    if current_user.role == RoleEnum.PATIENT.value:
        patient_id = _get_patient_id(db, current_user.id)
        return db.query(InsuranceClaim).filter(InsuranceClaim.patient_id == patient_id).order_by(InsuranceClaim.created_at.desc()).all()
    elif current_user.role == RoleEnum.INSURER.value:
        # An insurer should only ever see claims where insurer_id matches their own profile
        insurer_id = _get_insurer_id(db, current_user.id)
        return db.query(InsuranceClaim).filter(InsuranceClaim.insurer_id == insurer_id).order_by(InsuranceClaim.created_at.desc()).all()
    else:
        raise HTTPException(status_code=403, detail="Role not authorized to list claims.")


def update_claim_status(
    db: Session, current_user: CurrentUser, claim_id: str, new_status: ClaimStatusEnum
) -> InsuranceClaim:
    if current_user.role != RoleEnum.INSURER.value:
        raise HTTPException(status_code=403, detail="Only insurers can update claim status.")

    insurer_id = _get_insurer_id(db, current_user.id)
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.claim_id == claim_id).first()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")

    if claim.insurer_id != insurer_id:
        raise HTTPException(status_code=403, detail="Claim does not belong to your insurer profile.")

    # State machine enforcement: Reject transitions out of a terminal state
    if claim.status != ClaimStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot transition from {claim.status} to {new_status}. Claim is immutable after decision.")

    claim.status = new_status
    
    # updated_at is handled by the server on status change via onupdate=func.now() in the model,
    # but we can also set it explicitly if needed. SQLAlchemy will do it automatically.
    
    # Notify the patient
    patient_user_id = db.query(PatientProfile).filter(PatientProfile.patient_id == claim.patient_id).first().user_id
    notification = Notification(
        recipient_id=patient_user_id,
        type=NotificationTypeEnum.INSURANCE_UPDATE,
        resource_type="insurance_claims",
        resource_id=claim.claim_id,
        message=f"Your insurance claim for {claim.resource_type} has been {new_status.value}.",
    )
    db.add(notification)

    db.commit()
    db.refresh(claim)
    return claim
