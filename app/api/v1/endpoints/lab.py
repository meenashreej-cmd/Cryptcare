from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.vault import DocumentTypeEnum
from app.models.lab import LabRequestStatusEnum
from app.schemas.lab import LabReportResponse, LabTestRequestCreate, LabTestRequestResponse, LabQueueItemResponse
from app.services import lab_service

router = APIRouter(prefix="/lab", tags=["Phase 3 — Laboratory"])

@router.get("/requests", response_model=list[LabQueueItemResponse])
def get_lab_requests(
    status_filter: LabRequestStatusEnum | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return lab_service.get_lab_requests(db, current_user, status_filter, skip, limit)


@router.post("/requests", response_model=LabTestRequestResponse, status_code=201)
def create_request(
    payload: LabTestRequestCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return lab_service.create_lab_test_request(db, current_user, payload)


@router.put("/requests/{request_id}/start", response_model=LabTestRequestResponse)
def start_processing(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return lab_service.start_processing(db, current_user, request_id)


@router.post("/requests/{request_id}/report", response_model=LabReportResponse, status_code=201)
def upload_report(
    request_id: str,
    summary_text: str = Form(...),
    document_type: DocumentTypeEnum = Form(DocumentTypeEnum.LAB_SUMMARY),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    report = lab_service.upload_report(db, current_user, request_id, file, summary_text, document_type)
    return LabReportResponse(
        report_id=report.report_id,
        patient_id=report.patient_id,
        lab_test_request_id=report.lab_test_request_id,
        document_type=report.document_type,
        file_size_bytes=report.file_size_bytes,
        summary=None,  # not re-decrypted here; fetch via GET /lab/reports/{id} to view
        uploaded_by=report.uploaded_by,
        uploaded_at=report.uploaded_at,
    )


@router.get("/reports/{report_id}", response_model=LabReportResponse)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    report = lab_service.get_report(db, current_user, report_id)
    return LabReportResponse(
        report_id=report.report_id,
        patient_id=report.patient_id,
        lab_test_request_id=report.lab_test_request_id,
        document_type=report.document_type,
        file_size_bytes=report.file_size_bytes,
        summary=report.report_summary_encrypted,  # decrypted upstream in the service layer
        uploaded_by=report.uploaded_by,
        uploaded_at=report.uploaded_at,
    )
