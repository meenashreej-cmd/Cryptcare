from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.rbac import CurrentUser
from app.models.user import RoleEnum, User, UserStatusEnum


def get_pending_verifications(db: Session, current_user: CurrentUser) -> list[User]:
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can view pending verifications.")
    
    return db.query(User).filter(
        User.status == UserStatusEnum.PENDING_VERIFICATION,
        User.role != RoleEnum.PATIENT
    ).order_by(User.created_at.asc()).all()


def get_all_users(db: Session, current_user: CurrentUser) -> list[User]:
    """Get all users in the system - admin only"""
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can view all users.")
    
    return db.query(User).order_by(User.created_at.desc()).all()
