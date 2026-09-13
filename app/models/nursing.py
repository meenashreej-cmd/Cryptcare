"""
Phase 6 — Nurse role: vital signs recording.

One row per observation (not one row per patient updated in place) — same
append-only-per-event reasoning as LabReport/AccessLog: a patient's vitals
history is itself clinically meaningful (trend over time), so overwriting a
previous reading would destroy data a doctor might need.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.consent import PermissionEnum, ResourceTypeEnum


class VitalSign(Base):
    __tablename__ = "vital_signs"

    vital_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    # References users.user_id directly, not nurse_profiles.nurse_id — same
    # convention as DispenseRecord.pharmacist_id and LabReport.uploaded_by.
    recorded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)

    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_pressure_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Free-text nursing observations can contain PHI narrative (symptoms,
    # patient-reported complaints) — encrypted at rest like every other
    # clinical free-text field in the vault (diagnosis, prescription notes).
    notes_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CareTeamAssignment(Base):
    __tablename__ = "care_team_assignments"

    assignment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    nurse_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    resource_type: Mapped[ResourceTypeEnum] = mapped_column(Enum(ResourceTypeEnum), nullable=False)
    permission: Mapped[PermissionEnum] = mapped_column(Enum(PermissionEnum), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
