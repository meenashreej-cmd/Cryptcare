"""
Phase 9 — Fraud Detection.

Rule-based, not ML — consistent with Phase 7's clinical safety engine (rule
logic makes determinations; nothing here is a black box). Detection runs
inline at the moment of the triggering event (prescription creation,
pharmacy signature failure, break-glass invocation) rather than as a batch
job, same pattern Phase 7 uses at prescription-creation time.

No insurance-claims model exists yet in this codebase (InsurerProfile has no
linked Claim/billing table), so this phase scopes "fraud" to the patterns the
existing data can actually support: prescribing, dispensing, and
break-glass-access behavior. A claims-fraud module can layer on top later
once a claims model exists.

Three rules, one persisted FraudAlert row each time a rule fires:

  DOCTOR_SHOPPING     — same patient obtaining prescriptions for the same
                        medicine from >=2 distinct doctors within a rolling
                        30-day window.
  PRESCRIPTION_TAMPERING — >=2 signature-verification failures (pharmacy QR
                        scan/dispense) against the same prescription_id —
                        a forged/tampered QR being retried.
  BREAK_GLASS_ABUSE   — same grantee invoking break-glass on >=3 distinct
                        patients within a rolling 24-hour window.

Alerts are patient-scoped and gated behind the same consent chokepoint as
everything else: an INSURER only sees a given patient's alerts once that
patient has granted them an ACTIVE consent (resource_type=fraud_alerts,
via the existing request/approve flow). ADMIN sees everything. This keeps
Phase 9 consistent with the patient-sovereignty thesis rather than carving
out a special "insurers see everyone's data" exception.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.vault import SeverityEnum  # reuse MILD/MODERATE/SEVERE — no need for a second severity enum


class FraudAlertCategoryEnum(str, enum.Enum):
    DOCTOR_SHOPPING = "DOCTOR_SHOPPING"
    PRESCRIPTION_TAMPERING = "PRESCRIPTION_TAMPERING"
    BREAK_GLASS_ABUSE = "BREAK_GLASS_ABUSE"


class FraudAlertStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    alert_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    category: Mapped[FraudAlertCategoryEnum] = mapped_column(Enum(FraudAlertCategoryEnum), nullable=False)
    severity: Mapped[SeverityEnum] = mapped_column(Enum(SeverityEnum), nullable=False)
    status: Mapped[FraudAlertStatusEnum] = mapped_column(
        Enum(FraudAlertStatusEnum), default=FraudAlertStatusEnum.OPEN, nullable=False
    )
    counts: Mapped[int] = mapped_column(default=1, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    encrypted_context: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Comma-joined list of related resource IDs (prescription_ids, consent_ids)
    # that triggered this alert — kept as plain text rather than a join table
    # since alerts are read-mostly and the set is small (2-5 IDs typically).
    related_resource_ids: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
