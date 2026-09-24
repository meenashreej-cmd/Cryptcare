"""
Phase 11 — Blood Bank service.

Inventory + request/fulfillment workflow. Two deliberate simplifications,
flagged the same way Phase 7's drug knowledge base is flagged as
illustrative-not-authoritative:

1. Compatibility matrix below is the standard textbook ABO/Rh chart, not a
   substitute for clinical crossmatching — a real transfusion always
   requires a lab crossmatch before issue, which this system doesn't model.
2. Inventory is treated as a single pooled system-wide stock for matching
   purposes (BloodUnit.blood_bank_id is kept for provenance/audit only, not
   used to silo matching to one facility) — this mirrors the existing
   codebase convention where LAB requests aren't scoped to a specific lab
   facility either (see lab_service.start_processing: any LAB-role user can
   pick up any PENDING request, no facility matching).

FEFO (first-expired-first-out) ordering is used when matching units to a
request — standard blood bank inventory practice, not specific to this
codebase.
"""

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.blood_bank import (
    BloodComponentEnum,
    BloodRequest,
    BloodRequestStatusEnum,
    BloodUnit,
    BloodUnitStatusEnum,
)
from app.models.notification import NotificationTypeEnum
from app.models.user import BloodBankProfile, PatientProfile, User
from app.schemas.blood_bank import (
    BloodInventorySummaryResponse,
    BloodRequestCreateRequest,
    BloodUnitCreateRequest,
)
from app.services import notification_service
from app.services.access_control import check_vault_access, is_owner

# Recipient blood_group -> set of donor blood_groups compatible for
# WHOLE_BLOOD / PACKED_RBC transfusion. Standard chart; O- is the universal
# RBC donor, AB+ the universal RBC recipient.
_RBC_COMPATIBLE_DONORS: dict[str, set[str]] = {
    "O-": {"O-"},
    "O+": {"O-", "O+"},
    "A-": {"O-", "A-"},
    "A+": {"O-", "O+", "A-", "A+"},
    "B-": {"O-", "B-"},
    "B+": {"O-", "O+", "B-", "B+"},
    "AB-": {"O-", "A-", "B-", "AB-"},
    "AB+": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
}


def _abo_only(blood_group: str) -> str:
    return blood_group[:-1]  # strip the +/- — Rh doesn't affect plasma compatibility


def _compatible_donor_groups(recipient_group: str, component: BloodComponentEnum) -> set[str]:
    if component in (BloodComponentEnum.WHOLE_BLOOD, BloodComponentEnum.PACKED_RBC):
        return _RBC_COMPATIBLE_DONORS.get(recipient_group, {recipient_group})

    # PLASMA: compatibility is the REVERSE of RBC — AB is the universal
    # plasma donor, O is the universal plasma recipient. Rh is irrelevant.
    if component == BloodComponentEnum.PLASMA:
        recipient_abo = _abo_only(recipient_group)
        plasma_map = {"AB": {"AB"}, "A": {"A", "AB"}, "B": {"B", "AB"}, "O": {"O", "A", "B", "AB"}}
        compatible_abo = plasma_map.get(recipient_abo, {recipient_abo})
        return {g for g in _RBC_COMPATIBLE_DONORS for abo in compatible_abo if g.startswith(abo)}

    # PLATELETS: simplified to ABO-group match (Rh commonly overridden in
    # practice for platelets) — same-group preferred, matched here on ABO only.
    recipient_abo = _abo_only(recipient_group)
    return {g for g in _RBC_COMPATIBLE_DONORS if g.startswith(recipient_abo)}


from app.core.audit import write_access_log as _write_access_log_shared


def _write_access_log(db, user_id, resource_id, action, patient_id=None):
    return _write_access_log_shared(
        db, user_id=user_id, resource_type="blood_requests",
        action=action, resource_id=resource_id, patient_id=patient_id,
    )


def _expire_stale_units(db: Session) -> None:
    """Lazy expiry, same pattern as access_control.expire_stale_consents — no scheduler required."""
    today = date.today()
    stale = db.query(BloodUnit).filter(BloodUnit.status == BloodUnitStatusEnum.AVAILABLE, BloodUnit.expiry_date < today).all()
    for unit in stale:
        unit.status = BloodUnitStatusEnum.EXPIRED
    if stale:
        db.commit()


# --------------------------------------------------------------------------
# BLOOD_BANK — inventory management
# --------------------------------------------------------------------------

