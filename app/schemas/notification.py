from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationTypeEnum


class NotificationResponse(BaseModel):
    notification_id: str
    type: NotificationTypeEnum
    resource_type: str | None
    resource_id: str | None
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
