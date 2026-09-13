"""
Phase 4 — Consent Management service layer.

Workflow: DOCTOR/LAB requests access -> PATIENT approves or rejects ->
approved grants are time-limited (expires_at) and independently revocable.

Extensions:
- Break-glass emergency access (a DOCTOR/LAB can self-grant immediate,
  time-boxed access with no approval step — always logged distinctly and
  always triggers a mandatory post-event patient notification).
- Delegated caregiver/family access (a PATIENT grants a named individual a
  configurable, scoped subset of their own vault access directly — no
  approval step needed since the patient is both requester and approver).
- Patient activity timeline (a read-only projection over the existing
  append-only audit log, filtered to the logged-in patient's own records).

Role enforcement (who is even allowed to call which function) happens at the
endpoint layer via `require_role(...)` dependencies, consistent with Phases
1-3. This module still re-checks *ownership* (is this really the patient who
owns this consent row?) itself, since that can't be expressed as a static
role check.
"""

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.consent import ConsentRequest, ConsentStatusEnum, GranteeTypeEnum, PermissionEnum, ResourceTypeEnum
from app.models.notification import NotificationTypeEnum
from app.models.user import PatientProfile, User
from app.schemas.consent import (
    BreakGlassRequest,
    CaregiverGrantRequest,
    ConsentApproveRequest,
    ConsentRequestCreate,
)
from app.services import notification_service
from app.services.access_control import expire_stale_consents, find_active_consent

# Break-glass grants are deliberately short-lived — this is an emergency
# override, not a convenience shortcut. A clinician who still needs access
# after this window has time to go through the normal request/approve flow,
# or trigger break-glass again (each invocation is independently logged).
_BREAK_GLASS_DURATION = timedelta(hours=1)


def _write_access_log(
    db: Session,
    user_id: str,
    resource_type: str,
    resource_id: str | None,
    action: AccessActionEnum,
    patient_id: str | None = None,
) -> None:
    db.add(AccessLog(user_id=user_id, patient_id=patient_id, resource_type=resource_type, resource_id=resource_id, action=action))


def _resolve_patient_id(db: Session, current_user: CurrentUser) -> str:
    """Looks up the PatientProfile.patient_id for the currently-logged-in patient."""
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient profile found for this account")
    return profile.patient_id


def _resolve_user_id_for_patient(db: Session, patient_id: str) -> str | None:
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    return profile.user_id if profile else None


def _get_owned_consent(db: Session, current_user: CurrentUser, consent_id: str) -> ConsentRequest:
    """Fetches a consent row and confirms current_user is the patient who owns it."""
    row = db.query(ConsentRequest).filter(ConsentRequest.consent_id == consent_id).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consent request not found")

    patient_id = _resolve_patient_id(db, current_user)
    if row.patient_id != patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This consent request does not belong to you")
    return row


