"""
Phase 4 extension — real-time notifications for consent requests,
prescriptions, lab results, and (future Phase 9) insurance updates.

"Real-time" here means event-driven at write time (created the instant the
triggering event happens), not push-delivered — actual device push (FCM/APNs)
is out of scope for this backend increment and would sit behind this table
as a delivery mechanism, same relationship OTP-to-console has to OTP-to-SMS.
Clients poll GET /notifications; a WebSocket/push layer can be added later
without changing this table's shape.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationTypeEnum(str, enum.Enum):
    CONSENT_REQUEST = "CONSENT_REQUEST"          # doctor/lab asked for access
    CONSENT_DECISION = "CONSENT_DECISION"        # patient's own approve/reject/revoke, echoed back for their record
    BREAK_GLASS_ALERT = "BREAK_GLASS_ALERT"      # mandatory post-event disclosure of an emergency access
    PRESCRIPTION = "PRESCRIPTION"                # new prescription issued
    LAB_RESULT = "LAB_RESULT"                    # lab report ready
    INSURANCE_UPDATE = "INSURANCE_UPDATE"        # reserved for Phase 9 — no producer yet
    PHARMACY_ACCESS = "PHARMACY_ACCESS"
    EMERGENCY_QR_ACCESS = "EMERGENCY_QR_ACCESS"
    BLOOD_REQUEST_UPDATE = "BLOOD_REQUEST_UPDATE"  # Phase 11 — blood request fulfilled/rejected


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_recipient_read", "recipient_id", "is_read"),)

    notification_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False)
    type: Mapped[NotificationTypeEnum] = mapped_column(Enum(NotificationTypeEnum), nullable=False)
    # Reference only — resource_type + resource_id, never the record's own
    # content, so a notification payload can't leak PHI to a lock screen or
    # a client-side notification store the way the record itself would.
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
