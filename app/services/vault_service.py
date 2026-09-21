"""
Phase 2 — Cryptographic Health Vault.

Implements: create_prescription, get_prescriptions, add_allergy, get_allergies,
add_vaccination, get_vaccinations, generate_prescription_qr.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.encryption import decrypt, encrypt
from app.core.qr import build_prescription_qr_payload, generate_qr_png
from app.core.rbac import CurrentUser
from app.core.signing import canonical_prescription_content, sign_prescription
from app.models.audit import AccessActionEnum, AccessLog
from app.models.notification import NotificationTypeEnum
from app.models.vault import Allergy, Prescription, PrescriptionItem, Vaccination
from app.schemas.vault import AllergyCreateRequest, PrescriptionCreateRequest, VaccinationCreateRequest
from app.services import clinical_safety_service, fraud_service, notification_service
from app.services.access_control import check_vault_access


def _write_access_log(db: Session, user_id: str, resource_type: str, resource_id: str | None, action: AccessActionEnum, patient_id: str | None = None):
    db.add(AccessLog(user_id=user_id, patient_id=patient_id, resource_type=resource_type, resource_id=resource_id, action=action))


def create_prescription(db: Session, current_user: CurrentUser, payload: PrescriptionCreateRequest) -> tuple[Prescription, dict]:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can create prescriptions")

    if not check_vault_access(db, current_user, payload.patient_id, "prescriptions", "write"):
        _write_access_log(db, current_user.id, "prescriptions", payload.patient_id, AccessActionEnum.DENIED, patient_id=payload.patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to write prescriptions for this patient")

    items_as_dicts = [item.model_dump() for item in payload.items]

    safety = clinical_safety_service.full_safety_check(db, payload.patient_id, items_as_dicts)
    if safety["blocking"]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Prescription blocked by clinical safety check", "safety": safety},
        )

    from app.models.user import DoctorProfile
    doctor_profile = db.query(DoctorProfile).filter_by(user_id=current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Doctor profile not found")

    prescription = Prescription(
        patient_id=payload.patient_id,
        doctor_id=doctor_profile.doctor_id,
    )
    db.add(prescription)
    db.flush()

    diagnosis_aad = f"cryptcare:v2|prescriptions|{prescription.prescription_id}|diagnosis_encrypted|{prescription.patient_id}"
    notes_aad = f"cryptcare:v2|prescriptions|{prescription.prescription_id}|notes_encrypted|{prescription.patient_id}"

    prescription.diagnosis_encrypted = encrypt(payload.diagnosis, diagnosis_aad)
    prescription.notes_encrypted = encrypt(payload.notes or "", notes_aad)

    canonical = canonical_prescription_content(payload.diagnosis, payload.notes or "", items_as_dicts)
    signature = sign_prescription(current_user.id, canonical)
    prescription.digital_signature = signature

    for item in payload.items:
        db.add(PrescriptionItem(
            prescription_id=prescription.prescription_id,
            medicine_name=item.medicine_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration_days=item.duration_days,
        ))

    _write_access_log(db, current_user.id, "prescriptions", prescription.prescription_id, AccessActionEnum.WRITE, patient_id=payload.patient_id)
    db.commit()
    db.refresh(prescription)

    notification_service.create_notification(
        db,
        recipient_id=_resolve_user_id_for_patient(db, payload.patient_id),
        notif_type=NotificationTypeEnum.PRESCRIPTION,
        message="Your doctor issued a new prescription",
        resource_type="prescriptions",
        resource_id=prescription.prescription_id,
    )
    db.commit()
    
    for item in payload.items:
        fraud_service.detect_doctor_shopping(db, payload.patient_id, item.medicine_name)
        
    return prescription, safety


def generate_prescription_qr(db: Session, current_user: CurrentUser, prescription_id: str) -> bytes:
    """Returns a PNG QR code encoding a reference + signature for this prescription
    (never the prescription's actual content — see app/core/qr.py). Access-gated
    the same as reading the prescription itself."""
    prescription = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not prescription:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")

    if not check_vault_access(db, current_user, prescription.patient_id, "prescriptions", "read"):
        _write_access_log(db, current_user.id, "prescriptions", prescription_id, AccessActionEnum.DENIED, patient_id=prescription.patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to read this prescription")

    _write_access_log(db, current_user.id, "prescriptions", prescription_id, AccessActionEnum.READ, patient_id=prescription.patient_id)
    db.commit()

    payload = build_prescription_qr_payload(prescription.prescription_id, prescription.digital_signature)
    return generate_qr_png(payload)


def get_prescriptions(db: Session, current_user: CurrentUser, patient_id: str) -> list[Prescription]:
    if not check_vault_access(db, current_user, patient_id, "prescriptions", "read"):
        _write_access_log(db, current_user.id, "prescriptions", patient_id, AccessActionEnum.DENIED, patient_id=patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to read prescriptions for this patient")

    rows = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    _write_access_log(db, current_user.id, "prescriptions", patient_id, AccessActionEnum.READ, patient_id=patient_id)
    db.commit()

    from app.core.signing import verify_prescription_signature, canonical_prescription_content

    # IMPORTANT: decrypt only AFTER commit, and only on rows detached (expunged)
    # from the session. Mutating a session-attached row's encrypted column and
    # then committing would flush the *decrypted* value back into the database,
    # permanently overwriting the ciphertext with plaintext. Expunging first
    # makes this mutation purely in-memory, for response building only.
    valid_rows = []
    for row in rows:
        # Access relationship before expunging to load items
        _ = row.items
        
        items_as_dicts = [
            {
                "medicine_name": i.medicine_name,
                "dosage": i.dosage,
                "frequency": i.frequency,
                "duration_days": i.duration_days,
            }
            for i in row.items
        ]
        
        diagnosis_aad = f"cryptcare:v2|prescriptions|{row.prescription_id}|diagnosis_encrypted|{row.patient_id}"
        notes_aad = f"cryptcare:v2|prescriptions|{row.prescription_id}|notes_encrypted|{row.patient_id}"
        
        db.expunge(row)
        row.diagnosis_encrypted = decrypt(row.diagnosis_encrypted, diagnosis_aad) if row.diagnosis_encrypted else ""
        row.notes_encrypted = decrypt(row.notes_encrypted, notes_aad) if row.notes_encrypted else ""
        
        canonical = canonical_prescription_content(row.diagnosis_encrypted, row.notes_encrypted, items_as_dicts)
        is_valid = verify_prescription_signature(row.doctor_id, canonical, row.digital_signature)
        
        if not is_valid:
            # Re-attach temporarily to create audit logs
            db.add(AccessLog(
                user_id=current_user.id,
                action=AccessActionEnum.DENIED,
                resource_type="PRESCRIPTION",
                resource_id=row.prescription_id,
                patient_id=row.patient_id,
                ip_address="127.0.0.1",
            ))
            db.commit()
            fraud_service.detect_prescription_tampering(db, row.prescription_id, row.patient_id)
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Signature verification failed for prescription {row.prescription_id} — data may be tampered."
            )
            
        valid_rows.append(row)

    return valid_rows


def add_allergy(db: Session, current_user: CurrentUser, patient_id: str, payload: AllergyCreateRequest) -> Allergy:
    if current_user.role == "PATIENT":
        if current_user.id != _resolve_user_id_for_patient(db, patient_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient can add their own allergies")
    elif current_user.role in ("DOCTOR", "NURSE"):
        if not check_vault_access(db, current_user, patient_id, "allergies", "write"):
            _write_access_log(db, current_user.id, "allergies", patient_id, AccessActionEnum.DENIED, patient_id=patient_id)
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to write allergies for this patient")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Role not permitted to add allergies")
    allergy = Allergy(patient_id=patient_id, allergen=payload.allergen, severity=payload.severity)
    db.add(allergy)
    _write_access_log(db, current_user.id, "allergies", patient_id, AccessActionEnum.WRITE, patient_id=patient_id)
    db.commit()
    db.refresh(allergy)
    return allergy


def get_allergies(db: Session, current_user: CurrentUser, patient_id: str) -> list[Allergy]:
    if not check_vault_access(db, current_user, patient_id, "allergies", "read"):
        _write_access_log(db, current_user.id, "allergies", patient_id, AccessActionEnum.DENIED, patient_id=patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to read allergies for this patient")

    rows = db.query(Allergy).filter(Allergy.patient_id == patient_id).all()
    _write_access_log(db, current_user.id, "allergies", patient_id, AccessActionEnum.READ, patient_id=patient_id)
    db.commit()
    return rows


def add_vaccination(db: Session, current_user: CurrentUser, patient_id: str, payload: VaccinationCreateRequest) -> Vaccination:
    if current_user.role == "PATIENT":
        if current_user.id != _resolve_user_id_for_patient(db, patient_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient can add their own vaccination records")
    elif current_user.role in ("DOCTOR", "NURSE"):
        if not check_vault_access(db, current_user, patient_id, "vaccinations", "write"):
            _write_access_log(db, current_user.id, "vaccinations", patient_id, AccessActionEnum.DENIED, patient_id=patient_id)
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to write vaccinations for this patient")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Role not permitted to add vaccinations")
    vaccination = Vaccination(
        patient_id=patient_id,
        vaccine_name=payload.vaccine_name,
        date_administered=payload.date_administered,
        next_due_date=payload.next_due_date,
    )
    db.add(vaccination)
    _write_access_log(db, current_user.id, "vaccinations", patient_id, AccessActionEnum.WRITE, patient_id=patient_id)
    db.commit()
    db.refresh(vaccination)
    return vaccination


def get_vaccinations(db: Session, current_user: CurrentUser, patient_id: str) -> list[Vaccination]:
    if not check_vault_access(db, current_user, patient_id, "vaccinations", "read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to read vaccinations for this patient")

    rows = db.query(Vaccination).filter(Vaccination.patient_id == patient_id).all()
    _write_access_log(db, current_user.id, "vaccinations", patient_id, AccessActionEnum.READ, patient_id=patient_id)
    db.commit()
    return rows


def _resolve_user_id_for_patient(db: Session, patient_id: str) -> str | None:
    from app.models.user import PatientProfile
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    return profile.user_id if profile else None
