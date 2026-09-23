from datetime import datetime

from pydantic import BaseModel

from app.models.fraud import FraudAlertCategoryEnum, FraudAlertStatusEnum
from app.models.vault import SeverityEnum


class FraudAlertResponse(BaseModel):
    alert_id: str
    patient_id: str
    category: FraudAlertCategoryEnum
    severity: SeverityEnum
    status: FraudAlertStatusEnum
    counts: int
    related_entity_type: str | None
    encrypted_context: str | None
    related_resource_ids: list[str]
    detected_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class FraudAlertAdminResponse(BaseModel):
    alert_id: str
    category: FraudAlertCategoryEnum
    severity: SeverityEnum
    status: FraudAlertStatusEnum
    counts: int
    related_entity_type: str | None
    related_resource_ids: list[str]
    detected_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class FraudAlertListResponse(BaseModel):
    alerts: list[FraudAlertResponse] | list[FraudAlertAdminResponse]


class FraudAlertAdminListResponse(BaseModel):
    alerts: list[FraudAlertAdminResponse]
    total: int
    skip: int
    limit: int


class FraudAlertReviewRequest(BaseModel):
    status: FraudAlertStatusEnum  # REVIEWED or DISMISSED
