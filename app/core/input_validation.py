"""
Enhanced input validation for healthcare data security.

Provides strict validation patterns for medical identifiers, personal data,
and other healthcare-sensitive inputs to prevent injection attacks and 
ensure data integrity.
"""

import re
from typing import Any
from pydantic import field_validator, ValidationInfo
from fastapi import HTTPException


class HealthcareValidators:
    """Collection of strict validators for healthcare data."""

    # Medical identifier patterns (strict alphanumeric + specific separators)
    LICENSE_PATTERN = re.compile(r'^[A-Z]{1,4}-[0-9]{4,8}$')  # e.g., MD-12345, RN-123456
    MRN_PATTERN = re.compile(r'^[A-Z0-9]{6,12}$')  # Medical Record Numbers
    NPI_PATTERN = re.compile(r'^[0-9]{10}$')  # National Provider Identifier
    
    # Personal data patterns (prevent injection while allowing international names)
    NAME_PATTERN = re.compile(r'^[a-zA-ZÀ-ÿ\s\'\-\.]{1,100}$')  # Names with accents, apostrophes
    PHONE_PATTERN = re.compile(r'^\+?[0-9\s\-\(\)\.]{10,20}$')  # International phone formats
    
    # Medical content patterns
    ALLERGY_PATTERN = re.compile(r'^[a-zA-Z0-9\s\,\.\-\(\)\/]{1,200}$')  # Medical terminology
    DIAGNOSIS_PATTERN = re.compile(r'^[a-zA-Z0-9\s\,\.\-\(\)\/\:]{1,500}$')  # ICD codes, descriptions
    
    # Prevent common injection patterns
    INJECTION_PATTERNS = [
        re.compile(r'<script[^>]*>', re.IGNORECASE),  # XSS
        re.compile(r'javascript:', re.IGNORECASE),   # XSS
        re.compile(r'on\w+\s*=', re.IGNORECASE),     # Event handlers
        re.compile(r'union\s+select', re.IGNORECASE), # SQL injection
        re.compile(r'drop\s+table', re.IGNORECASE),   # SQL injection
        re.compile(r'insert\s+into', re.IGNORECASE),  # SQL injection
        re.compile(r'delete\s+from', re.IGNORECASE),  # SQL injection
        re.compile(r'\$\{.*\}'),                     # Template injection
        re.compile(r'{{.*}}'),                       # Template injection
        re.compile(r'<%.*%>'),                       # Template injection
    ]

    @classmethod
    def validate_no_injection(cls, value: str, field_name: str = "field") -> str:
        """Check for common injection attack patterns."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(value):
                raise ValueError(f"{field_name} contains potentially malicious content")
        return value

    @classmethod
    def validate_medical_license(cls, value: str) -> str:
        """Validate medical license number format."""
        if not isinstance(value, str):
            raise ValueError("License number must be a string")
        
        value = value.strip().upper()
        cls.validate_no_injection(value, "license number")
        
        if not cls.LICENSE_PATTERN.match(value):
            raise ValueError("License number must be in format: PREFIX-NUMBER (e.g., MD-12345)")
        
        return value

    @classmethod
    def validate_mrn(cls, value: str) -> str:
        """Validate Medical Record Number format."""
        if not isinstance(value, str):
            raise ValueError("MRN must be a string")
        
        value = value.strip().upper()
        cls.validate_no_injection(value, "MRN")
        
        if not cls.MRN_PATTERN.match(value):
            raise ValueError("MRN must be 6-12 alphanumeric characters")
        
        return value

    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        """Validate Patient ID (UUID format or MRN)."""
        if not isinstance(value, str):
            raise ValueError("Patient ID must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "patient_id")
        
        uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if not (uuid_pattern.match(value) or cls.MRN_PATTERN.match(value.upper())):
            raise ValueError("Patient ID must be a valid UUID or MRN")
        
        return value

    @classmethod
    def validate_npi(cls, value: str) -> str:
        """Validate National Provider Identifier."""
        if not isinstance(value, str):
            raise ValueError("NPI must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "NPI")
        
        if not cls.NPI_PATTERN.match(value):
            raise ValueError("NPI must be exactly 10 digits")
        
        return value

    @classmethod
    def validate_person_name(cls, value: str) -> str:
        """Validate person names (patients, doctors, etc.)."""
        if not isinstance(value, str):
            raise ValueError("Name must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "name")
        
        if not value:
            raise ValueError("Name cannot be empty")
        
        if not cls.NAME_PATTERN.match(value):
            raise ValueError("Name contains invalid characters")
        
        if len(value) > 100:
            raise ValueError("Name too long (max 100 characters)")
        
        return value

    @classmethod
    def validate_phone(cls, value: str) -> str:
        """Validate phone numbers."""
        if not isinstance(value, str):
            raise ValueError("Phone number must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "phone number")
        
        if not cls.PHONE_PATTERN.match(value):
            raise ValueError("Invalid phone number format")
        
        return value

    @classmethod
    def validate_medical_text(cls, value: str, field_name: str = "medical text", max_length: int = 500) -> str:
        """Validate medical text fields (allergies, diagnoses, etc.)."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, field_name)
        
        if len(value) > max_length:
            raise ValueError(f"{field_name} too long (max {max_length} characters)")
        
        # Allow medical terminology but prevent code injection
        if not re.match(r'^[a-zA-Z0-9\s\,\.\-\(\)\/\:\+\%\&]{0,' + str(max_length) + '}$', value):
            raise ValueError(f"{field_name} contains invalid characters")
        
        return value

    @classmethod
    def validate_dosage(cls, value: str) -> str:
        """Validate medication dosage strings."""
        if not isinstance(value, str):
            raise ValueError("Dosage must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "dosage")
        
        # Allow medical dosage formats: "10mg", "2.5 ml", "1 tablet twice daily"
        if not re.match(r'^[0-9\.\s]+(mg|ml|g|units?|tablets?|capsules?|drops?|tsp|tbsp)(\s+[a-zA-Z0-9\s\-,\.]{0,50})?$', value, re.IGNORECASE):
            raise ValueError("Invalid dosage format")
        
        return value

    @classmethod
    def validate_icd_code(cls, value: str) -> str:
        """Validate ICD-10 diagnostic codes."""
        if not isinstance(value, str):
            raise ValueError("ICD code must be a string")
        
        value = value.strip().upper()
        cls.validate_no_injection(value, "ICD code")
        
        # ICD-10 format: Letter + 2 digits + optional dot + up to 4 more alphanumeric
        if not re.match(r'^[A-Z][0-9]{2}(\.[A-Z0-9]{1,4})?$', value):
            raise ValueError("Invalid ICD-10 code format")
        
        return value

    @classmethod
    def validate_blood_group(cls, value: str) -> str:
        """Validate blood group/type."""
        if not isinstance(value, str):
            raise ValueError("Blood group must be a string")
        
        value = value.strip().upper()
        cls.validate_no_injection(value, "blood group")
        
        valid_groups = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
        if value not in valid_groups:
            raise ValueError(f"Invalid blood group. Must be one of: {', '.join(sorted(valid_groups))}")
        
        return value

    @classmethod
    def validate_emergency_message(cls, value: str) -> str:
        """Validate emergency contact messages."""
        if not isinstance(value, str):
            raise ValueError("Emergency message must be a string")
        
        value = value.strip()
        cls.validate_no_injection(value, "emergency message")
        
        if len(value) > 1000:
            raise ValueError("Emergency message too long (max 1000 characters)")
        
        # Allow essential emergency information
        if not re.match(r'^[a-zA-Z0-9\s\,\.\-\(\)\/\:\+\%\&\!\?\'\"]{0,1000}$', value):
            raise ValueError("Emergency message contains invalid characters")
        
        return value


def create_length_validator(min_length: int = 0, max_length: int = 1000):
    """Factory for creating string length validators."""
    def validate_length(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        value = value.strip()
        if len(value) < min_length:
            raise ValueError(f"Value too short (minimum {min_length} characters)")
        if len(value) > max_length:
            raise ValueError(f"Value too long (maximum {max_length} characters)")
        
        return value
    
    return validate_length


def create_numeric_validator(min_val: float = None, max_val: float = None, positive_only: bool = False):
    """Factory for creating numeric validators with range checks."""
    def validate_numeric(value: float) -> float:
        if positive_only and value < 0:
            raise ValueError("Value must be positive")
        
        if min_val is not None and value < min_val:
            raise ValueError(f"Value must be at least {min_val}")
        
        if max_val is not None and value > max_val:
            raise ValueError(f"Value must be at most {max_val}")
        
        return value
    
    return validate_numeric