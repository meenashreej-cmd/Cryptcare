"""
Phase 9 — Fraud Detection service.

Detection functions are called inline, right after the triggering event's
own db.commit() — they run fresh queries rather than touching ORM instances
from the caller's session, which sidesteps the decrypt-then-commit
DetachedInstanceError pattern documented in vault_service/lab_service.

Each detect_* function is idempotent-ish per window: it checks whether an
OPEN alert of the same category already exists covering the same resource
before creating a new one, so a flood of repeat events doesn't spam
duplicate alerts.
"""

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.core.audit import write_access_log as _write_audit_log
from app.models.audit import AccessActionEnum, AccessLog
from app.models.consent import ConsentRequest
from app.models.fraud import FraudAlert, FraudAlertCategoryEnum, FraudAlertStatusEnum
from app.models.user import PatientProfile
from app.models.vault import Prescription, PrescriptionItem, SeverityEnum
from app.services import access_control, notification_service
from app.models.notification import NotificationTypeEnum

_DOCTOR_SHOPPING_WINDOW = timedelta(days=30)
_DOCTOR_SHOPPING_MIN_DOCTORS = 2
_TAMPERING_MIN_ATTEMPTS = 2
_BREAK_GLASS_WINDOW = timedelta(hours=24)
_BREAK_GLASS_MIN_PATIENTS = 3


def _open_alert_exists(db: Session, patient_id: str, category: FraudAlertCategoryEnum, resource_key: str) -> bool:
    """True if an OPEN alert of this category already references resource_key — avoids duplicate spam."""
    rows = (
        db.query(FraudAlert)
        .filter(
            FraudAlert.patient_id == patient_id,
            FraudAlert.category == category,
            FraudAlert.status == FraudAlertStatusEnum.OPEN,
        )
        .all()
    )
    for row in rows:
        ids = (row.related_resource_ids or "").split(",")
        if resource_key in ids:
            return True
    return False


def _create_alert(
    db: Session,
    patient_id: str,
    category: FraudAlertCategoryEnum,
    severity: SeverityEnum,
    counts: int,
    related_entity_type: str | None,
    context: str | None,
    related_resource_ids: list[str],
) -> FraudAlert:
    alert = FraudAlert(
        patient_id=patient_id,
        category=category,
        severity=severity,
        counts=counts,
        related_entity_type=related_entity_type,
        related_resource_ids=",".join(related_resource_ids),
    )
    db.add(alert)
    db.flush()
    
    if context:
        from app.core.encryption import encrypt
        aad = f"cryptcare:v2|fraud_alerts|{alert.alert_id}|encrypted_context|{patient_id}"
        alert.encrypted_context = encrypt(context, aad)
        
    return alert


def detect_doctor_shopping(db: Session, patient_id: str, medicine_name: str) -> FraudAlert | None:
    """
    Called right after a prescription is created and committed. Looks at
    every ACTIVE/DISPENSED prescription for this patient in the last 30
    days containing the same medicine (case-insensitive) and flags it if
    >=2 distinct doctors are behind them.
    """
    if _open_alert_exists(db, patient_id, FraudAlertCategoryEnum.DOCTOR_SHOPPING, medicine_name.lower()):
        return None

    since = datetime.utcnow() - _DOCTOR_SHOPPING_WINDOW
    rows = (
        db.query(Prescription.doctor_id, Prescription.prescription_id)
        .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.prescription_id)
        .filter(
            Prescription.patient_id == patient_id,
            Prescription.created_at >= since,
            PrescriptionItem.medicine_name.ilike(medicine_name),
        )
        .distinct()
        .all()
    )

    distinct_doctors = {doctor_id for doctor_id, _ in rows}
    if len(distinct_doctors) < _DOCTOR_SHOPPING_MIN_DOCTORS:
        return None

    prescription_ids = sorted({pid for _, pid in rows})
    alert = _create_alert(
        db,
        patient_id,
        FraudAlertCategoryEnum.DOCTOR_SHOPPING,
        SeverityEnum.MODERATE if len(distinct_doctors) == 2 else SeverityEnum.SEVERE,
        len(prescription_ids),
        "MEDICINE",
        (
            f"Patient obtained '{medicine_name}' prescriptions from "
            f"{len(distinct_doctors)} different doctors within the last 30 days."
        ),
        [medicine_name.lower(), *prescription_ids],
    )
    db.commit()
    return alert


