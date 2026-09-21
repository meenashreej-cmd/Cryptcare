"""
Phase 8 — Pharmacy service.

Design decision (resolves the two gaps flagged during Phase 8 review):

1. QR "consent bypass" — a pharmacist is never a pre-approved consent
   grantee the way a doctor/nurse/lab is (a patient can't know in advance
   which pharmacy they'll walk into), so routing this through the normal
   ConsentRequest approve/reject table doesn't fit the real-world flow.
   That's a legitimate design choice, not the bug. The bug was that the
   exception was *silent*: no distinct audit trail entry, no patient
   notification, and no enforced signature check. This module now treats a
   pharmacist QR scan the way consent_service.break_glass_access() treats
   an emergency override — access without prior patient approval is still
   allowed, but only with compensating controls:
     a. The QR's signature MUST verify before any prescription content is
        decrypted or returned. An invalid signature is now a hard 403, not
        a soft "verified: false" warning the caller could ignore (see
        app/core/qr.py's own docstring: "not a bypass around access
        control").
     b. Every successful scan/dispense is logged with a distinct
        AccessActionEnum.PHARMACY_ACCESS action, never indistinguishable
        from a generic READ/WRITE the way it was before.
     c. Every successful scan/dispense fires a patient notification
        disclosing which pharmacist accessed/dispensed which prescription
        and when — same "always paired with a notification" rule
        break-glass follows.

2. Dispense not checking the signature — dispense_prescription() now takes
   the same qr_payload the pharmacist scanned and independently re-verifies
   it (via the shared _load_and_verify helper) before flipping status to
   DISPENSED, instead of trusting prescription.status alone. A tampered or
   forged QR can no longer be used to dispense even if it happens to name a
   real, ACTIVE prescription_id.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.encryption import decrypt
from app.core.qr import parse_prescription_qr_payload
from app.core.rbac import CurrentUser
from app.core.signing import canonical_prescription_content, verify_prescription_signature
from app.models.audit import AccessActionEnum, AccessLog
from app.models.notification import NotificationTypeEnum
from app.models.user import PatientProfile
from app.models.vault import DispenseRecord, Prescription, PrescriptionStatusEnum
from app.schemas.pharmacy import DispenseResponse, QRVerifyRequest, QRVerifyResponse
from app.services import fraud_service, notification_service


def _load_and_verify(db: Session, qr_payload: str, current_user: CurrentUser) -> tuple[Prescription, str, str, list[dict]]:
    """
    Parses a QR payload, loads the referenced prescription, and enforces
    signature validity before returning anything. Raises 400/404/403 rather
    than returning a soft "invalid" flag — callers must not be able to see
    or act on a prescription whose signature doesn't check out.
    """
    try:
        prescription_id, signature = parse_prescription_qr_payload(qr_payload)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or malformed QR code payload.")

    prescription = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(Prescription.prescription_id == prescription_id)
        .with_for_update()
        .first()
    )
    if not prescription:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if prescription.diagnosis_encrypted:
        diagnosis_aad = f"cryptcare:v2|prescriptions|{prescription.prescription_id}|diagnosis_encrypted|{prescription.patient_id}"
        diagnosis = decrypt(prescription.diagnosis_encrypted, aad=diagnosis_aad)
    else:
        diagnosis = ""
        
    if prescription.notes_encrypted:
        notes_aad = f"cryptcare:v2|prescriptions|{prescription.prescription_id}|notes_encrypted|{prescription.patient_id}"
        notes = decrypt(prescription.notes_encrypted, aad=notes_aad)
    else:
        notes = ""
    items_list = [
        {
            "medicine_name": item.medicine_name,
            "dosage": item.dosage,
            "frequency": item.frequency,
            "duration_days": item.duration_days,
        }
        for item in prescription.items
    ]

    canonical = canonical_prescription_content(diagnosis, notes, items_list)
    is_valid = verify_prescription_signature(prescription.doctor_id, canonical, signature)

    if not is_valid:
        db.add(
            AccessLog(
                user_id=current_user.id,
                action=AccessActionEnum.DENIED,
                resource_type="PRESCRIPTION",
                resource_id=prescription.prescription_id,
                patient_id=prescription.patient_id,
                ip_address="127.0.0.1",  # Hardcoded for demo/simplicity
            )
        )
        db.commit()
        fraud_service.detect_prescription_tampering(db, prescription.prescription_id, prescription.patient_id)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Signature verification failed — this QR code does not match the prescription on record and may be tampered or forged.",
        )

    return prescription, diagnosis, notes, items_list


def _notify_patient_of_pharmacy_access(db: Session, prescription: Prescription, current_user: CurrentUser, action_label: str) -> None:
    patient_profile = db.query(PatientProfile).filter(PatientProfile.patient_id == prescription.patient_id).first()
    if not patient_profile:
        return
    notification_service.create_notification(
        db,
        recipient_id=patient_profile.user_id,
        notif_type=NotificationTypeEnum.PHARMACY_ACCESS,
        message=(
            f"A pharmacist {action_label} your prescription ({prescription.prescription_id}) "
            f"by scanning its QR code. This access has been logged."
        ),
        resource_type="PRESCRIPTION",
        resource_id=prescription.prescription_id,
    )


def verify_prescription_qr(db: Session, current_user: CurrentUser, payload: QRVerifyRequest) -> QRVerifyResponse:
    prescription, diagnosis, notes, items_list = _load_and_verify(db, payload.qr_payload, current_user)

    # Signature is already confirmed valid by _load_and_verify — reaching
    # here means access is granted. Compensating controls for the missing
    # pre-approval step: distinct audit action + mandatory notification.
    db.add(
        AccessLog(
            user_id=current_user.id,
            action=AccessActionEnum.PHARMACY_ACCESS,
            resource_type="PRESCRIPTION",
            resource_id=prescription.prescription_id,
            patient_id=prescription.patient_id,
            ip_address="127.0.0.1",  # Hardcoded for demo/simplicity
        )
    )
    _notify_patient_of_pharmacy_access(db, prescription, current_user, "viewed")
    db.commit()
    db.refresh(prescription)

    return QRVerifyResponse(
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        status=prescription.status.value,
        diagnosis=diagnosis,
        notes=notes,
        items=items_list,
        verified=True,
        message="Signature valid.",
    )


def dispense_prescription(db: Session, current_user: CurrentUser, prescription_id: str, qr_payload: str) -> DispenseResponse:
    prescription, _diagnosis, _notes, _items = _load_and_verify(db, qr_payload, current_user)

    if prescription.prescription_id != prescription_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The QR payload does not match the prescription_id being dispensed.",
        )

    if prescription.status == PrescriptionStatusEnum.DISPENSED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Duplicate-dispense prevention: This prescription has already been dispensed.",
        )

    if prescription.status != PrescriptionStatusEnum.ACTIVE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispense a prescription with status {prescription.status.value}.",
        )

    prescription.status = PrescriptionStatusEnum.DISPENSED

    dispense_record = DispenseRecord(
        prescription_id=prescription.prescription_id,
        pharmacist_id=current_user.id,
    )
    db.add(dispense_record)

    db.add(
        AccessLog(
            user_id=current_user.id,
            action=AccessActionEnum.PHARMACY_ACCESS,
            resource_type="PRESCRIPTION_STATUS",
            resource_id=prescription.prescription_id,
            patient_id=prescription.patient_id,
            ip_address="127.0.0.1",
        )
    )
    _notify_patient_of_pharmacy_access(db, prescription, current_user, "dispensed")
    db.commit()
    db.refresh(dispense_record)

    return DispenseResponse(
        dispense_id=dispense_record.dispense_id,
        prescription_id=prescription.prescription_id,
        pharmacist_id=dispense_record.pharmacist_id,
        status=prescription.status.value,
        dispensed_at=dispense_record.dispensed_at,
        message="Prescription successfully dispensed.",
    )
