from datetime import datetime
from pydantic import BaseModel
from typing import Dict

from app.models.audit import AccessActionEnum


class AuditLogResponse(BaseModel):
    log_id: str
    user_id: str | None
    patient_id: str | None
    resource_type: str
    resource_id: str | None
    action: AccessActionEnum
    ip_address: str | None
    accessed_at: datetime

    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    action_counts: Dict[str, int]
    total_logs: int


class TrustLedgerEntry(BaseModel):
    id: str
    tag: str
    event: str
    hash: str
    timestamp: str
    formatted_text: str


class TrustLedgerResponse(BaseModel):
    entries: list[TrustLedgerEntry]
    chain_tip_hash: str | None
    total_entries: int
    is_tamper_free: bool

