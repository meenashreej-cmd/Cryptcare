"""
Secure file upload handling for healthcare documents.

Provides comprehensive security controls for file uploads:
- MIME type validation and verification
- File size limits
- Virus scanning capability
- Malicious filename protection
- Content validation for medical documents
"""

import hashlib
import mimetypes
import os
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from fastapi import File, HTTPException, UploadFile
from fastapi.responses import FileResponse

# Allowed MIME types for healthcare documents
ALLOWED_MIME_TYPES = {
    # Medical images
    "image/jpeg": ".jpg",
    "image/png": ".png", 
    "image/tiff": ".tiff",  # Medical imaging standard
    "application/dicom": ".dcm",  # DICOM medical images
    
    # Medical documents
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",  # Lab results, data exports
    
    # Medical data formats
    "application/hl7-v2": ".hl7",  # HL7 medical data
    "application/fhir+json": ".json",  # FHIR medical records
    "application/json": ".json",
}

# File size limits by type (in bytes)
FILE_SIZE_LIMITS = {
    "image/jpeg": 50 * 1024 * 1024,      # 50MB for medical images
    "image/png": 50 * 1024 * 1024,       # 50MB for medical images  
    "image/tiff": 100 * 1024 * 1024,     # 100MB for high-res medical imaging
    "application/dicom": 500 * 1024 * 1024,  # 500MB for DICOM files
    "application/pdf": 20 * 1024 * 1024,  # 20MB for documents
    "text/plain": 1 * 1024 * 1024,       # 1MB for text files
    "text/csv": 10 * 1024 * 1024,        # 10MB for lab data
    "application/hl7-v2": 5 * 1024 * 1024,   # 5MB for HL7
    "application/fhir+json": 5 * 1024 * 1024, # 5MB for FHIR
    "application/json": 5 * 1024 * 1024,  # 5MB for JSON
}

# Maximum total file size across all types
MAX_TOTAL_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# Dangerous file signatures (magic bytes) to reject
MALICIOUS_SIGNATURES = [
    b'\x4D\x5A',  # PE executable (MZ header)
    b'\x7F\x45\x4C\x46',  # ELF executable
    b'\xCA\xFE\xBA\xBE',  # Java class file
    b'\xFE\xED\xFA\xCE',  # Mach-O executable (macOS)
    b'\xCE\xFA\xED\xFE',  # Mach-O executable (macOS, different endian)
    b'PK\x03\x04',  # ZIP archive (could contain malware)
    b'Rar!',  # RAR archive
]

# Filename character allowlist (prevent directory traversal, shell injection)
SAFE_FILENAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"


class FileSecurityError(Exception):
    """Custom exception for file security violations."""
    pass


