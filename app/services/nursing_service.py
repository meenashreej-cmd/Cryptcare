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


from app.schemas.nursing import NurseAssignmentRequest
from datetime import datetime

def assign_nurse(db: Session, current_user: CurrentUser, payload: NurseAssignmentRequest) -> dict:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can assign nurses to a care team")
        
    from app.models.user import User
    nurse = db.query(User).filter(User.user_id == payload.nurse_id, User.role == "NURSE").first()
    if not nurse:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nurse not found")
        
    from app.models.consent import ConsentRequest, ConsentStatusEnum, ResourceTypeEnum
    now = datetime.utcnow()
    doctor_consent = (
        db.query(ConsentRequest)
        .filter(
            ConsentRequest.patient_id == payload.patient_id,
            ConsentRequest.grantee_id == current_user.id,
            ConsentRequest.status == ConsentStatusEnum.ACTIVE,
            ConsentRequest.allow_delegation == True
        )
        .all()
    )
    
    from app.services.access_control import _PERMISSION_COVERS
    
    has_valid_consent = False
    for d_row in doctor_consent:
        if d_row.expires_at is None or d_row.expires_at < now:
            continue
        d_resource_matches = d_row.resource_type == ResourceTypeEnum.ALL or d_row.resource_type == payload.resource_type
        if not d_resource_matches:
            continue
        if payload.permission.value.lower() not in _PERMISSION_COVERS.get(d_row.permission, set()):
            continue
        has_valid_consent = True
        break
        
    if not has_valid_consent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have the required active consent with delegation enabled to assign this access")
        
    from app.models.nursing import CareTeamAssignment
    assignment = CareTeamAssignment(
        patient_id=payload.patient_id,
        doctor_id=current_user.id,
        nurse_id=payload.nurse_id,
        resource_type=payload.resource_type,
        permission=payload.permission,
        status="ACTIVE"
    )
    db.add(assignment)
    db.flush()
    
    _write_access_log(db, current_user.id, assignment.assignment_id, AccessActionEnum.CAREGIVER_GRANTED, patient_id=payload.patient_id)
    db.commit()
    db.refresh(assignment)
    
    return {
        "assignment_id": assignment.assignment_id,
        "patient_id": assignment.patient_id,
        "doctor_id": assignment.doctor_id,
        "nurse_id": assignment.nurse_id,
        "resource_type": assignment.resource_type,
        "permission": assignment.permission,
        "status": assignment.status,
        "created_at": assignment.created_at,
        "removed_at": assignment.removed_at
    }

def remove_nurse(db: Session, current_user: CurrentUser, assignment_id: str) -> dict:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can remove nurses from a care team")
        
    from app.models.nursing import CareTeamAssignment
    assignment = db.query(CareTeamAssignment).filter(CareTeamAssignment.assignment_id == assignment_id).first()
    if not assignment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
        
    if assignment.doctor_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only remove assignments that you created")
        
    if assignment.status != "ACTIVE":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignment is already removed")
        
    assignment.status = "REMOVED"
    assignment.removed_at = datetime.utcnow()
    
    _write_access_log(db, current_user.id, assignment.assignment_id, AccessActionEnum.CONSENT_REVOKED, patient_id=assignment.patient_id)
    db.commit()
    db.refresh(assignment)
    
    return {
        "assignment_id": assignment.assignment_id,
        "patient_id": assignment.patient_id,
        "doctor_id": assignment.doctor_id,
        "nurse_id": assignment.nurse_id,
        "resource_type": assignment.resource_type,
        "permission": assignment.permission,
        "status": assignment.status,
        "created_at": assignment.created_at,
        "removed_at": assignment.removed_at
    }

def get_assignments(db: Session, current_user: CurrentUser) -> list[dict]:
    if current_user.role != "DOCTOR":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can view their assignments")
        
    from app.models.nursing import CareTeamAssignment
    assignments = db.query(CareTeamAssignment).filter(CareTeamAssignment.doctor_id == current_user.id).order_by(CareTeamAssignment.created_at.desc()).all()
    
    return [
        {
            "assignment_id": a.assignment_id,
            "patient_id": a.patient_id,
            "doctor_id": a.doctor_id,
            "nurse_id": a.nurse_id,
            "resource_type": a.resource_type,
            "permission": a.permission,
            "status": a.status,
            "created_at": a.created_at,
            "removed_at": a.removed_at
        }
        for a in assignments
    ]

def get_nurse_patients(db: Session, current_user: CurrentUser) -> list[dict]:
    if current_user.role != "NURSE":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only nurses can view their assigned patients")
        
    from app.models.nursing import CareTeamAssignment
    assignments = db.query(CareTeamAssignment).filter(
        CareTeamAssignment.nurse_id == current_user.id,
        CareTeamAssignment.status == "ACTIVE"
    ).all()
    
    # We will return the unique patient IDs and who assigned them
    patients = {}
    for a in assignments:
        if a.patient_id not in patients:
            patients[a.patient_id] = []
        patients[a.patient_id].append({
            "doctor_id": a.doctor_id,
            "resource_type": a.resource_type,
            "permission": a.permission
        })
        
    return [{"patient_id": pid, "assignments": details} for pid, details in patients.items()]
