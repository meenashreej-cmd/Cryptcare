"""
Phase 4 extension — notification creation and retrieval.

See app/models/notification.py for the "event-driven, poll-based for now"
scope note. This module is called from other services (consent_service,
vault_service, lab_service) whenever a notification-worthy event happens —
it never queries for events itself.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.models.notification import Notification, NotificationTypeEnum


def create_notification(
    db: Session,
    recipient_id: str | None,
    notif_type: NotificationTypeEnum,
    message: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> Notification | None:
    """
    Adds a Notification row to the current session WITHOUT committing —
    callers are expected to be mid-transaction already (e.g. right after
    creating the prescription/report/consent row that triggered this) and
    commit once, together. Returns None (and logs nothing) if recipient_id
    couldn't be resolved, rather than raising — a missing notification
    recipient shouldn't block the underlying action that triggered it.
    """
    if not recipient_id:
        return None

    notification = Notification(
        recipient_id=recipient_id,
        type=notif_type,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notification)
    return notification


def list_notifications(db: Session, current_user: CurrentUser, unread_only: bool = False) -> list[Notification]:
    query = db.query(Notification).filter(Notification.recipient_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).all()


def mark_read(db: Session, current_user: CurrentUser, notification_id: str) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.notification_id == notification_id, Notification.recipient_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
