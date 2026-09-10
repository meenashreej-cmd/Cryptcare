"""
Phase 10 — Emergency QR Access service. See app/models/emergency.py for the
full design rationale and compensating controls.
"""

import hashlib
import secrets

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.qr import build_emergency_qr_payload, generate_qr_png
from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.emergency import EmergencyAccessToken
from app.models.notification import NotificationTypeEnum
from app.models.user import PatientProfile
from app.models.vault import Allergy, Prescription, PrescriptionItem, PrescriptionStatusEnum
from app.schemas.emergency import (
    EmergencyAllergyItem,
    EmergencyCardResponse,
    EmergencyContactUpdateRequest,
    EmergencyMedicationItem,
    EmergencyQRStatusResponse,
)
from app.services import notification_service


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _resolve_patient_profile(db: Session, current_user: CurrentUser) -> PatientProfile:
    if current_user.role != "PATIENT":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only patients can manage their own emergency QR.")
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found.")
    return profile


def update_emergency_contact(db: Session, current_user: CurrentUser, payload: EmergencyContactUpdateRequest) -> PatientProfile:
    profile = _resolve_patient_profile(db, current_user)
    if payload.blood_group is not None:
        profile.blood_group = payload.blood_group
    if payload.emergency_contact_name is not None:
        profile.emergency_contact_name = payload.emergency_contact_name
    if payload.emergency_contact_phone is not None:
        profile.emergency_contact_phone = payload.emergency_contact_phone
    db.commit()
    db.refresh(profile)
    return profile


def _revoke_active_tokens(db: Session, patient_id: str) -> None:
    from datetime import datetime

    active = (
        db.query(EmergencyAccessToken)
        .filter(EmergencyAccessToken.patient_id == patient_id, EmergencyAccessToken.is_active.is_(True))
        .all()
    )
    for row in active:
        row.is_active = False
        row.revoked_at = datetime.utcnow()


def generate_emergency_qr(db: Session, current_user: CurrentUser) -> bytes:
    """
    Regenerating immediately invalidates any previously issued QR — one
    live token per patient at a time, same pattern a lost physical ID card
    follows: get a replacement, the old one stops working.
    """
    profile = _resolve_patient_profile(db, current_user)

    _revoke_active_tokens(db, profile.patient_id)

    raw_token = secrets.token_urlsafe(32)  # `secrets`, never `random` — see Phase 1 OTP lesson
    token_row = EmergencyAccessToken(patient_id=profile.patient_id, token_hash=_hash_token(raw_token))
    db.add(token_row)

    db.add(
        AccessLog(
            user_id=current_user.id,
            patient_id=profile.patient_id,
            resource_type="emergency_qr",
            resource_id=token_row.token_id,
            action=AccessActionEnum.WRITE,
        )
    )
    db.commit()

    payload = build_emergency_qr_payload(raw_token)
    return generate_qr_png(payload)


def revoke_emergency_qr(db: Session, current_user: CurrentUser) -> None:
    profile = _resolve_patient_profile(db, current_user)
    _revoke_active_tokens(db, profile.patient_id)
    db.add(
        AccessLog(
            user_id=current_user.id,
            patient_id=profile.patient_id,
            resource_type="emergency_qr",
            resource_id=None,
            action=AccessActionEnum.CONSENT_REVOKED,
        )
    )
    db.commit()


def get_emergency_qr_status(db: Session, current_user: CurrentUser) -> EmergencyQRStatusResponse:
    profile = _resolve_patient_profile(db, current_user)
    row = (
        db.query(EmergencyAccessToken)
        .filter(EmergencyAccessToken.patient_id == profile.patient_id, EmergencyAccessToken.is_active.is_(True))
        .first()
    )
    if not row:
        return EmergencyQRStatusResponse(has_active_token=False)
    return EmergencyQRStatusResponse(has_active_token=True, created_at=row.created_at.isoformat())


def access_emergency_card(db: Session, token: str, request: Request) -> EmergencyCardResponse:
    """
    PUBLIC — no authentication, deliberately. See app/models/emergency.py
    for why this is safe: narrow field set, distinct audit action, mandatory
    patient notification, hashed unguessable token, tight per-IP rate limit.
    """
    ip_address = request.client.host if request.client else None
    token_hash = _hash_token(token)

    row = (
        db.query(EmergencyAccessToken)
        .filter(EmergencyAccessToken.token_hash == token_hash, EmergencyAccessToken.is_active.is_(True))
        .first()
    )
    if not row:
        # No patient_id is known for an invalid/guessed token — logged
        # without one, same as any other unattributable DENIED attempt.
        db.add(
            AccessLog(
                user_id=None,
                patient_id=None,
                resource_type="emergency_qr",
                resource_id=None,
                action=AccessActionEnum.DENIED,
                ip_address=ip_address,
            )
        )
        db.commit()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or revoked emergency QR code.")

    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == row.patient_id).first()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient record not found.")

    allergies = db.query(Allergy).filter(Allergy.patient_id == profile.patient_id).all()
    active_items = (
        db.query(PrescriptionItem)
        .join(Prescription, Prescription.prescription_id == PrescriptionItem.prescription_id)
        .filter(Prescription.patient_id == profile.patient_id, Prescription.status == PrescriptionStatusEnum.ACTIVE)
        .all()
    )

    db.add(
        AccessLog(
            user_id=None,
            patient_id=profile.patient_id,
            resource_type="emergency_qr",
            resource_id=row.token_id,
            action=AccessActionEnum.EMERGENCY_QR_ACCESS,
            ip_address=ip_address,
        )
    )
    notification_service.create_notification(
        db,
        recipient_id=profile.user_id,
        notif_type=NotificationTypeEnum.EMERGENCY_QR_ACCESS,
        message=(
            f"Your emergency QR code was scanned"
            f"{f' from IP {ip_address}' if ip_address else ''}. "
            f"If this wasn't expected, revoke it immediately from your app and generate a new one."
        ),
        resource_type="emergency_qr",
        resource_id=row.token_id,
    )
    db.commit()

    return EmergencyCardResponse(
        full_name=profile.user.full_name,
        dob=profile.dob,
        blood_group=profile.blood_group,
        allergies=[EmergencyAllergyItem(allergen=a.allergen, severity=a.severity.value) for a in allergies],
        current_medications=[
            EmergencyMedicationItem(medicine_name=i.medicine_name, dosage=i.dosage, frequency=i.frequency)
            for i in active_items
        ],
        emergency_contact_name=profile.emergency_contact_name,
        emergency_contact_phone=profile.emergency_contact_phone,
    )
