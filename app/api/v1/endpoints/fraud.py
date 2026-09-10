from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, require_role
from app.db.session import get_db
from app.models.fraud import FraudAlert
from app.schemas.fraud import FraudAlertListResponse, FraudAlertResponse, FraudAlertReviewRequest
from app.services import fraud_service

router = APIRouter(prefix="/fraud", tags=["Phase 9 — Fraud Detection"])


def _to_response(alert: FraudAlert) -> FraudAlertResponse:
    return FraudAlertResponse(
        alert_id=alert.alert_id,
        patient_id=alert.patient_id,
        category=alert.category,
        severity=alert.severity,
        status=alert.status,
        description=alert.description,
        related_resource_ids=(alert.related_resource_ids or "").split(",") if alert.related_resource_ids else [],
        detected_at=alert.detected_at,
        reviewed_by=alert.reviewed_by,
        reviewed_at=alert.reviewed_at,
    )


@router.get("/alerts/{patient_id}", response_model=FraudAlertListResponse)
def list_alerts(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("PATIENT", "INSURER", "ADMIN")),
):
    """
    PATIENT sees their own alerts unconditionally. INSURER needs an ACTIVE
    consent grant (resource_type=fraud_alerts) from this patient, requested
    via POST /consent/request and approved the normal way. ADMIN sees all.
    """
    rows = fraud_service.list_alerts_for_patient(db, current_user, patient_id)
    return FraudAlertListResponse(alerts=[_to_response(r) for r in rows])


@router.put("/alerts/{alert_id}/review", response_model=FraudAlertResponse)
def review_alert(
    alert_id: str,
    payload: FraudAlertReviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("INSURER", "ADMIN")),
):
    """Mark an OPEN alert as REVIEWED (confirmed, action taken elsewhere) or DISMISSED (false positive)."""
    alert = fraud_service.review_alert(db, current_user, alert_id, payload.status)
    return _to_response(alert)
