from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.models.fraud import FraudAlert
from app.schemas.fraud import FraudAlertListResponse, FraudAlertResponse, FraudAlertAdminResponse, FraudAlertReviewRequest
from app.services import fraud_service

router = APIRouter(prefix="/fraud", tags=["Phase 9 — Fraud Detection"])


def _to_response(alert: FraudAlert, is_admin: bool = False) -> FraudAlertResponse | FraudAlertAdminResponse:
    if is_admin:
        from app.schemas.fraud import FraudAlertAdminResponse
        return FraudAlertAdminResponse(
            alert_id=alert.alert_id,
            category=alert.category,
            severity=alert.severity,
            status=alert.status,
            counts=alert.counts,
            related_entity_type=alert.related_entity_type,
            related_resource_ids=(alert.related_resource_ids or "").split(",") if alert.related_resource_ids else [],
            detected_at=alert.detected_at,
            reviewed_by=alert.reviewed_by,
            reviewed_at=alert.reviewed_at,
        )
    return FraudAlertResponse(
        alert_id=alert.alert_id,
        patient_id=alert.patient_id,
        category=alert.category,
        severity=alert.severity,
        status=alert.status,
        counts=alert.counts,
        related_entity_type=alert.related_entity_type,
        encrypted_context=alert.encrypted_context,
        related_resource_ids=(alert.related_resource_ids or "").split(",") if alert.related_resource_ids else [],
        detected_at=alert.detected_at,
        reviewed_by=alert.reviewed_by,
        reviewed_at=alert.reviewed_at,
    )


from app.schemas.fraud import FraudAlertAdminListResponse
from app.models.fraud import FraudAlertStatusEnum

@router.get("/alerts", response_model=FraudAlertAdminListResponse)
def list_all_alerts(
    status: FraudAlertStatusEnum | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """
    ADMIN sees the global queue of alerts (sanitized view: no patient_id).
    """
    rows, total_count = fraud_service.list_all_alerts(db, current_user, status, skip, limit)
    return FraudAlertAdminListResponse(
        alerts=[_to_response(r, is_admin=True) for r in rows],
        total=total_count,
        skip=skip,
        limit=limit
    )


@router.get("/alerts/{patient_id}", response_model=FraudAlertListResponse)
def list_alerts(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT")),
):
    """
    PATIENT sees their own alerts unconditionally. 
    (ADMIN must use the global /alerts queue or a justified access flow)
    """
    rows = fraud_service.list_alerts_for_patient(db, current_user, patient_id)
    return FraudAlertListResponse(alerts=[_to_response(r, is_admin=False) for r in rows])


@router.put("/alerts/{alert_id}/review", response_model=FraudAlertAdminResponse)
def review_alert(
    alert_id: str,
    payload: FraudAlertReviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("ADMIN")),
):
    """Mark an OPEN alert as REVIEWED (confirmed, action taken elsewhere) or DISMISSED (false positive)."""
    alert = fraud_service.review_alert(db, current_user, alert_id, payload.status)
    return _to_response(alert, is_admin=True)
