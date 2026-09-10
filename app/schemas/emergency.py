from datetime import date

from pydantic import BaseModel, Field


class EmergencyContactUpdateRequest(BaseModel):
    blood_group: str | None = Field(None, max_length=5)
    emergency_contact_name: str | None = Field(None, max_length=150)
    emergency_contact_phone: str | None = Field(None, max_length=20)


class EmergencyQRStatusResponse(BaseModel):
    has_active_token: bool
    created_at: str | None = None


class EmergencyAllergyItem(BaseModel):
    allergen: str
    severity: str


class EmergencyMedicationItem(BaseModel):
    medicine_name: str
    dosage: str | None
    frequency: str | None


class EmergencyCardResponse(BaseModel):
    """
    Deliberately narrow — safety-critical fields only. Never diagnosis,
    notes, lab reports, or anything else in the vault. See
    app/models/emergency.py for the full rationale.
    """

    full_name: str
    dob: date | None
    blood_group: str | None
    allergies: list[EmergencyAllergyItem]
    current_medications: list[EmergencyMedicationItem]
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