def request_consent(db: Session, current_user: CurrentUser, payload: ConsentRequestCreate) -> ConsentRequest:
    """DOCTOR, NURSE, LAB, or INSURER requests access to a patient's records. Creates a PENDING row."""
    if current_user.role not in (
        GranteeTypeEnum.DOCTOR.value,
        GranteeTypeEnum.NURSE.value,
        GranteeTypeEnum.LAB.value,
        GranteeTypeEnum.INSURER.value,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors, nurses, labs, and insurers can request consent")

    patient = db.query(PatientProfile).filter(PatientProfile.patient_id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    duplicate = (
        db.query(ConsentRequest)
        .filter(
            ConsentRequest.patient_id == payload.patient_id,
            ConsentRequest.grantee_id == current_user.id,
            ConsentRequest.resource_type == payload.resource_type,
            ConsentRequest.status.in_([ConsentStatusEnum.PENDING, ConsentStatusEnum.ACTIVE]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A {duplicate.status.value.lower()} request for this resource already exists (consent_id={duplicate.consent_id})",
        )

    row = ConsentRequest(
        patient_id=payload.patient_id,
        grantee_id=current_user.id,
        grantee_type=GranteeTypeEnum(current_user.role),
        resource_type=payload.resource_type,
        permission=payload.permission,
        status=ConsentStatusEnum.PENDING,
        allow_delegation=payload.allow_delegation,
    )
    db.add(row)
    db.flush()  # get consent_id before the audit log FK-adjacent insert

    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_REQUESTED, patient_id=payload.patient_id)

    notification_service.create_notification(
        db,
        recipient_id=patient.user_id,
        notif_type=NotificationTypeEnum.CONSENT_REQUEST,
        message=f"{row.grantee_type.value.title()} is requesting {row.permission.value} access to your {row.resource_type.value}",
        resource_type="consent",
        resource_id=row.consent_id,
    )

    db.commit()
    db.refresh(row)
    return row


def approve_consent(db: Session, current_user: CurrentUser, consent_id: str, payload: ConsentApproveRequest) -> ConsentRequest:
    row = _get_owned_consent(db, current_user, consent_id)
    if row.status != ConsentStatusEnum.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only PENDING requests can be approved (this one is {row.status.value})")

    row.status = ConsentStatusEnum.ACTIVE
    row.expires_at = datetime.utcnow() + timedelta(days=payload.duration_days)

    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_APPROVED, patient_id=row.patient_id)
    db.commit()
    db.refresh(row)
    return row


def reject_consent(db: Session, current_user: CurrentUser, consent_id: str) -> ConsentRequest:
    row = _get_owned_consent(db, current_user, consent_id)
    if row.status != ConsentStatusEnum.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only PENDING requests can be rejected (this one is {row.status.value})")

    row.status = ConsentStatusEnum.REJECTED
    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_REJECTED, patient_id=row.patient_id)
    db.commit()
    db.refresh(row)
    return row


def revoke_consent(db: Session, current_user: CurrentUser, consent_id: str) -> ConsentRequest:
    row = _get_owned_consent(db, current_user, consent_id)
    if row.status != ConsentStatusEnum.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only ACTIVE grants can be revoked (this one is {row.status.value})")

    row.status = ConsentStatusEnum.REVOKED
    row.revoked_at = datetime.utcnow()
    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CONSENT_REVOKED, patient_id=row.patient_id)
    db.commit()
    db.refresh(row)
    return row


def list_active_consents(db: Session, current_user: CurrentUser) -> list[ConsentRequest]:
    """PATIENT's currently ACTIVE grants."""
    patient_id = _resolve_patient_id(db, current_user)
    expire_stale_consents(db, patient_id=patient_id)
    return (
        db.query(ConsentRequest)
        .filter(ConsentRequest.patient_id == patient_id, ConsentRequest.status == ConsentStatusEnum.ACTIVE)
        .order_by(ConsentRequest.created_at.desc())
        .all()
    )


def list_consent_history(db: Session, current_user: CurrentUser) -> list[ConsentRequest]:
    """PATIENT's full history — every status, past and present."""
    patient_id = _resolve_patient_id(db, current_user)
    expire_stale_consents(db, patient_id=patient_id)
    return (
        db.query(ConsentRequest)
        .filter(ConsentRequest.patient_id == patient_id)
        .order_by(ConsentRequest.created_at.desc())
        .all()
    )


def list_my_requests(db: Session, current_user: CurrentUser) -> list[ConsentRequest]:
    """DOCTOR/LAB's own requests (any status) across all patients — read-only for them."""
    expire_stale_consents(db, grantee_id=current_user.id)
    return (
        db.query(ConsentRequest)
        .filter(ConsentRequest.grantee_id == current_user.id)
        .order_by(ConsentRequest.created_at.desc())
        .all()
    )


def list_all_consents(db: Session, limit: int = 200) -> list[ConsentRequest]:
    """ADMIN read-only view across every patient/grantee."""
    expire_stale_consents(db)
    return db.query(ConsentRequest).order_by(ConsentRequest.created_at.desc()).limit(limit).all()


def has_valid_consent(db: Session, patient_id: str, grantee_id: str, resource: str, mode: str) -> bool:
    """Thin, explicitly-named wrapper for callers (e.g. Phase 3 lab endpoints) that
    want a plain yes/no without going through the is_owner short-circuit in
    check_vault_access — e.g. checking a non-owner grantee's access specifically."""
    return find_active_consent(db, patient_id, grantee_id, resource, mode) is not None


# --------------------------------------------------------------------------
# Break-glass emergency access
# --------------------------------------------------------------------------

