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


import uuid
from sqlalchemy import insert, select, literal, exists
from sqlalchemy.exc import SQLAlchemyError

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
    Append a new AccessLog row chained to the most recent existing row,
    using an atomic compare-and-set to prevent concurrent forks of the chain.
    
    This function will retry up to 5 times if a concurrent transaction
    advances the chain before we do. If it succeeds, the new entry is 
    immediately added to the session's transaction, requiring the caller 
    to commit it.
    """
    max_retries = 5
    for attempt in range(max_retries):
        last = (
            db.query(AccessLog)
            .order_by(AccessLog.accessed_at.desc(), AccessLog.log_id.desc())
            .first()
        )

        prev_hash: str | None = None
        if last is not None and last.accessed_at is not None:
            prev_hash = compute_entry_hash(
                log_id=last.log_id,
                user_id=last.user_id,
                action=last.action.value,
                resource_type=last.resource_type,
                resource_id=last.resource_id,
                patient_id=last.patient_id,
                accessed_at=str(last.accessed_at),
            )

        new_log_id = str(uuid.uuid4())
        
        if prev_hash is None:
            # Genesis condition: ensure no rows exist at all
            condition = ~exists().where(AccessLog.log_id != None)
        else:
            # Normal condition: ensure no row has already appended to this prev_hash
            condition = ~exists().where(AccessLog.prev_hash == prev_hash)

        sel = select(
            literal(new_log_id).label("log_id"),
            literal(user_id).label("user_id"),
            literal(patient_id).label("patient_id"),
            literal(resource_type).label("resource_type"),
            literal(resource_id).label("resource_id"),
            literal(action.value).label("action"),
            literal(ip_address).label("ip_address"),
            literal(prev_hash).label("prev_hash")
        ).where(condition)

        stmt = insert(AccessLog).from_select(
            ["log_id", "user_id", "patient_id", "resource_type", "resource_id", "action", "ip_address", "prev_hash"],
            sel
        )

        res = db.execute(stmt)
        if res.rowcount > 0:
            # Successfully inserted. Fetch and return the ORM object so callers can use it.
            return db.query(AccessLog).filter(AccessLog.log_id == new_log_id).one()

    raise RuntimeError("Failed to write access log due to high concurrency. Hash chain advanced too rapidly.")
