import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    claim_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # CRITICAL: Linking directly to the profile IDs, NOT the users.user_id,
    # to maintain strict foreign key integrity and prevent ID mismatch bugs.
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False)
    insurer_id: Mapped[str] = mapped_column(String(36), ForeignKey("insurer_profiles.insurer_id", ondelete="CASCADE"), nullable=False)
    
    # Reference to the clinical document (e.g. "prescriptions" or "lab_reports") and its ID.
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    status: Mapped[ClaimStatusEnum] = mapped_column(Enum(ClaimStatusEnum), default=ClaimStatusEnum.PENDING, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
