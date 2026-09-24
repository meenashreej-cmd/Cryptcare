"""
Phase 3 — Laboratory Management.

Implements: create_lab_test_request, start_processing, upload_report, get_report.

Extension: upload_report now accepts a document_type and uses secure file 
handling with comprehensive security validation including MIME type verification,
malware scanning, and secure storage.
"""

import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.encryption import decrypt, encrypt
from app.core.file_security import secure_file_handler, FileSecurityError
from app.core.rbac import CurrentUser
from app.models.audit import AccessActionEnum, AccessLog
from app.models.lab import LabRequestStatusEnum, LabTestRequest
from app.models.notification import NotificationTypeEnum
from app.models.vault import DocumentTypeEnum, LabReport
from app.schemas.lab import LabTestRequestCreate
from app.services import notification_service
from app.services.access_control import check_vault_access
_ALLOWED_EXTENSIONS: dict[DocumentTypeEnum, set[str]] = {
    DocumentTypeEnum.MRI: {".dcm", ".jpg", ".jpeg", ".png"},
    DocumentTypeEnum.CT_SCAN: {".dcm", ".jpg", ".jpeg", ".png"},
    DocumentTypeEnum.XRAY: {".dcm", ".jpg", ".jpeg", ".png"},
    DocumentTypeEnum.PDF_REPORT: {".pdf"},
    DocumentTypeEnum.LAB_SUMMARY: {".pdf", ".txt", ".csv"},
    DocumentTypeEnum.OTHER: set(),  # no extension restriction
}
_ALLOWED_MIME_TYPES: dict[DocumentTypeEnum, set[str]] = {
    DocumentTypeEnum.MRI: {"application/dicom", "image/jpeg", "image/png"},
    DocumentTypeEnum.CT_SCAN: {"application/dicom", "image/jpeg", "image/png"},
    DocumentTypeEnum.XRAY: {"application/dicom", "image/jpeg", "image/png"},
    DocumentTypeEnum.PDF_REPORT: {"application/pdf"},
    DocumentTypeEnum.LAB_SUMMARY: {"application/pdf", "text/plain", "text/csv"},
    DocumentTypeEnum.OTHER: set(),  # no restriction
}


from app.core.audit import write_access_log as _write_access_log_shared


def _write_access_log(db, user_id, resource_type, resource_id, action, patient_id=None):
    return _write_access_log_shared(
        db, user_id=user_id, resource_type=resource_type,
        action=action, resource_id=resource_id, patient_id=patient_id,
    )


def _resolve_user_id_for_patient(db: Session, patient_id: str) -> str | None:
    from app.models.user import PatientProfile
    profile = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    return profile.user_id if profile else None


