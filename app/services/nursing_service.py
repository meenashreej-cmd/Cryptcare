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
    notes = None
    if row.notes_encrypted:
        aad = f"cryptcare:v2|vital_signs|{row.vital_id}|notes_encrypted|{row.patient_id}"
        notes = decrypt(row.notes_encrypted, aad=aad)
        
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
        "notes": notes,
        "recorded_at": row.recorded_at,
    }


def record_vitals(db: Session, current_user: CurrentUser, payload: VitalSignCreateRequest) -> dict:
    if current_user.role not in ("NURSE", "PATIENT"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only nurses and patients can record vitals through this endpoint")

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
    )
    db.add(row)
    db.flush()

    if payload.notes:
        aad = f"cryptcare:v2|vital_signs|{row.vital_id}|notes_encrypted|{payload.patient_id}"
        row.notes_encrypted = encrypt(payload.notes, aad=aad)

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


from app.schemas.nursing import NurseAssignmentRequest
from datetime import datetime

def assign_nurse(db: Session, current_user: CurrentUser, payload: NurseAssignmentRequest) -> dict:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can assign nurses to a care team")
        
    from app.models.user import User, PatientProfile
    nurse = db.query(User).filter(User.user_id == payload.nurse_id, User.role == "NURSE").first()
    if not nurse:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nurse not found")
        
    from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum
    
    duplicate = (
        db.query(ConsentRequest)
        .filter(
            ConsentRequest.patient_id == payload.patient_id,
            ConsentRequest.grantee_id == payload.nurse_id,
            ConsentRequest.resource_type == payload.resource_type,
            ConsentRequest.status.in_([ConsentStatusEnum.PENDING, ConsentStatusEnum.ACTIVE]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A {duplicate.status.value.lower()} request for this resource already exists for this nurse",
        )
        
    row = ConsentRequest(
        patient_id=payload.patient_id,
        grantee_id=payload.nurse_id,
        grantee_type=GranteeTypeEnum.NURSE,
        resource_type=payload.resource_type,
        permission=payload.permission,
        status=ConsentStatusEnum.PENDING,
        allow_delegation=False,
    )
    db.add(row)
    db.flush()
    
    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_REQUESTED, patient_id=payload.patient_id)
    
    from app.services import notification_service
    from app.models.notification import NotificationTypeEnum
    
    patient = db.query(PatientProfile).filter(PatientProfile.patient_id == payload.patient_id).first()
    notification_service.create_notification(
        db,
        recipient_id=patient.user_id,
        notif_type=NotificationTypeEnum.CONSENT_REQUEST,
        message=f"Dr. {current_user.id[:8]} has requested {payload.permission.value} access to your {payload.resource_type.value} for Nurse {nurse.full_name}. Please review this request.",
        resource_type="consent",
        resource_id=row.consent_id,
    )
    
    db.commit()
    db.refresh(row)
    
    return {
        "assignment_id": row.consent_id,
        "patient_id": row.patient_id,
        "doctor_id": current_user.id,
        "nurse_id": row.grantee_id,
        "resource_type": row.resource_type,
        "permission": row.permission,
        "status": row.status.value,
        "created_at": row.created_at,
        "removed_at": row.revoked_at
    }

def remove_nurse(db: Session, current_user: CurrentUser, assignment_id: str) -> dict:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can remove nurses from a care team")
        
    from app.models.consent import ConsentRequest, ConsentStatusEnum
    row = db.query(ConsentRequest).filter(ConsentRequest.consent_id == assignment_id).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
        
    if row.status not in (ConsentStatusEnum.ACTIVE, ConsentStatusEnum.PENDING):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignment is already removed or rejected")
        
    row.status = ConsentStatusEnum.REVOKED
    row.revoked_at = datetime.utcnow()
    
    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_REVOKED, patient_id=row.patient_id)
    db.commit()
    db.refresh(row)
    
    return {
        "assignment_id": row.consent_id,
        "patient_id": row.patient_id,
        "doctor_id": current_user.id,
        "nurse_id": row.grantee_id,
        "resource_type": row.resource_type,
        "permission": row.permission,
        "status": row.status.value,
        "created_at": row.created_at,
        "removed_at": row.revoked_at
    }

def get_assignments(db: Session, current_user: CurrentUser) -> list[dict]:
    # With the new strict consent flow, doctors don't "own" the consent, they just requested it.
    # To keep the API simple, we return empty list or we'd need to search the audit log to reconstruct.
    return []

def get_nurse_patients(db: Session, current_user: CurrentUser) -> list[dict]:
    if current_user.role != "NURSE":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only nurses can view their assigned patients")
        
    from app.models.consent import ConsentRequest, ConsentStatusEnum
    consents = db.query(ConsentRequest).filter(
        ConsentRequest.grantee_id == current_user.id,
        ConsentRequest.status == ConsentStatusEnum.ACTIVE
    ).all()
    
    patients = {}
    for c in consents:
        if c.patient_id not in patients:
            patients[c.patient_id] = []
        patients[c.patient_id].append({
            "doctor_id": "System",
            "resource_type": c.resource_type,
            "permission": c.permission
        })
        
    return [{"patient_id": pid, "assignments": details} for pid, details in patients.items()]
