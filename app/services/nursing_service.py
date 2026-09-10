"""
Phase 6 — Nurse role: vital signs.

Reuses the same consent-gated choke point every other role's vault access
goes through (app.services.access_control.check_vault_access) — a nurse is
just another grantee_id in the consent_requests table, same as a doctor or
lab. No nurse-specific bypass exists: even though nurses often work under a
supervising doctor in real hospital workflows, this build does not implicitly
inherit the doctor's consent grant onto the nurse — each grantee holds (and
can independently lose) their own consent row, consistent with the
architecture's principle of least privilege. A patient (or an emergency
break-glass event) is what grants a nurse access, not another clinician.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.encryption import decrypt, encrypt
from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.nursing import VitalSign
from app.schemas.nursing import VitalSignCreateRequest
from app.services.access_control import check_vault_access


def _write_access_log(
    db: Session,
    user_id: str,
    resource_id: str | None,
    action: AccessActionEnum,
    patient_id: str | None = None,
) -> None:
    db.add(AccessLog(
        user_id=user_id,
        patient_id=patient_id,
        resource_type="vitals",
        resource_id=resource_id,
        action=action,
    ))


def _to_response_dict(row: VitalSign) -> dict:
    return {
        "vital_id": row.vital_id,
        "patient_id": row.patient_id,
        "recorded_by": row.recorded_by,
        "heart_rate_bpm": row.heart_rate_bpm,
        "blood_pressure_systolic": row.blood_pressure_systolic,
        "blood_pressure_diastolic": row.blood_pressure_diastolic,
        "temperature_celsius": row.temperature_celsius,
        "respiratory_rate": row.respiratory_rate,
        "spo2_percent": row.spo2_percent,
        "notes": decrypt(row.notes_encrypted) if row.notes_encrypted else None,
        "recorded_at": row.recorded_at,
    }


def record_vitals(db: Session, current_user: CurrentUser, payload: VitalSignCreateRequest) -> dict:
    if current_user.role != "NURSE":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only nurses can record vitals through this endpoint")

    if not check_vault_access(db, current_user, payload.patient_id, "vitals", "write"):
        _write_access_log(db, current_user.id, None, AccessActionEnum.DENIED, patient_id=payload.patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to record vitals for this patient")

    row = VitalSign(
        patient_id=payload.patient_id,
        recorded_by=current_user.id,
        heart_rate_bpm=payload.heart_rate_bpm,
        blood_pressure_systolic=payload.blood_pressure_systolic,
        blood_pressure_diastolic=payload.blood_pressure_diastolic,
        temperature_celsius=payload.temperature_celsius,
        respiratory_rate=payload.respiratory_rate,
        spo2_percent=payload.spo2_percent,
        notes_encrypted=encrypt(payload.notes) if payload.notes else None,
    )
    db.add(row)
    db.flush()

    _write_access_log(db, current_user.id, row.vital_id, AccessActionEnum.WRITE, patient_id=payload.patient_id)

    db.commit()
    db.refresh(row)
    return _to_response_dict(row)


def list_vitals(db: Session, current_user: CurrentUser, patient_id: str) -> list[dict]:
    if not check_vault_access(db, current_user, patient_id, "vitals", "read"):
        _write_access_log(db, current_user.id, None, AccessActionEnum.DENIED, patient_id=patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to read vitals for this patient")

    rows = (
        db.query(VitalSign)
        .filter(VitalSign.patient_id == patient_id)
        .order_by(VitalSign.recorded_at.desc())
        .all()
    )

    _write_access_log(db, current_user.id, None, AccessActionEnum.READ, patient_id=patient_id)
    db.commit()

    return [_to_response_dict(row) for row in rows]
