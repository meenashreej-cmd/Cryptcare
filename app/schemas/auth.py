from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.user import RoleEnum, UserStatusEnum

_PROFESSIONAL_ROLES = (
    RoleEnum.DOCTOR, RoleEnum.NURSE, RoleEnum.LAB,
    RoleEnum.PHARMACIST, RoleEnum.INSURER, RoleEnum.BLOOD_BANK,
)


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    role: RoleEnum

    # Patient-only fields
    dob: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None

    # Doctor/Nurse/Lab/Pharmacist/Insurer fields
    license_number: Optional[str] = None
    specialization: Optional[str] = None
    hospital_name: Optional[str] = None
    organization_name: Optional[str] = None
    department: Optional[str] = None  # Nurse-only, e.g. "ICU", "General Ward"

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v

<<<<<<< Updated upstream
    @field_validator("license_number")
    @classmethod
    def license_required_for_professional_roles(cls, v, info):
        role = info.data.get("role")
        if role in (RoleEnum.DOCTOR, RoleEnum.NURSE, RoleEnum.LAB, RoleEnum.PHARMACIST, RoleEnum.INSURER, RoleEnum.BLOOD_BANK) and not v:
            raise ValueError(f"license_number is required for role {role}")
        return v
        
    @field_validator("hospital_name")
    @classmethod
    def hospital_name_required_for_hospital_admin(cls, v, info):
        role = info.data.get("role")
        if role == RoleEnum.HOSPITAL_ADMIN and not v:
            raise ValueError("hospital_name is required for HOSPITAL_ADMIN")
        return v
=======
    @model_validator(mode="after")
    def license_required_for_professional_roles(self) -> "RegisterRequest":
        """
        Uses model_validator (runs after all fields are parsed) so `role`
        is always available — field_validator on license_number ran before
        role was guaranteed to be in info.data, causing silent misses.
        """
        if self.role in _PROFESSIONAL_ROLES and not self.license_number:
            raise ValueError(f"license_number is required for role {self.role}")
        return self
>>>>>>> Stashed changes


class RegisterResponse(BaseModel):
    user_id: str
    status: UserStatusEnum
    # True when the submitted license_number was found in the licensing
    # registry and the professional profile has been pre-verified.
    # Always False for PATIENT and ADMIN (no license required).
    license_verified: bool = False
    # Only present for MFA-required roles (DOCTOR/NURSE/PHARMACIST/ADMIN),
    # and only ever returned on this one response — scan it into an
    # authenticator app now; it cannot be retrieved again.
    mfa_provisioning_uri: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    user_id: str
    otp_code: str = Field(min_length=4, max_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: Optional[str] = None  # required for MFA-enabled roles


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    user_id: str
    email: EmailStr
    phone: str
    full_name: str
    role: RoleEnum
    status: UserStatusEnum

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
