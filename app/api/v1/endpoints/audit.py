from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.audit import AuditLogResponse, AuditStatsResponse
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["Phase 13 — Audit Dashboard"])


@router.get("/logs", response_model=list[AuditLogResponse])
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    Paginated feed of all access logs across the system.
    Restricted to ADMIN. Useful for forensic investigation and compliance audits.
    """
    return audit_service.get_audit_logs(db, current_user, skip, limit)


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    Aggregated stats for the audit landing view.
    Groups log counts by action type.
    """
    stats = audit_service.get_audit_stats(db, current_user)
    return AuditStatsResponse(**stats)
