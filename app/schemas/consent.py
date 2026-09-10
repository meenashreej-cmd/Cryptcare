from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.audit import AccessActionEnum
from app.models.consent import ConsentStatusEnum, GranteeTypeEnum, PermissionEnum, ResourceTypeEnum


class ConsentRequestCreate(BaseModel):
    """Body for a DOCTOR/LAB requesting access to a patient's records."""

    patient_id: str = Field(..., description="PatientProfile.patient_id being requested")
    resource_type: ResourceTypeEnum
    permission: PermissionEnum


class ConsentApproveRequest(BaseModel):
    """Body for a PATIENT approving a pending request."""

    duration_days: int = Field(30, gt=0, le=365, description="How many days the grant stays valid from now")


class BreakGlassRequest(BaseModel):
    """Body for a DOCTOR/LAB invoking emergency break-glass access."""

    patient_id: str
    resource_type: ResourceTypeEnum
    permission: PermissionEnum
    reason: str = Field(..., min_length=10, max_length=500, description="Mandatory justification — recorded in the patient's notification and the audit log")


class CaregiverGrantRequest(BaseModel):
    """Body for a PATIENT delegating scoped access to a caregiver/family member."""

    caregiver_email: EmailStr
    resource_type: ResourceTypeEnum
    permission: PermissionEnum
    duration_days: int = Field(90, gt=0, le=365)


class ConsentResponse(BaseModel):
    consent_id: str
    patient_id: str
    grantee_id: str
    grantee_type: GranteeTypeEnum
    resource_type: ResourceTypeEnum
    permission: PermissionEnum
    status: ConsentStatusEnum
    is_break_glass: bool
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class ConsentListResponse(BaseModel):
    consents: list[ConsentResponse]


class TimelineEntryResponse(BaseModel):
    log_id: str
    patient_id: str | None
    user_id: str | None
    resource_type: str
    resource_id: str | None
    action: AccessActionEnum
    accessed_at: datetime

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    entries: list[TimelineEntryResponse]
