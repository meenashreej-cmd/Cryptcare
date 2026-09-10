from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.lab import LabRequestStatusEnum
from app.models.vault import DocumentTypeEnum


class LabTestRequestCreate(BaseModel):
    patient_id: str
    test_name: str = Field(min_length=1, max_length=200)


class LabTestRequestResponse(BaseModel):
    request_id: str
    patient_id: str
    doctor_id: str
    test_name: str
    status: LabRequestStatusEnum
    requested_at: datetime

    class Config:
        from_attributes = True


class LabReportUploadRequest(BaseModel):
    # file itself arrives via multipart/form-data in the endpoint,
    # this schema covers the accompanying metadata fields
    summary_text: str = Field(min_length=1, max_length=4000)
    document_type: DocumentTypeEnum = DocumentTypeEnum.LAB_SUMMARY


class LabReportResponse(BaseModel):
    report_id: str
    patient_id: str
    lab_test_request_id: str
    document_type: DocumentTypeEnum
    file_size_bytes: Optional[int] = None
    summary: Optional[str] = None  # decrypted before returning
    uploaded_by: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
