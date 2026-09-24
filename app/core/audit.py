"""
app/core/audit.py — Shared audit-log helper with hash-chaining.

Phase 3: every AccessLog entry now carries a prev_hash — the SHA-256 digest
of the immediately preceding entry's canonical representation.  This forms a
tamper-evident append-only chain: altering any past row breaks all subsequent
hashes, making silent historical tampering detectable.

Usage (replaces every service's local _write_access_log):

    from app.core.audit import write_access_log

    write_access_log(
        db, user_id=current_user.id,
        resource_type="prescriptions", resource_id=rx_id,
        action=AccessActionEnum.WRITE, patient_id=patient_id,
    )

The caller must still call db.commit() themselves — write_access_log only
adds the row to the session, consistent with the existing pattern used
throughout the service layer.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AccessActionEnum, AccessLog, compute_entry_hash


def write_access_log(
    db: Session,
    user_id: str | None,
    resource_type: str,
    action: AccessActionEnum,
    resource_id: str | None = None,
    patient_id: str | None = None,
    ip_address: str | None = None,
) -> AccessLog:
    """
    Append a new AccessLog row chained to the most recent existing row.

    The prev_hash is computed from the *last committed* row's fields — so
    this function issues a lightweight SELECT MAX query to get that row
    before building the new entry. In the common case (sequential writes
    inside a request) this is a single indexed pk-order lookup.

    If no prior row exists (genesis / first-ever entry) prev_hash is NULL.
    """
    # Fetch the most recent committed row by insertion order (log_id is a
    # UUID but we order by accessed_at + log_id for determinism).
    last = (
        db.query(AccessLog)
        .order_by(AccessLog.accessed_at.desc(), AccessLog.log_id.desc())
        .first()
    )

    prev_hash: str | None = None
    if last is not None and last.accessed_at is not None:
        # Use the already-committed timestamp so the hash is stable.
        prev_hash = compute_entry_hash(
            log_id=last.log_id,
            user_id=last.user_id,
            action=last.action.value,
            resource_type=last.resource_type,
            resource_id=last.resource_id,
            patient_id=last.patient_id,
            accessed_at=str(last.accessed_at),
        )

    entry = AccessLog(
        user_id=user_id,
        patient_id=patient_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        ip_address=ip_address,
        prev_hash=prev_hash,
    )
    db.add(entry)
    return entry
