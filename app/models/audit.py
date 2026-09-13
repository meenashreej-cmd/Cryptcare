import enum
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
    BREAK_GLASS_ACCESS = "BREAK_GLASS_ACCESS"  # emergency override — always paired with a patient notification
    CAREGIVER_GRANTED = "CAREGIVER_GRANTED"
    PHARMACY_ACCESS = "PHARMACY_ACCESS"
    EMERGENCY_QR_ACCESS = "EMERGENCY_QR_ACCESS"
    NURSE_ASSIGNED = "NURSE_ASSIGNED"
    NURSE_REMOVED = "NURSE_REMOVED"


class AccessLog(Base):
    __tablename__ = "access_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=True)
    # Which PATIENT this log entry concerns, when known — distinct from user_id
    # (the actor performing the action). Nullable because some log rows (e.g.
    # a doctor's own profile edit) have no associated patient. This is what
    # powers the Phase 4 patient activity timeline: "every access/action
    # concerning MY records", not "every action I personally took."
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[AccessActionEnum] = mapped_column(Enum(AccessActionEnum), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
