from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.blood_bank import (
    BloodComponentEnum,
    BloodRequestStatusEnum,
    BloodRequestUrgencyEnum,
    BloodUnitStatusEnum,
)


class BloodUnitCreateRequest(BaseModel):
    blood_group: str = Field(..., pattern=r"^(A|B|AB|O)[+-]$")
    component: BloodComponentEnum
    collection_date: date
    expiry_date: date


class BloodUnitResponse(BaseModel):
    unit_id: str
    blood_group: str
    component: BloodComponentEnum
    collection_date: date
    expiry_date: date
    status: BloodUnitStatusEnum

    model_config = {"from_attributes": True}


class BloodInventorySummaryResponse(BaseModel):
    """Grouped counts — what a blood bank dashboard actually wants to see, not a raw unit list."""
    blood_group: str
    component: BloodComponentEnum
    available_units: int


class BloodRequestCreateRequest(BaseModel):
    patient_id: str
    blood_group: str = Field(..., pattern=r"^(A|B|AB|O)[+-]$")
    component: BloodComponentEnum
    units_needed: int = Field(..., gt=0, le=20)
    urgency: BloodRequestUrgencyEnum = BloodRequestUrgencyEnum.ROUTINE


class BloodRequestResponse(BaseModel):
    request_id: str
    patient_id: str
    requested_by: str
    blood_group: str
    component: BloodComponentEnum
    units_needed: int
    urgency: BloodRequestUrgencyEnum
    status: BloodRequestStatusEnum
    fulfilled_by: str | None
    rejection_reason: str | None
    created_at: datetime
    resolved_at: datetime | None
    matched_unit_ids: list[str] = []

    model_config = {"from_attributes": True}


class BloodRequestRejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
