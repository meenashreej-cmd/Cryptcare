from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.vault import PrescriptionStatusEnum, SeverityEnum


class PrescriptionItemInput(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=200)
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)


class PrescriptionCreateRequest(BaseModel):
    patient_id: str
    diagnosis: str = Field(min_length=1, max_length=2000)
    notes: Optional[str] = None
    items: list[PrescriptionItemInput] = Field(min_length=1)


class PrescriptionItemResponse(BaseModel):
    item_id: str
    medicine_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    duration_days: Optional[int]

    class Config:
        from_attributes = True


class PrescriptionResponse(BaseModel):
    prescription_id: str
    patient_id: str
    doctor_id: str
    diagnosis: Optional[str] = None  # decrypted before returning
    notes: Optional[str] = None
    status: PrescriptionStatusEnum
    created_at: datetime
    items: list[PrescriptionItemResponse] = []
    # Non-blocking clinical safety findings (Phase 7) — MODERATE interactions,
    # duplicate-therapy notes, unmatched drug names. Only present when there's
    # something worth a second look; a fully clean check omits this field.
    safety_warnings: Optional[dict] = None

    class Config:
        from_attributes = True


class AllergyCreateRequest(BaseModel):
    allergen: str = Field(min_length=1, max_length=150)
    severity: SeverityEnum


class AllergyResponse(BaseModel):
    allergy_id: str
    allergen: str
    severity: SeverityEnum

    class Config:
        from_attributes = True


class VaccinationCreateRequest(BaseModel):
    vaccine_name: str = Field(min_length=1, max_length=150)
    date_administered: Optional[datetime] = None
    next_due_date: Optional[datetime] = None


class VaccinationResponse(BaseModel):
    vaccination_id: str
    vaccine_name: str
    date_administered: Optional[datetime]
    next_due_date: Optional[datetime]

    class Config:
        from_attributes = True
