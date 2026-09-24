from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.vault import PrescriptionStatusEnum, SeverityEnum
from app.core.input_validation import HealthcareValidators


class PrescriptionItemInput(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=200)
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)

    @field_validator("medicine_name")
    @classmethod
    def validate_medicine_name(cls, v: str) -> str:
        return HealthcareValidators.validate_medical_text(v, "medicine name", max_length=200)

    @field_validator("dosage")
    @classmethod
    def validate_dosage_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return HealthcareValidators.validate_dosage(v)

    @field_validator("frequency")
    @classmethod
    def validate_frequency_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return HealthcareValidators.validate_medical_text(v, "frequency", max_length=100)


class PrescriptionCreateRequest(BaseModel):
    patient_id: str
    diagnosis: str = Field(min_length=1, max_length=2000)
    notes: Optional[str] = None
    items: list[PrescriptionItemInput] = Field(min_length=1)

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        return HealthcareValidators.validate_patient_id(v)

    @field_validator("diagnosis")
    @classmethod
    def validate_diagnosis_text(cls, v: str) -> str:
        return HealthcareValidators.validate_medical_text(v, "diagnosis", max_length=2000)

    @field_validator("notes")
    @classmethod
    def validate_notes_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return HealthcareValidators.validate_medical_text(v, "notes", max_length=1000)


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

    @field_validator("allergen")
    @classmethod
    def validate_allergen_text(cls, v: str) -> str:
        return HealthcareValidators.validate_medical_text(v, "allergen", max_length=150)


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

    @field_validator("vaccine_name")
    @classmethod
    def validate_vaccine_name(cls, v: str) -> str:
        return HealthcareValidators.validate_medical_text(v, "vaccine name", max_length=150)


class VaccinationResponse(BaseModel):
    vaccination_id: str
    vaccine_name: str
    date_administered: Optional[datetime]
    next_due_date: Optional[datetime]

    class Config:
        from_attributes = True