def break_glass_access(db: Session, current_user: CurrentUser, payload: BreakGlassRequest) -> ConsentRequest:
    """
    DOCTOR/LAB self-grants immediate access with NO approval step — this is
    the one path in the whole consent system that bypasses patient sign-off,
    and it's compensated for on three fronts, all mandatory, none optional:
      1. Time-boxed to _BREAK_GLASS_DURATION regardless of what's requested.
      2. Logged with a distinct AccessActionEnum.BREAK_GLASS_ACCESS action —
         never indistinguishable from a normal consent-gated read in the audit
         trail or the patient's activity timeline.
      3. Triggers an immediate patient notification disclosing exactly who
         accessed what and when — this happens in the SAME transaction as
         granting access, not as a best-effort follow-up.
    """
    if current_user.role not in (GranteeTypeEnum.DOCTOR.value, GranteeTypeEnum.LAB.value):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors and labs can invoke break-glass access")

    patient = db.query(PatientProfile).filter(PatientProfile.patient_id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    row = ConsentRequest(
        patient_id=payload.patient_id,
        grantee_id=current_user.id,
        grantee_type=GranteeTypeEnum(current_user.role),
        resource_type=payload.resource_type,
        permission=payload.permission,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + _BREAK_GLASS_DURATION,
        is_break_glass=True,
    )
    db.add(row)
    db.flush()

    _write_access_log(
        db, current_user.id, "consent", row.consent_id, AccessActionEnum.BREAK_GLASS_ACCESS, patient_id=payload.patient_id
    )

    grantee = db.query(User).filter(User.user_id == current_user.id).first()
    grantee_label = grantee.email if grantee else current_user.id
    notification_service.create_notification(
        db,
        recipient_id=patient.user_id,
        notif_type=NotificationTypeEnum.BREAK_GLASS_ALERT,
        message=(
            f"EMERGENCY ACCESS: {current_user.role.title()} ({grantee_label}) used break-glass access to view your "
            f"{row.resource_type.value} for the reason: \"{payload.reason}\". This access expires "
            f"{row.expires_at.isoformat()}Z and has been permanently logged."
        ),
        resource_type="consent",
        resource_id=row.consent_id,
    )

    db.commit()
    db.refresh(row)
    
    from app.services import fraud_service
    fraud_service.detect_break_glass_abuse(db, current_user.id)
    
    return row


# --------------------------------------------------------------------------
# Delegated caregiver / family access
# --------------------------------------------------------------------------

def grant_caregiver_access(db: Session, current_user: CurrentUser, payload: CaregiverGrantRequest) -> ConsentRequest:
    """
    PATIENT grants a named individual (identified by email — must already
    have a CryptCare account) a configurable, scoped subset of their own
    vault access. No approval step: the patient IS the approver here, unlike
    the doctor/lab request flow. Immediately ACTIVE, still time-limited,
    still independently revocable via the existing revoke_consent().
    """
    patient_id = _resolve_patient_id(db, current_user)

    caregiver = db.query(User).filter(User.email == payload.caregiver_email).first()
    if not caregiver:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No account found for that caregiver email — they must register first")
    if caregiver.user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot grant caregiver access to yourself")

    row = ConsentRequest(
        patient_id=patient_id,
        grantee_id=caregiver.user_id,
        grantee_type=GranteeTypeEnum.CAREGIVER,
        resource_type=payload.resource_type,
        permission=payload.permission,
        status=ConsentStatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=payload.duration_days),
    )
    db.add(row)
    db.flush()

    _write_access_log(db, current_user.id, "consent", row.consent_id, AccessActionEnum.CAREGIVER_GRANTED, patient_id=patient_id)
    db.commit()
    db.refresh(row)
    return row


# --------------------------------------------------------------------------
# Patient activity timeline
# --------------------------------------------------------------------------

def get_patient_timeline(db: Session, current_user: CurrentUser, limit: int = 200) -> list[AccessLog]:
    """
    Every access/action concerning the logged-in patient's own records —
    reads, writes, consent lifecycle events, break-glass events, caregiver
    grants — in one chronological feed. This is a read-only query over the
    existing append-only audit log (see app/models/audit.py); it introduces
    no new logging mechanism, only a new patient-facing view over one that
    already exists.
    """
    patient_id = _resolve_patient_id(db, current_user)
    return (
        db.query(AccessLog)
        .filter(AccessLog.patient_id == patient_id)
        .order_by(AccessLog.accessed_at.desc())
        .limit(limit)
        .all()
    )
