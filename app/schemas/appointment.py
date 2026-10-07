"""
Appointment schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.appointment import AppointmentStatusEnum, AppointmentTypeEnum


class AppointmentCreateRequest(BaseModel):
    """Request to create a new appointment"""
    patient_id: str = Field(..., min_length=36, max_length=36)
    doctor_id: str = Field(..., min_length=36, max_length=36)
    scheduled_datetime: datetime
    duration_minutes: str = "30"
    appointment_type: AppointmentTypeEnum = AppointmentTypeEnum.CONSULTATION
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=200)
    is_virtual: bool = False
    virtual_meeting_link: Optional[str] = Field(None, max_length=500)

    @field_validator("scheduled_datetime")
    @classmethod
    def validate_future_datetime(cls, v: datetime) -> datetime:
        if v <= datetime.now():
            raise ValueError("Appointment must be scheduled for a future date and time")
        return v


class AppointmentUpdateRequest(BaseModel):
    """Request to update an existing appointment"""
    scheduled_datetime: Optional[datetime] = None
    duration_minutes: Optional[str] = None
    appointment_type: Optional[AppointmentTypeEnum] = None
    status: Optional[AppointmentStatusEnum] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=200)
    is_virtual: Optional[bool] = None
    virtual_meeting_link: Optional[str] = Field(None, max_length=500)
    doctor_notes: Optional[str] = Field(None, max_length=2000)
    patient_notes: Optional[str] = Field(None, max_length=1000)


class AppointmentResponse(BaseModel):
    """Response containing appointment information"""
    appointment_id: str
    patient_id: str
    doctor_id: str
    patient_name: str
    doctor_name: str
    scheduled_datetime: datetime
    duration_minutes: str
    appointment_type: AppointmentTypeEnum
    status: AppointmentStatusEnum
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_virtual: bool
    virtual_meeting_link: Optional[str] = None
    doctor_notes: Optional[str] = None
    patient_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    """Response containing list of appointments"""
    appointments: list[AppointmentResponse]
    total: int


class AppointmentStatsResponse(BaseModel):
    """Response containing appointment statistics"""
    total_appointments: int
    scheduled: int
    confirmed: int
    completed: int
    cancelled: int
    upcoming_today: int
    upcoming_this_week: int