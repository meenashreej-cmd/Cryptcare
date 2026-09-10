"""
Phase 11 — Blood Bank.

Two entities:

  BloodUnit    — one physical unit of donated blood/component sitting in a
                 specific blood bank facility's inventory. Blood-group and
                 component fields are plaintext (same tradeoff as
                 PrescriptionItem.medicine_name in Phase 2/9 — inventory has
                 to be queryable/filterable by group and component to be
                 useful at all, and neither field is sensitive on its own).
                 Donor identity is deliberately NOT modeled here — this
                 phase is inventory + request/fulfillment, not a donor
                 registry, which would need its own consent/privacy
                 treatment and is out of scope.

  BloodRequest — a doctor/nurse asking for N units of a given group+component
                 for a specific patient. Same request -> approve/fulfill
                 shape as Phase 3's LabTestRequest. Creating a request is
                 consent-gated (resource_type=blood_requests, same chokepoint
                 as everything else); fulfilling/rejecting it is a
                 BLOOD_BANK-role action, not further consent-gated, mirroring
                 how a LAB technician can act on any assigned lab request
                 without needing their own separate patient consent grant.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BloodComponentEnum(str, enum.Enum):
    WHOLE_BLOOD = "WHOLE_BLOOD"
    PACKED_RBC = "PACKED_RBC"
    PLASMA = "PLASMA"
    PLATELETS = "PLATELETS"


class BloodUnitStatusEnum(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"   # matched to a request, not yet issued
    ISSUED = "ISSUED"       # handed over against a fulfilled request
    EXPIRED = "EXPIRED"     # lazily flipped on read, same pattern as expire_stale_consents
    DISCARDED = "DISCARDED"  # manually pulled (failed screening, damaged, etc.)


class BloodRequestUrgencyEnum(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class BloodRequestStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class BloodUnit(Base):
    __tablename__ = "blood_units"

    unit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blood_bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("blood_bank_profiles.blood_bank_id"), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=False)  # e.g. "O+", "AB-"
    component: Mapped[BloodComponentEnum] = mapped_column(Enum(BloodComponentEnum), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[BloodUnitStatusEnum] = mapped_column(Enum(BloodUnitStatusEnum), default=BloodUnitStatusEnum.AVAILABLE, nullable=False)
    reserved_for_request_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("blood_requests.request_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)  # doctor/nurse users.user_id
    blood_group: Mapped[str] = mapped_column(String(5), nullable=False)
    component: Mapped[BloodComponentEnum] = mapped_column(Enum(BloodComponentEnum), nullable=False)
    units_needed: Mapped[int] = mapped_column(Integer, nullable=False)
    urgency: Mapped[BloodRequestUrgencyEnum] = mapped_column(Enum(BloodRequestUrgencyEnum), default=BloodRequestUrgencyEnum.ROUTINE, nullable=False)
    status: Mapped[BloodRequestStatusEnum] = mapped_column(Enum(BloodRequestStatusEnum), default=BloodRequestStatusEnum.PENDING, nullable=False)
    fulfilled_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=True)  # blood_bank users.user_id
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
