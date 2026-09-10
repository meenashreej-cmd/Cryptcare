from datetime import datetime
from pydantic import BaseModel, Field

from app.models.insurance import ClaimStatusEnum


class ClaimCreateRequest(BaseModel):
    insurer_id: str = Field(..., description="The ID of the insurer profile this claim is submitted to.")
    resource_type: str = Field(..., description="The type of resource this claim is for (e.g., 'prescriptions', 'lab_reports').")
    resource_id: str = Field(..., description="The ID of the resource.")
    amount: float = Field(..., description="The monetary amount claimed.", gt=0)


class ClaimStatusUpdateRequest(BaseModel):
    status: ClaimStatusEnum = Field(..., description="The new status of the claim (APPROVED or REJECTED).")


class ClaimResponse(BaseModel):
    """
    Exposes metadata only.
    Does NOT include the underlying prescription/lab report content.
    If insurers need to see actual clinical data to adjudicate, they must
    request access through the normal consent flow against the vault/lab service.
    """
    claim_id: str
    patient_id: str
    insurer_id: str
    resource_type: str
    resource_id: str
    status: ClaimStatusEnum
    amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