def add_unit(db: Session, current_user: CurrentUser, payload: BloodUnitCreateRequest) -> BloodUnit:
    if current_user.role != "BLOOD_BANK":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only blood bank staff can add inventory")

    profile = db.query(BloodBankProfile).filter(BloodBankProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No blood bank profile found for this account")

    if payload.expiry_date <= payload.collection_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "expiry_date must be after collection_date")

    unit = BloodUnit(
        blood_bank_id=profile.blood_bank_id,
        blood_group=payload.blood_group,
        component=payload.component,
        collection_date=payload.collection_date,
        expiry_date=payload.expiry_date,
    )
    db.add(unit)
    db.flush()
    _write_access_log(db, current_user.id, unit.unit_id, AccessActionEnum.WRITE)
    db.commit()
    db.refresh(unit)
    return unit


def list_inventory_summary(db: Session, current_user: CurrentUser) -> list[BloodInventorySummaryResponse]:
    if current_user.role not in ("BLOOD_BANK", "ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only blood bank staff can view inventory")

    _expire_stale_units(db)

    rows = db.query(BloodUnit).filter(BloodUnit.status == BloodUnitStatusEnum.AVAILABLE).all()
    counts: dict[tuple[str, BloodComponentEnum], int] = {}
    for row in rows:
        key = (row.blood_group, row.component)
        counts[key] = counts.get(key, 0) + 1

    return [
        BloodInventorySummaryResponse(blood_group=g, component=c, available_units=n)
        for (g, c), n in sorted(counts.items(), key=lambda kv: (kv[0][0], kv[0][1].value))
    ]


# --------------------------------------------------------------------------
# DOCTOR / NURSE — request blood for a patient (consent-gated, same
# chokepoint as every other cross-role write)
# --------------------------------------------------------------------------

def create_blood_request(db: Session, current_user: CurrentUser, payload: BloodRequestCreateRequest) -> BloodRequest:
    if current_user.role not in ("DOCTOR", "PATIENT"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors and patients can request blood")

    patient_id = payload.patient_id
    if current_user.role == "PATIENT":
        # Resolve the patient_id from the PatientProfile — current_user.id
        # is the user_id (users table PK), NOT the patient_id (patient_profiles PK).
        # Using user_id here would silently store a wrong FK or violate the
        # patient_profiles.patient_id FK constraint.
        own_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not own_profile:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No patient profile found for this account")
        patient_id = own_profile.patient_id
    elif not patient_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "patient_id is required for doctors/nurses")

    if current_user.role != "PATIENT" and not check_vault_access(db, current_user, patient_id, "blood_requests", "write"):
        from sqlalchemy.exc import IntegrityError
        try:
            _write_access_log(db, current_user.id, None, AccessActionEnum.DENIED, patient_id=patient_id)
            db.commit()
        except IntegrityError:
            db.rollback()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to request blood for this patient")

    request = BloodRequest(
        patient_id=patient_id,
        requested_by=current_user.id,
        blood_group=payload.blood_group,
        component=payload.component,
        units_needed=payload.units_needed,
        urgency=payload.urgency,
    )
    db.add(request)
    db.flush()
    _write_access_log(db, current_user.id, request.request_id, AccessActionEnum.WRITE, patient_id=patient_id)
    db.commit()
    db.refresh(request)
    return request


def list_requests(db: Session, current_user: CurrentUser, patient_id: str | None = None) -> list[BloodRequest]:
    query = db.query(BloodRequest)

    if current_user.role in ("BLOOD_BANK", "ADMIN"):
        pass  # sees the full queue, filtered further by patient_id below if given
    elif current_user.role == "PATIENT":
        if patient_id and not is_owner(current_user, patient_id, db):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view another patient's blood requests")
        # Resolve caller's own patient_id if not explicitly given
        own_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        patient_id = patient_id or (own_profile.patient_id if own_profile else None)
        if not patient_id:
            return []
    elif current_user.role in ("DOCTOR", "NURSE"):
        query = query.filter(BloodRequest.requested_by == current_user.id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view blood requests")

    if patient_id:
        query = query.filter(BloodRequest.patient_id == patient_id)

    return query.order_by(BloodRequest.created_at.desc()).all()


# --------------------------------------------------------------------------
# BLOOD_BANK — fulfill / reject a PENDING request
# --------------------------------------------------------------------------

def fulfill_request(db: Session, current_user: CurrentUser, request_id: str) -> tuple[BloodRequest, list[str]]:
    if current_user.role != "BLOOD_BANK":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only blood bank staff can fulfill blood requests")

    request = db.query(BloodRequest).filter(BloodRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")
    if request.status != BloodRequestStatusEnum.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is already {request.status.value}")

    _expire_stale_units(db)

    compatible_groups = _compatible_donor_groups(request.blood_group, request.component)
    candidates = (
        db.query(BloodUnit)
        .filter(
            BloodUnit.blood_group.in_(compatible_groups),
            BloodUnit.component == request.component,
            BloodUnit.status == BloodUnitStatusEnum.AVAILABLE,
        )
        .order_by(BloodUnit.expiry_date.asc())  # FEFO
        .limit(request.units_needed)
        .with_for_update()
        .all()
    )

    if len(candidates) < request.units_needed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient compatible inventory: need {request.units_needed} unit(s) of "
                f"{request.component.value} compatible with {request.blood_group}, only {len(candidates)} available."
            ),
        )

    matched_ids = []
    for unit in candidates:
        unit.status = BloodUnitStatusEnum.ISSUED
        unit.reserved_for_request_id = request.request_id
        matched_ids.append(unit.unit_id)

    request.status = BloodRequestStatusEnum.FULFILLED
    request.fulfilled_by = current_user.id
    request.resolved_at = datetime.utcnow()

    _write_access_log(db, current_user.id, request.request_id, AccessActionEnum.WRITE, patient_id=request.patient_id)
    _notify_patient(db, request, "fulfilled")
    db.commit()
    db.refresh(request)
    return request, matched_ids


