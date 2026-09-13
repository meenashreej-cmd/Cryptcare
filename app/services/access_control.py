"""
Shared consent-aware access-control check, reused by vault_service (Phase 2),
lab_service (Phase 3), and consent_service (Phase 4) itself.

This is the single choke point every cross-role read/write of patient data
must pass through — see CryptCare_Phase_Specs.md, Phase 2, `check_vault_access`.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.consent import ConsentRequest, ConsentStatusEnum, PermissionEnum, ResourceTypeEnum
from app.models.user import PatientProfile

# Which requested "mode" strings each stored PermissionEnum value satisfies.
_PERMISSION_COVERS: dict[PermissionEnum, set[str]] = {
    PermissionEnum.READ: {"read"},
    PermissionEnum.WRITE: {"write"},
    PermissionEnum.BOTH: {"read", "write"},
}


def is_owner(current_user: CurrentUser, patient_id: str, db: Session) -> bool:
    """True if current_user IS the patient identified by patient_id."""
    if current_user.role != "PATIENT":
        return False
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    return bool(profile and profile.user_id == current_user.id)


def expire_stale_consents(db: Session, patient_id: str | None = None, grantee_id: str | None = None) -> int:
    """
    Flips any ACTIVE row whose expires_at has passed to EXPIRED. Scoped to a
    patient and/or grantee when given (cheap, called opportunistically on the
    hot path); called with no filters from admin/history listing endpoints to
    sweep everything. No scheduler required — status is kept accurate lazily,
    at read/check time, which is sufficient for an academic build's audit trail.
    """
    query = db.query(ConsentRequest).filter(
        ConsentRequest.status == ConsentStatusEnum.ACTIVE,
        ConsentRequest.expires_at.isnot(None),
        ConsentRequest.expires_at < datetime.utcnow(),
    )
    if patient_id is not None:
        query = query.filter(ConsentRequest.patient_id == patient_id)
    if grantee_id is not None:
        query = query.filter(ConsentRequest.grantee_id == grantee_id)

    rows = query.all()
    for row in rows:
        row.status = ConsentStatusEnum.EXPIRED
        db.add(AccessLog(
            user_id=row.grantee_id,
            patient_id=row.patient_id,
            resource_type="consent",
            resource_id=row.consent_id,
            action=AccessActionEnum.CONSENT_EXPIRED,
        ))
    if rows:
        db.commit()
    return len(rows)


def find_active_consent(
    db: Session, patient_id: str, grantee_id: str, resource: str, mode: str
) -> ConsentRequest | None:
    """
    Returns the ACTIVE, non-expired consent row (if any) that covers this
    grantee accessing `resource` in `mode` ("read"/"write") for this patient.
    A row with resource_type=ALL covers every resource. Permission is checked
    via _PERMISSION_COVERS (READ only covers read, WRITE only write, BOTH both).
    """
    expire_stale_consents(db, patient_id=patient_id, grantee_id=grantee_id)

    try:
        resource_enum = ResourceTypeEnum(resource)
    except ValueError:
        # Unknown resource string — nothing can match it except an ALL-scoped grant.
        resource_enum = None

    now = datetime.utcnow()
    rows = (
        db.query(ConsentRequest)
        .filter(
            ConsentRequest.patient_id == patient_id,
            ConsentRequest.grantee_id == grantee_id,
            ConsentRequest.status == ConsentStatusEnum.ACTIVE,
        )
        .all()
    )

    for row in rows:
        if row.expires_at is None or row.expires_at < now:
            continue  # belt-and-suspenders; expire_stale_consents should have already caught this
        resource_matches = row.resource_type == ResourceTypeEnum.ALL or (
            resource_enum is not None and row.resource_type == resource_enum
        )
        if not resource_matches:
            continue
        if mode not in _PERMISSION_COVERS.get(row.permission, set()):
            continue
        return row

    # If no direct consent is found, check if grantee is a nurse with an active delegation
    from app.models.user import User
    from app.models.nursing import CareTeamAssignment
    grantee = db.query(User).filter(User.user_id == grantee_id).first()
    if grantee and grantee.role == "NURSE":
        assignments = (
            db.query(CareTeamAssignment)
            .filter(
                CareTeamAssignment.patient_id == patient_id,
                CareTeamAssignment.nurse_id == grantee_id,
                CareTeamAssignment.status == "ACTIVE"
            )
            .all()
        )
        for assignment in assignments:
            resource_matches = assignment.resource_type == ResourceTypeEnum.ALL or (
                resource_enum is not None and assignment.resource_type == resource_enum
            )
            if not resource_matches:
                continue
            if mode not in _PERMISSION_COVERS.get(assignment.permission, set()):
                continue
            
            # The assignment matches the request. Now check if the supervising doctor has active consent with allow_delegation.
            doctor_consent = (
                db.query(ConsentRequest)
                .filter(
                    ConsentRequest.patient_id == patient_id,
                    ConsentRequest.grantee_id == assignment.doctor_id,
                    ConsentRequest.status == ConsentStatusEnum.ACTIVE,
                    ConsentRequest.allow_delegation == True
                )
                .all()
            )
            for d_row in doctor_consent:
                if d_row.expires_at is None or d_row.expires_at < now:
                    continue
                d_resource_matches = d_row.resource_type == ResourceTypeEnum.ALL or (
                    resource_enum is not None and d_row.resource_type == resource_enum
                )
                if not d_resource_matches:
                    continue
                if mode not in _PERMISSION_COVERS.get(d_row.permission, set()):
                    continue
                
                # Found valid doctor consent that allows delegation!
                return d_row

    return None


def check_vault_access(
    db: Session,
    current_user: CurrentUser,
    patient_id: str,
    resource: str,
    mode: str,
) -> bool:
    """
    resource: e.g. "prescriptions", "lab_reports", "lab_requests", "allergies", "vaccinations"
    mode: "read" | "write"
    """
    if is_owner(current_user, patient_id, db):
        return True

    grant = find_active_consent(db, patient_id, current_user.id, resource, mode)
    return grant is not None
