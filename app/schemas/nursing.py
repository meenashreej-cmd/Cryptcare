from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.consent import PermissionEnum, ResourceTypeEnum


class VitalSignCreateRequest(BaseModel):
    patient_id: str = Field(..., description="PatientProfile.patient_id this observation is for")
    heart_rate_bpm: Optional[int] = Field(None, ge=0, le=350)
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=200)
    temperature_celsius: Optional[float] = Field(None, ge=25.0, le=45.0)
    respiratory_rate: Optional[int] = Field(None, ge=0, le=100)
    spo2_percent: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=2000)


class VitalSignResponse(BaseModel):
    vital_id: str
    patient_id: str
    recorded_by: str
    heart_rate_bpm: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    temperature_celsius: Optional[float] = None
    respiratory_rate: Optional[int] = None
    spo2_percent: Optional[int] = None
    notes: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class VitalSignListResponse(BaseModel):
    vitals: list[VitalSignResponse]


class NurseAssignmentRequest(BaseModel):
    patient_id: str
    nurse_id: str
    resource_type: ResourceTypeEnum
    permission: PermissionEnum


class NurseAssignmentResponse(BaseModel):
    assignment_id: str
    patient_id: str
    doctor_id: str
    nurse_id: str
    resource_type: ResourceTypeEnum
    permission: PermissionEnum
    status: str
    created_at: datetime
    removed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NurseAssignmentListResponse(BaseModel):
    assignments: list[NurseAssignmentResponse]
