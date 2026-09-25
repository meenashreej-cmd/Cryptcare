"""
Audit / Access Log model.

Phase 3 — hash-chain:
  AccessLog.prev_hash stores a SHA-256 digest of the previous log entry's
  canonical representation, forming a tamper-evident append-only chain.
  Any row that has prev_hash=NULL is the genesis entry (or the first entry
  after a DB reset). Verifying the chain means walking the table in
  log_id-insertion order and checking that each row's prev_hash equals
  SHA-256(prev row's canonical string).

  Canonical string for hashing: "<log_id>|<user_id>|<action>|<resource_type>|<resource_id>|<patient_id>|<accessed_at>"
  — same fields that would appear in a compliance export, excluding
  ip_address (which may be absent/anonymised in some deployments).
"""

import enum
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccessActionEnum(str, enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    DENIED = "DENIED"
    CONSENT_REQUESTED = "CONSENT_REQUESTED"
    CONSENT_APPROVED = "CONSENT_APPROVED"
    CONSENT_REJECTED = "CONSENT_REJECTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_EXPIRED = "CONSENT_EXPIRED"
    BREAK_GLASS_ACCESS = "BREAK_GLASS_ACCESS"
    CAREGIVER_GRANTED = "CAREGIVER_GRANTED"
    PHARMACY_ACCESS = "PHARMACY_ACCESS"
    EMERGENCY_QR_ACCESS = "EMERGENCY_QR_ACCESS"
    NURSE_ASSIGNED = "NURSE_ASSIGNED"
    NURSE_REMOVED = "NURSE_REMOVED"
    AUTH_LOGIN = "AUTH_LOGIN"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_PASSWORD_CHANGED = "AUTH_PASSWORD_CHANGED"
    AUTH_MFA_ENROLLED = "AUTH_MFA_ENROLLED"
    AUTH_SUSPICIOUS = "AUTH_SUSPICIOUS"


def _canonical(log_id: str, user_id: str | None, action: str,
               resource_type: str, resource_id: str | None,
               patient_id: str | None, accessed_at: str) -> str:
    """Deterministic string used as hash input for the chain."""
    return (
        f"{log_id}|{user_id or ''}|{action}|{resource_type}"
        f"|{resource_id or ''}|{patient_id or ''}|{accessed_at}"
    )


def compute_entry_hash(
    log_id: str,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    patient_id: str | None,
    accessed_at: str,
) -> str:
    """SHA-256 of this entry's canonical string — stored as the *next* entry's prev_hash."""
    raw = _canonical(log_id, user_id, action, resource_type, resource_id, patient_id, accessed_at)
    return hashlib.sha256(raw.encode()).hexdigest()


class AccessLog(Base):
    __tablename__ = "access_logs"

    log_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.user_id"), nullable=True
    )
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patient_profiles.patient_id"), nullable=True
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[AccessActionEnum] = mapped_column(Enum(AccessActionEnum), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    from sqlalchemy.dialects.mysql import DATETIME as MySQL_DATETIME
    accessed_at: Mapped[datetime] = mapped_column(MySQL_DATETIME(fsp=6), server_default=func.now(6))
    # Hash-chain: SHA-256 digest of the previous log entry's canonical fields.
    # NULL on the first (genesis) entry. Allows offline chain verification.
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
