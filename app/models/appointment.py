"""
Appointment models for CryptCare.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class AppointmentStatusEnum(enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class AppointmentTypeEnum(enum.Enum):
    CONSULTATION = "CONSULTATION"
    FOLLOW_UP = "FOLLOW_UP"
    ROUTINE_CHECK = "ROUTINE_CHECK"
    EMERGENCY = "EMERGENCY"
    PROCEDURE = "PROCEDURE"
    VACCINATION = "VACCINATION"


class Appointment(Base):
    """
    Appointment between patient and doctor.
    """
    __tablename__ = "appointments"

    appointment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Appointment details
    scheduled_datetime = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(String(10), default="30")  # Default 30 minutes
    appointment_type = Column(Enum(AppointmentTypeEnum), default=AppointmentTypeEnum.CONSULTATION)
    status = Column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.SCHEDULED)
    
    # Additional information
    title = Column(String(200), nullable=True)  # Brief title/reason
    description = Column(Text, nullable=True)  # Detailed description
    location = Column(String(200), nullable=True)  # Room number, clinic name, etc.
    is_virtual = Column(Boolean, default=False)
    virtual_meeting_link = Column(String(500), nullable=True)
    
    # Notes and outcomes
    doctor_notes = Column(Text, nullable=True)  # Private doctor notes
    patient_notes = Column(Text, nullable=True)  # Patient-visible notes
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)  # Who created the appointment
    
    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], backref="patient_appointments")
    doctor = relationship("User", foreign_keys=[doctor_id], backref="doctor_appointments")
    creator = relationship("User", foreign_keys=[created_by])