def detect_prescription_tampering(db: Session, prescription_id: str, patient_id: str | None) -> FraudAlert | None:
    """
    Called after pharmacy_service logs a DENIED (signature-verification
    failure) AccessLog row for a given prescription_id. Counts how many
    DENIED attempts exist against this prescription_id total and flags it
    once it crosses the threshold — a single failed scan could be an honest
    typo/corrupt QR, but repeated failures against the same prescription_id
    look like someone retrying a forged code.
    """
    if patient_id is None:
        return None  # can't attribute the alert to a patient — nothing to do

    if _open_alert_exists(db, patient_id, FraudAlertCategoryEnum.PRESCRIPTION_TAMPERING, prescription_id):
        return None

    attempts = (
        db.query(AccessLog)
        .filter(
            AccessLog.resource_type == "PRESCRIPTION",
            AccessLog.resource_id == prescription_id,
            AccessLog.action == AccessActionEnum.DENIED,
        )
        .count()
    )
    if attempts < _TAMPERING_MIN_ATTEMPTS:
        return None

    alert = _create_alert(
        db,
        patient_id,
        FraudAlertCategoryEnum.PRESCRIPTION_TAMPERING,
        SeverityEnum.SEVERE,
        attempts,
        "PRESCRIPTION",
        (
            f"Failed signature verification attempts against prescription {prescription_id} "
            f"— the QR code presented does not match the record on file."
        ),
        [prescription_id],
    )
    db.commit()

    # Signature-tamper attempts are serious enough to warrant the same
    # immediate-disclosure treatment as break-glass, not a silent alert
    # only an insurer might see later.
    patient = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    if patient:
        notification_service.create_notification(
            db,
            recipient_id=patient.user_id,
            notif_type=NotificationTypeEnum.PHARMACY_ACCESS,
            message=(
                f"Security alert: {attempts} failed attempts to scan/dispense your prescription "
                f"({prescription_id}) with an invalid signature were detected and blocked."
            ),
            resource_type="PRESCRIPTION",
            resource_id=prescription_id,
        )
        db.commit()

    return alert


def detect_break_glass_abuse(db: Session, grantee_id: str) -> list[FraudAlert]:
    """
    Called after consent_service.break_glass_access commits a new
    break-glass grant. Looks at how many DISTINCT patients this grantee has
    invoked break-glass on in the last 24 hours; if >=3, flags an alert
    against EACH of those patients (each patient deserves visibility into
    the pattern involving their own record, not just an aggregate number).
    """
    since = datetime.utcnow() - _BREAK_GLASS_WINDOW
    rows = (
        db.query(ConsentRequest.patient_id, ConsentRequest.consent_id)
        .filter(
            ConsentRequest.grantee_id == grantee_id,
            ConsentRequest.is_break_glass.is_(True),
            ConsentRequest.created_at >= since,
        )
        .distinct()
        .all()
    )
    distinct_patients = {patient_id for patient_id, _ in rows}
    if len(distinct_patients) < _BREAK_GLASS_MIN_PATIENTS:
        return []

    consent_ids = sorted({cid for _, cid in rows})
    created: list[FraudAlert] = []
    for patient_id in distinct_patients:
        if _open_alert_exists(db, patient_id, FraudAlertCategoryEnum.BREAK_GLASS_ABUSE, grantee_id):
            continue
        alert = _create_alert(
            db,
            patient_id,
            FraudAlertCategoryEnum.BREAK_GLASS_ABUSE,
            SeverityEnum.SEVERE,
            len(distinct_patients),
            "DOCTOR",
            (
                f"Provider {grantee_id} invoked break-glass emergency access on "
                f"{len(distinct_patients)} different patients within 24 hours."
            ),
            [grantee_id, *consent_ids],
        )
        created.append(alert)
    if created:
        db.commit()
    return created


# --------------------------------------------------------------------------
# Read/review — INSURER (consent-gated per patient) and ADMIN (unrestricted)
# --------------------------------------------------------------------------

def list_all_alerts(
    db: Session, current_user: CurrentUser, status: FraudAlertStatusEnum | None, skip: int, limit: int
) -> tuple[list[FraudAlert], int]:
    if current_user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view global fraud alerts.")
    
    query = db.query(FraudAlert)
    if status:
        query = query.filter(FraudAlert.status == status)
        
    total_count = query.count()
    rows = query.order_by(FraudAlert.detected_at.desc()).offset(skip).limit(limit).all()
    return rows, total_count


def list_alerts_for_patient(db: Session, current_user: CurrentUser, patient_id: str) -> list[FraudAlert]:
    if access_control.is_owner(current_user, patient_id, db):
        pass  # patients can always see alerts concerning their own record
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view fraud alerts.")

    rows = (
        db.query(FraudAlert)
        .filter(FraudAlert.patient_id == patient_id)
        .order_by(FraudAlert.detected_at.desc())
        .all()
    )
    
    # Decrypt context for patient (admin gets None since encrypted_context isn't shown to admin)
    if current_user.role == "PATIENT":
        from app.core.encryption import decrypt
        for row in rows:
            if row.encrypted_context:
                aad = f"cryptcare:v2|fraud_alerts|{row.alert_id}|encrypted_context|{row.patient_id}"
                row.encrypted_context = decrypt(row.encrypted_context, aad)
                
    return rows


def review_alert(db: Session, current_user: CurrentUser, alert_id: str, new_status: FraudAlertStatusEnum) -> FraudAlert:
    if current_user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can review fraud alerts.")

    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fraud alert not found.")

    if new_status not in (FraudAlertStatusEnum.REVIEWED, FraudAlertStatusEnum.DISMISSED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status must be REVIEWED or DISMISSED.")

    alert.status = new_status
    alert.reviewed_by = current_user.id
    alert.reviewed_at = datetime.utcnow()

    _write_audit_log(
        db, user_id=current_user.id, resource_type="fraud_alerts",
        action=AccessActionEnum.WRITE, resource_id=alert.alert_id,
        patient_id=alert.patient_id,
    )
    db.commit()
    db.refresh(alert)
    return alert
