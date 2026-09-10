import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabRequestStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LabTestRequest(Base):
    __tablename__ = "lab_test_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctor_profiles.doctor_id"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[LabRequestStatusEnum] = mapped_column(Enum(LabRequestStatusEnum), default=LabRequestStatusEnum.REQUESTED)
    assigned_lab_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