def reject_request(db: Session, current_user: CurrentUser, request_id: str, reason: str) -> BloodRequest:
    if current_user.role != "BLOOD_BANK":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only blood bank staff can reject blood requests")

    request = db.query(BloodRequest).filter(BloodRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")
    if request.status != BloodRequestStatusEnum.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is already {request.status.value}")

    request.status = BloodRequestStatusEnum.REJECTED
    request.fulfilled_by = current_user.id
    request.rejection_reason = reason
    request.resolved_at = datetime.utcnow()

    _write_access_log(db, current_user.id, request.request_id, AccessActionEnum.WRITE, patient_id=request.patient_id)
    _notify_patient(db, request, "rejected")
    db.commit()
    db.refresh(request)
    return request


def _notify_patient(db: Session, request: BloodRequest, outcome: str) -> None:
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == request.patient_id).first()
    if not profile:
        return
    notification_service.create_notification(
        db,
        recipient_id=profile.user_id,
        notif_type=NotificationTypeEnum.BLOOD_REQUEST_UPDATE,
        message=f"Your blood request ({request.request_id}) for {request.units_needed} unit(s) of {request.blood_group} {request.component.value} was {outcome}.",
        resource_type="blood_requests",
        resource_id=request.request_id,
    )


def reject_and_broadcast_shortage(db: Session, current_user: CurrentUser, request_id: str) -> BloodRequest:
    if current_user.role != "BLOOD_BANK":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only blood bank staff can reject blood requests")

    # 1. Reject the request using compare-and-set (atomic row lock)
    request = db.query(BloodRequest).filter(BloodRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")

    updated_count = db.query(BloodRequest).filter(
        BloodRequest.request_id == request_id,
        BloodRequest.status == BloodRequestStatusEnum.PENDING
    ).update({
        "status": BloodRequestStatusEnum.REJECTED,
        "fulfilled_by": current_user.id,
        "rejection_reason": "Insufficient inventory",
        "resolved_at": datetime.utcnow()
    })
    
    if updated_count == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request is no longer PENDING or does not exist")
        
    db.refresh(request)
    _write_access_log(db, current_user.id, request.request_id, AccessActionEnum.WRITE, patient_id=request.patient_id)
    _notify_patient(db, request, "rejected")

    # 2. Check cooldown globally for this blood group using compare-and-set
    from app.models.blood_bank import BroadcastCooldown
    from datetime import timedelta
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=15)
    
    cooldown_updated = db.query(BroadcastCooldown).filter(
        BroadcastCooldown.blood_group == request.blood_group,
        BroadcastCooldown.component == request.component,
        BroadcastCooldown.last_broadcast_at <= cutoff
    ).update({
        "last_broadcast_at": now
    })
    
    if cooldown_updated == 0:
        # Either on cooldown or missing row (which should be pre-seeded)
        db.commit()
        return request
    
    # 3. Broadcast URGENT_BLOOD_SHORTAGE to all patients, doctors, and nurses
    users_to_notify = db.query(User).filter(User.role.in_(["PATIENT", "DOCTOR", "NURSE"])).all()
    
    # Message must NOT contain PHI, patient info, hospital, requester, or request_id
    message = f"URGENT SHORTAGE: The Blood Bank urgently needs {request.blood_group} {request.component.value} donations."
    
    from app.models.notification import Notification, NotificationTypeEnum
    notifications = []
    for user in users_to_notify:
        notifications.append(
            Notification(
                recipient_id=user.user_id,
                type=NotificationTypeEnum.URGENT_BLOOD_SHORTAGE,
                message=message,
                resource_type=None,
                resource_id=None,
            )
        )
    
    if notifications:
        db.bulk_save_objects(notifications)
    
    db.commit()
    return request

