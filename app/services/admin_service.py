from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.rbac import CurrentUser
from app.models.user import RoleEnum, User, UserStatusEnum


def get_pending_verifications(db: Session, current_user: CurrentUser) -> list[User]:
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can view pending verifications.")
    
    return db.query(User).filter(
        User.status == UserStatusEnum.PENDING_VERIFICATION
    ).order_by(User.created_at.asc()).all()
