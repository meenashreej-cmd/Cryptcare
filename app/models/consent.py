"""
Phase 4 — Consent Management.

Workflow (per CryptCare's original Phase 4 spec): a DOCTOR or LAB requests
access to a patient's records; the patient approves or rejects; approved
grants are time-limited via `expires_at`. Resource/permission typing below
follows the richer structured schema (enums, not a free-form JSON scope)
so `check_vault_access()` can validate a request precisely instead of
string-matching a loosely-shaped blob.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConsentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"    # requested, awaiting patient decision
    ACTIVE = "ACTIVE"      # approved and currently within its validity window
    REJECTED = "REJECTED"  # patient declined the request
    EXPIRED = "EXPIRED"    # was ACTIVE, expires_at has passed
    REVOKED = "REVOKED"    # patient ended an ACTIVE grant early


class GranteeTypeEnum(str, enum.Enum):
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    LAB = "LAB"
    INSURER = "INSURER"  # Phase 9 — patient-granted, needed before an insurer can view that patient's fraud alerts
    CAREGIVER = "CAREGIVER"  # delegated family/caregiver access — patient-granted directly, no approval step


class ResourceTypeEnum(str, enum.Enum):
    PRESCRIPTIONS = "prescriptions"
    ALLERGIES = "allergies"
    VACCINATIONS = "vaccinations"
    LAB_REPORTS = "lab_reports"
    LAB_REQUESTS = "lab_requests"  # covers Phase 3's doctor -> lab test request creation
    VITALS = "vitals"  # covers Phase 6's nurse-recorded vital signs
    FRAUD_ALERTS = "fraud_alerts"  # Phase 9 — insurer's view into that patient's flagged fraud alerts
    BLOOD_REQUESTS = "blood_requests"  # Phase 11 — doctor/nurse requesting blood for a patient
    ALL = "all"


class PermissionEnum(str, enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    BOTH = "BOTH"


class ConsentRequest(Base):
    """
    One row = one grantee's access to one resource type for one patient.
    A doctor who needs both prescriptions and lab_reports access holds two
    rows, not one row with a multi-value scope — this keeps each grant
    independently approvable, revocable, and auditable.
    """

    __tablename__ = "consent_requests"
    __table_args__ = (
        Index("ix_consent_patient_status", "patient_id", "status"),
        Index("ix_consent_grantee_status", "grantee_id", "status"),
    )

    consent_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    grantee_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    grantee_type: Mapped[GranteeTypeEnum] = mapped_column(Enum(GranteeTypeEnum), nullable=False)
    resource_type: Mapped[ResourceTypeEnum] = mapped_column(Enum(ResourceTypeEnum), nullable=False)
    permission: Mapped[PermissionEnum] = mapped_column(Enum(PermissionEnum), nullable=False)
    status: Mapped[ConsentStatusEnum] = mapped_column(Enum(ConsentStatusEnum), default=ConsentStatusEnum.PENDING, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # set on approval, null while PENDING
    # True only for emergency override grants (see consent_service.break_glass_access).
    # Does NOT change how check_vault_access() evaluates the row — an ACTIVE
    # break-glass row grants access exactly like any other ACTIVE row. This
    # flag exists purely so break-glass events are distinguishable in the
    # audit trail and timeline, and so the mandatory patient notification
    # knows to use different (more urgent) copy.
    is_break_glass: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_delegation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
