"""
Phase 8 — Pharmacy service.

Real client IP is now propagated from the HTTP layer through every audit
log entry — no more hardcoded 127.0.0.1. The endpoint passes
Request.client.host → ip_address parameter to verify_prescription_qr()
and dispense_prescription(), which pass it into _load_and_verify() and
every AccessLog write inside this module.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.encryption import decrypt
from app.core.qr import parse_prescription_qr_payload
from app.core.rbac import CurrentUser
from app.core.signing import canonical_prescription_content, verify_prescription_signature
from app.core.audit import write_access_log as _write_audit_log
from app.models.audit import AccessActionEnum
from app.models.notification import NotificationTypeEnum
from app.models.user import PatientProfile
from app.models.vault import DispenseRecord, Prescription, PrescriptionStatusEnum
from app.schemas.pharmacy import DispenseResponse, QRVerifyRequest, QRVerifyResponse
from app.services import fraud_service, notification_service


def _load_and_verify(
    db: Session,
    qr_payload: str,
    current_user: CurrentUser,
    ip_address: str = "unknown",
) -> tuple[Prescription, str, str, list[dict]]:
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

    diagnosis = ""
    if prescription.diagnosis_encrypted:
        diagnosis_aad = (
            f"cryptcare:v2|prescriptions|{prescription.prescription_id}"
            f"|diagnosis_encrypted|{prescription.patient_id}"
        )
        diagnosis = decrypt(prescription.diagnosis_encrypted, aad=diagnosis_aad)

    notes = ""
    if prescription.notes_encrypted:
        notes_aad = (
            f"cryptcare:v2|prescriptions|{prescription.prescription_id}"
            f"|notes_encrypted|{prescription.patient_id}"
        )
        notes = decrypt(prescription.notes_encrypted, aad=notes_aad)

    items_list = [
        {
            "medicine_name": item.medicine_name,
            "dosage": item.dosage,
            "frequency": item.frequency,
            "duration_days": item.duration_days,
        }
        for item in prescription.items
    ]

    canonical = canonical_prescription_content(
        diagnosis, notes, items_list, doctor_id=prescription.doctor_id
    )
    is_valid = verify_prescription_signature(prescription.doctor_id, canonical, signature)

    if not is_valid:
        _write_audit_log(
            db, user_id=current_user.id, resource_type="PRESCRIPTION",
            action=AccessActionEnum.DENIED,
            resource_id=prescription.prescription_id,
            patient_id=prescription.patient_id,
            ip_address=ip_address,
        )
        db.commit()
        fraud_service.detect_prescription_tampering(
            db, prescription.prescription_id, prescription.patient_id
        )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "Signature verification failed — this QR code does not match "
                "the prescription on record and may be tampered or forged."
            ),
        )

    return prescription, diagnosis, notes, items_list


def _notify_patient_of_pharmacy_access(
    db: Session,
    prescription: Prescription,
    current_user: CurrentUser,
    action_label: str,
) -> None:
    patient_profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.patient_id == prescription.patient_id)
        .first()
    )
    if not patient_profile:
        return
    notification_service.create_notification(
        db,
        recipient_id=patient_profile.user_id,
        notif_type=NotificationTypeEnum.PHARMACY_ACCESS,
        message=(
            f"A pharmacist {action_label} your prescription "
            f"({prescription.prescription_id}) by scanning its QR code. "
            "This access has been logged."
        ),
        resource_type="PRESCRIPTION",
        resource_id=prescription.prescription_id,
    )


def verify_prescription_qr(
    db: Session,
    current_user: CurrentUser,
    payload: QRVerifyRequest,
    ip_address: str = "unknown",
) -> QRVerifyResponse:
    prescription, diagnosis, notes, items_list = _load_and_verify(
        db, payload.qr_payload, current_user, ip_address=ip_address
    )

    _write_audit_log(
        db, user_id=current_user.id, resource_type="PRESCRIPTION",
        action=AccessActionEnum.PHARMACY_ACCESS,
        resource_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        ip_address=ip_address,
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


def dispense_prescription(
    db: Session,
    current_user: CurrentUser,
    prescription_id: str,
    qr_payload: str,
    ip_address: str = "unknown",
) -> DispenseResponse:
    prescription, _diagnosis, _notes, _items = _load_and_verify(
        db, qr_payload, current_user, ip_address=ip_address
    )

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

    _write_audit_log(
        db, user_id=current_user.id, resource_type="PRESCRIPTION_STATUS",
        action=AccessActionEnum.PHARMACY_ACCESS,
        resource_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        ip_address=ip_address,
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