def create_lab_test_request(db: Session, current_user: CurrentUser, payload: LabTestRequestCreate) -> LabTestRequest:
    if current_user.role not in ("DOCTOR", "PATIENT"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors and patients can request lab tests")

    if not check_vault_access(db, current_user, payload.patient_id, "lab_requests", "write"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active consent to request lab tests for this patient")

    doctor_id = None
    if current_user.role == "DOCTOR":
        from app.models.user import DoctorProfile
        doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not doctor_profile:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Doctor profile not found")
        doctor_id = doctor_profile.doctor_id

    request = LabTestRequest(
        patient_id=payload.patient_id,
        doctor_id=doctor_id,
        test_name=payload.test_name,
        status=LabRequestStatusEnum.REQUESTED,
    )
    db.add(request)
    _write_access_log(db, current_user.id, "lab_test_requests", None, AccessActionEnum.WRITE, patient_id=payload.patient_id)
    db.commit()
    db.refresh(request)
    return request


def start_processing(db: Session, current_user: CurrentUser, request_id: str) -> LabTestRequest:
    if current_user.role != "LAB":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only lab staff can begin processing a request")

    from app.models.user import LabProfile
    lab_profile = db.query(LabProfile).filter(LabProfile.user_id == current_user.id).first()
    if not lab_profile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lab profile not found")

    request = db.query(LabTestRequest).filter(LabTestRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lab test request not found")
    if request.status != LabRequestStatusEnum.REQUESTED:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request is already {request.status.value}")

    updated_count = db.query(LabTestRequest).filter(
        LabTestRequest.request_id == request_id,
        LabTestRequest.status == LabRequestStatusEnum.REQUESTED
    ).update({
        "status": LabRequestStatusEnum.IN_PROGRESS,
        "assigned_lab_id": lab_profile.lab_id
    })
    
    if updated_count == 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Request was concurrently claimed by another lab technician")

    _write_access_log(db, current_user.id, "lab_test_requests", request_id, AccessActionEnum.WRITE, patient_id=request.patient_id)
    db.commit()
    db.refresh(request)
    return request


def _validate_upload(file: UploadFile, document_type: DocumentTypeEnum, raw_bytes: bytes) -> None:
    if file.filename:
        if "/" in file.filename or "\\" in file.filename or ".." in file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename")

    if len(raw_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {_MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit for {document_type.value}",
        )

    allowed = _ALLOWED_EXTENSIONS.get(document_type, set())
    if allowed:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in allowed:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"File extension '{ext}' is not allowed for document_type={document_type.value}. Allowed: {sorted(allowed)}",
            )

    allowed_mimes = _ALLOWED_MIME_TYPES.get(document_type, set())
    if allowed_mimes:
        if file.content_type not in allowed_mimes:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"MIME type '{file.content_type}' is not allowed for document_type={document_type.value}. Allowed: {sorted(allowed_mimes)}",
            )


def _store_encrypted_file(file: UploadFile, document_type: DocumentTypeEnum, aad: str | None = None) -> tuple[str, int]:
    raw_bytes = file.file.read()
    _validate_upload(file, document_type, raw_bytes)

    # Encrypt file bytes at rest; store only the encrypted blob + a random filename.
    encrypted_blob = encrypt(raw_bytes.decode("latin1"), aad=aad)  # simple reversible byte<->str mapping for the demo
    file_name = f"{uuid.uuid4()}.enc"
    file_path = os.path.join(_REPORT_STORAGE_DIR, file_name)
    with open(file_path, "w") as f:
        f.write(encrypted_blob)
    return file_path, len(raw_bytes)


async def upload_report(
    db: Session,
    current_user: CurrentUser,
    request_id: str,
    file: UploadFile,
    summary_text: str,
    document_type: DocumentTypeEnum = DocumentTypeEnum.LAB_SUMMARY,
) -> LabReport:
    if current_user.role != "LAB":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only lab staff can upload reports")

    request = db.query(LabTestRequest).filter(LabTestRequest.request_id == request_id).first()
    if not request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lab test request not found")

    if request.status != LabRequestStatusEnum.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Request must be IN_PROGRESS before a lab can upload a report")

    from app.models.user import LabProfile
    lab_profile = db.query(LabProfile).filter(LabProfile.user_id == current_user.id).first()
    if not lab_profile or request.assigned_lab_id != lab_profile.lab_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is assigned to a different lab technician")

    # Secure file processing
    try:
        file_id, stored_filename, file_hash = await secure_file_handler.process_upload(
            file, request.patient_id, f"lab_report_{document_type.value}"
        )
    except FileSecurityError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File security validation failed: {e}")

    report = LabReport(
        patient_id=request.patient_id,
        lab_test_request_id=request.request_id,
        document_type=document_type,
        uploaded_by=current_user.id,
        file_size_bytes=0,
    )
    db.add(report)
    db.flush()

    # Encrypt file metadata for database storage
    file_path_aad = f"cryptcare:v2|lab_reports|{report.report_id}|file_path_encrypted|{request.patient_id}"
    file_path_encrypted = encrypt(stored_filename, aad=file_path_aad)
    
    summary_aad = f"cryptcare:v2|lab_reports|{report.report_id}|report_summary_encrypted|{request.patient_id}"
    summary_ct = encrypt(summary_text, aad=summary_aad)
    
    filename_aad = f"cryptcare:v2|lab_reports|{report.report_id}|original_filename_encrypted|{request.patient_id}"
    filename_ct = encrypt(file.filename or "", aad=filename_aad) if file.filename else None

    # Store encrypted metadata and file hash
    report.original_filename_encrypted = filename_ct
    report.file_path_encrypted = file_path_encrypted
    report.report_summary_encrypted = summary_ct
    # Store file hash for integrity verification
    setattr(report, 'file_hash', file_hash)  # Add this field to model if needed
    
    request.status = LabRequestStatusEnum.COMPLETED
    _write_access_log(db, current_user.id, "lab_reports", None, AccessActionEnum.WRITE, patient_id=request.patient_id)
    db.commit()
    db.refresh(report)

    notification_service.create_notification(
        db,
        recipient_id=_resolve_user_id_for_patient(db, request.patient_id),
        notif_type=NotificationTypeEnum.LAB_RESULT,
        message=f"Your {document_type.value.replace('_', ' ').title()} result is ready to view",
        resource_type="lab_reports",
        resource_id=report.report_id,
    )
    db.commit()
    return report


def get_report(db: Session, current_user: CurrentUser, report_id: str) -> LabReport:
    report = db.query(LabReport).filter(LabReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lab report not found")

    request = db.query(LabTestRequest).filter(LabTestRequest.request_id == report.lab_test_request_id).first()

    is_requesting_doctor = current_user.role == "DOCTOR" and request and current_user.id == request.doctor_id
    has_consent = check_vault_access(db, current_user, report.patient_id, "lab_reports", "read")

    if not (is_requesting_doctor or has_consent):
        _write_access_log(db, current_user.id, "lab_reports", report_id, AccessActionEnum.DENIED, patient_id=report.patient_id)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this report")

    _write_access_log(db, current_user.id, "lab_reports", report_id, AccessActionEnum.READ, patient_id=report.patient_id)
    db.commit()

    summary_aad = f"cryptcare:v2|lab_reports|{report.report_id}|report_summary_encrypted|{report.patient_id}"
    summary_decrypted = decrypt(report.report_summary_encrypted, aad=summary_aad)
    db.expunge(report)
    report.report_summary_encrypted = summary_decrypted
    return report


def get_lab_requests(
    db: Session, 
    current_user: CurrentUser, 
    status_filter: LabRequestStatusEnum | None = None,
    skip: int = 0,
    limit: int = 50
) -> list[dict]:
    if current_user.role != "LAB":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only lab staff can view the queue")
    
    from app.models.consent import ConsentRequest, ConsentStatusEnum, ResourceTypeEnum
    
    active_consents = db.query(ConsentRequest.patient_id).filter(
        ConsentRequest.grantee_id == current_user.id,
        ConsentRequest.resource_type.in_([ResourceTypeEnum.LAB_REQUESTS, ResourceTypeEnum.ALL]),
        ConsentRequest.status == ConsentStatusEnum.ACTIVE
    ).subquery()
    
    query = db.query(LabTestRequest).filter(LabTestRequest.patient_id.in_(active_consents))
    if status_filter:
        query = query.filter(LabTestRequest.status == status_filter)
        
    requests = query.order_by(LabTestRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    _write_access_log(db, current_user.id, "lab_test_requests_queue", None, AccessActionEnum.READ)
    db.commit()
    
    return [
        {
            "request_id": r.request_id,
            "patient_id": r.patient_id,
            "test_name": r.test_name,
            "status": r.status,
            "created_at": r.created_at
        }
        for r in requests
    ]
