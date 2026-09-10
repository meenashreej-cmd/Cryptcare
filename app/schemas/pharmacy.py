from datetime import datetime
from pydantic import BaseModel, Field


class QRVerifyRequest(BaseModel):
    qr_payload: str = Field(..., description="The base64 encoded JWT QR code string")


class DispenseRequest(BaseModel):
    qr_payload: str = Field(
        ...,
        description=(
            "The same QR payload scanned in verify-qr. Re-submitted here so the "
            "dispense endpoint can independently re-verify the Ed25519/HMAC "
            "signature immediately before marking the prescription DISPENSED, "
            "rather than trusting whatever verify-qr returned earlier."
        ),
    )


class PrescriptionItemSchema(BaseModel):
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration_days: int | None = None

    class Config:
        from_attributes = True


class QRVerifyResponse(BaseModel):
    prescription_id: str
    patient_id: str
    doctor_id: str
    status: str
    diagnosis: str | None = None
    notes: str | None = None
    items: list[PrescriptionItemSchema]
    verified: bool = Field(..., description="True if the Ed25519 signature is valid")
    message: str | None = None


class DispenseResponse(BaseModel):
    dispense_id: str
    prescription_id: str
    pharmacist_id: str
    status: str
    dispensed_at: datetime
    message: str