class SecureFileUpload:
    """Handles secure file upload processing for healthcare documents."""

    def __init__(self, upload_base_dir: str = "./uploads"):
        self.upload_base_dir = Path(upload_base_dir)
        self.upload_base_dir.mkdir(exist_ok=True, parents=True)

    def validate_filename(self, filename: str) -> str:
        """Validate and sanitize filename to prevent security issues."""
        if not filename:
            raise FileSecurityError("Filename cannot be empty")
        
        # Remove path components (directory traversal protection)
        filename = os.path.basename(filename)
        
        # Check for dangerous patterns
        if any(pattern in filename.lower() for pattern in ['..', '/', '\\', '|', '&', ';', '$', '`']):
            raise FileSecurityError("Filename contains dangerous characters")
        
        # Sanitize characters
        safe_chars = ''.join(c if c in SAFE_FILENAME_CHARS else '_' for c in filename)
        
        if len(safe_chars) > 255:
            # Truncate but preserve extension
            name, ext = os.path.splitext(safe_chars)
            safe_chars = name[:250-len(ext)] + ext
        
        if not safe_chars or safe_chars.startswith('.'):
            raise FileSecurityError("Invalid filename after sanitization")
        
        return safe_chars

    def validate_mime_type(self, file_content: bytes, declared_mime: str, filename: str) -> str:
        """Validate MIME type against content and allowlist."""
        # Check declared MIME type is allowed
        if declared_mime not in ALLOWED_MIME_TYPES:
            raise FileSecurityError(f"MIME type '{declared_mime}' is not allowed")
        
        # Verify MIME type matches file content (basic magic bytes check)
        detected_mime = self._detect_mime_from_content(file_content)
        
        if detected_mime and detected_mime != declared_mime:
            # Allow some common variations
            variations = {
                "image/jpeg": ["image/jpg"],
                "text/plain": ["text/csv"],  # CSV often detected as plain text
            }
            
            allowed_variations = variations.get(declared_mime, [])
            if detected_mime not in allowed_variations:
                raise FileSecurityError(
                    f"MIME type mismatch: declared '{declared_mime}' but detected '{detected_mime}'"
                )
        
        return declared_mime

    def validate_file_size(self, file_size: int, mime_type: str) -> None:
        """Validate file size against type-specific limits."""
        max_size = FILE_SIZE_LIMITS.get(mime_type, 1024 * 1024)  # Default 1MB
        
        if file_size > max_size:
            raise FileSecurityError(
                f"File too large: {file_size} bytes (max {max_size} bytes for {mime_type})"
            )
        
        if file_size > MAX_TOTAL_FILE_SIZE:
            raise FileSecurityError(f"File exceeds absolute size limit of {MAX_TOTAL_FILE_SIZE} bytes")

    def scan_for_malware(self, file_content: bytes) -> None:
        """Basic malware signature detection."""
        # Check for known malicious file signatures
        for signature in MALICIOUS_SIGNATURES:
            if file_content.startswith(signature):
                raise FileSecurityError("File contains malicious signature")
        
        # Additional content-based checks
        if b'<script' in file_content.lower():
            raise FileSecurityError("File contains potentially malicious script content")
        
        # Check for embedded executables in images/documents
        if b'This program cannot be run in DOS mode' in file_content:
            raise FileSecurityError("File contains embedded executable")

    def validate_medical_content(self, file_content: bytes, mime_type: str) -> None:
        """Validate medical document content structure."""
        if mime_type == "application/pdf":
            # Basic PDF validation
            if not file_content.startswith(b'%PDF-'):
                raise FileSecurityError("Invalid PDF file structure")
            
            # Check for JavaScript in PDF (security risk)
            if b'/JavaScript' in file_content or b'/JS' in file_content:
                raise FileSecurityError("PDF contains JavaScript (security risk)")
        
        elif mime_type.startswith("image/"):
            # Basic image validation - ensure it's not a disguised executable
            if b'MZ' in file_content[:1024]:  # PE header in image
                raise FileSecurityError("Image file contains executable code")
        
        elif mime_type == "text/csv":
            # Basic CSV validation
            try:
                # Check if content looks like CSV
                content_str = file_content.decode('utf-8', errors='ignore')
                lines = content_str.split('\n')[:10]  # Check first 10 lines
                
                for line in lines:
                    if line.strip() and not all(c.isprintable() or c.isspace() for c in line):
                        raise FileSecurityError("CSV contains non-printable characters")
            except UnicodeDecodeError:
                raise FileSecurityError("CSV file encoding is invalid")

    def _detect_mime_from_content(self, file_content: bytes) -> Optional[str]:
        """Detect MIME type from file content magic bytes."""
        if file_content.startswith(b'\xFF\xD8\xFF'):
            return "image/jpeg"
        elif file_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif file_content.startswith(b'%PDF-'):
            return "application/pdf"
        elif file_content.startswith(b'II*\x00') or file_content.startswith(b'MM\x00*'):
            return "image/tiff"
        elif file_content[:512].find(b'DICM') != -1:
            return "application/dicom"
        
        return None

    async def process_upload(
        self, 
        upload_file: UploadFile, 
        patient_id: str, 
        document_type: str = "medical_document"
    ) -> Tuple[str, str, str]:
        """
        Process and securely store uploaded file.
        
        Returns:
            Tuple of (file_id, stored_filename, file_hash)
        """
        # Read file content
        file_content = await upload_file.read()
        
        if not file_content:
            raise FileSecurityError("Empty file uploaded")
        
        # Validate filename
        safe_filename = self.validate_filename(upload_file.filename or "document")
        
        # Validate MIME type
        declared_mime = upload_file.content_type or "application/octet-stream"
        validated_mime = self.validate_mime_type(file_content, declared_mime, safe_filename)
        
        # Validate file size
        self.validate_file_size(len(file_content), validated_mime)
        
        # Security scans
        self.scan_for_malware(file_content)
        self.validate_medical_content(file_content, validated_mime)
        
        # Generate secure file ID and path
        file_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Create patient-specific directory
        patient_dir = self.upload_base_dir / patient_id
        patient_dir.mkdir(exist_ok=True, mode=0o755)
        
        # Generate stored filename with extension matching MIME type
        extension = ALLOWED_MIME_TYPES[validated_mime]
        stored_filename = f"{file_id}_{document_type}{extension}"
        file_path = patient_dir / stored_filename
        
        # Write file securely
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Set restrictive permissions
        os.chmod(file_path, 0o644)
        
        return file_id, stored_filename, file_hash

    def get_file_path(self, patient_id: str, stored_filename: str) -> Path:
        """Get the full path for a stored file."""
        file_path = self.upload_base_dir / patient_id / stored_filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {stored_filename}")
        
        # Security check: ensure path is within upload directory
        if not str(file_path.resolve()).startswith(str(self.upload_base_dir.resolve())):
            raise FileSecurityError("Invalid file path (directory traversal attempt)")
        
        return file_path

    def create_secure_download(self, patient_id: str, stored_filename: str) -> FileResponse:
        """Create a secure file download response."""
        file_path = self.get_file_path(patient_id, stored_filename)
        
        # Determine MIME type from extension
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
            mime_type = "application/octet-stream"
        
        # Create secure headers
        headers = {
            "Content-Disposition": f'attachment; filename="{os.path.basename(stored_filename)}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache"
        }
        
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            headers=headers
        )

    def delete_file(self, patient_id: str, stored_filename: str) -> None:
        """Securely delete a stored file."""
        file_path = self.get_file_path(patient_id, stored_filename)
        
        # Secure deletion (overwrite before delete for sensitive medical data)
        file_size = file_path.stat().st_size
        with open(file_path, 'r+b') as f:
            f.write(b'\x00' * file_size)
            f.flush()
            os.fsync(f.fileno())
        
        file_path.unlink()


# Global instance for the application
secure_file_handler = SecureFileUpload()


# FastAPI dependency for file upload validation
async def validate_uploaded_file(file: UploadFile = File(...)) -> UploadFile:
    """FastAPI dependency to validate uploaded files."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Basic filename validation
    try:
        secure_file_handler.validate_filename(file.filename)
    except FileSecurityError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {e}")
    
    # MIME type validation
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        allowed_types = ", ".join(ALLOWED_MIME_TYPES.keys())
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed types: {allowed_types}"
        )
    
    return file