import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PrescriptionStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISPENSED = "DISPENSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SeverityEnum(str, enum.Enum):
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctor_profiles.doctor_id"), nullable=False)
    diagnosis_encrypted: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    notes_encrypted: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    digital_signature: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[PrescriptionStatusEnum] = mapped_column(Enum(PrescriptionStatusEnum), default=PrescriptionStatusEnum.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["PrescriptionItem"]] = relationship(back_populates="prescription", cascade="all, delete-orphan")
    dispense_record: Mapped["DispenseRecord"] = relationship(back_populates="prescription", uselist=False)

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id: Mapped[str] = mapped_column(String(36), ForeignKey("prescriptions.prescription_id", ondelete="CASCADE"))
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prescription: Mapped["Prescription"] = relationship(back_populates="items")


class Allergy(Base):
    __tablename__ = "allergies"

    allergy_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    allergen: Mapped[str] = mapped_column(String(150), nullable=False)
    severity: Mapped[SeverityEnum] = mapped_column(Enum(SeverityEnum), nullable=False)


class Vaccination(Base):
    __tablename__ = "vaccinations"

    vaccination_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    vaccine_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date_administered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DocumentTypeEnum(str, enum.Enum):
    LAB_SUMMARY = "LAB_SUMMARY"  # default — a plain text/structured result, not a scan
    MRI = "MRI"
    CT_SCAN = "CT_SCAN"
    XRAY = "XRAY"
    PDF_REPORT = "PDF_REPORT"
    OTHER = "OTHER"


class LabReport(Base):
    __tablename__ = "lab_reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    lab_test_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("lab_test_requests.request_id"), nullable=False)
    document_type: Mapped[DocumentTypeEnum] = mapped_column(Enum(DocumentTypeEnum), default=DocumentTypeEnum.LAB_SUMMARY, nullable=False)
    original_filename_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    report_summary_encrypted: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DispenseRecord(Base):
    __tablename__ = "dispense_records"

    dispense_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id: Mapped[str] = mapped_column(String(36), ForeignKey("prescriptions.prescription_id", ondelete="CASCADE"), unique=True)
    pharmacist_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    dispensed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    prescription: Mapped["Prescription"] = relationship(back_populates="dispense_record")
