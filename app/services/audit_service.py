from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser
from app.models.audit import AccessLog
from app.models.user import RoleEnum
from fastapi import HTTPException


def get_audit_logs(db: Session, current_user: CurrentUser, skip: int = 0, limit: int = 100) -> list[AccessLog]:
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can view the full audit dashboard.")
    
    return db.query(AccessLog).order_by(AccessLog.accessed_at.desc()).offset(skip).limit(limit).all()


def get_audit_stats(db: Session, current_user: CurrentUser) -> dict:
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only admins can view audit stats.")
    
    # Group by action and count
    action_counts = db.query(
        AccessLog.action, func.count(AccessLog.log_id)
    ).group_by(AccessLog.action).all()
    
    total_logs = db.query(func.count(AccessLog.log_id)).scalar()
    
    counts_dict = {action.value: count for action, count in action_counts}
    
    return {
        "action_counts": counts_dict,
        "total_logs": total_logs
    }
