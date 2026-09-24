import base64

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_ZERO_HEX_64 = "0" * 64


class Settings(BaseSettings):
    """
    Centralized application settings, loaded from environment variables / .env.
    Never hardcode secrets here — this class only defines shape + defaults.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "mysql+pymysql://cryptcare_user:changeme@localhost:3306/cryptcare"

    # JWT
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    MFA_REQUIRED_ROLES: list[str] = ["DOCTOR", "NURSE", "PHARMACIST", "LAB", "BLOOD_BANK", "INSURER", "HOSPITAL_ADMIN", "ADMIN"]
    BREAK_GLASS_ALLOWED_ROLES: list[str] = ["DOCTOR"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY_V1: str
    ENCRYPTION_KEY_V2: str | None = None
    ACTIVE_ENCRYPTION_KEY_VERSION: str = "v1"
    ENFORCE_AAD_V2: bool = False

    # Prescription Signing (Ed25519)
    # Must be a 64-char hex string representing a 32-byte raw Ed25519 private key.
    # Generate with:
    #   python -c "from cryptography.hazmat.primitives.asymmetric import ed25519; \
    #              print(ed25519.Ed25519PrivateKey.generate().private_bytes_raw().hex())"
    PRESCRIPTION_SIGNING_KEY_HEX: str = _ZERO_HEX_64

    @field_validator("PRESCRIPTION_SIGNING_KEY_HEX")
    @classmethod
    def _validate_signing_key(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError(
                "PRESCRIPTION_SIGNING_KEY_HEX must be exactly 64 hex characters (32-byte Ed25519 key)."
            )
        try:
            bytes.fromhex(v)
        except ValueError:
            raise ValueError("PRESCRIPTION_SIGNING_KEY_HEX must be a valid hex string.")
        # Reject the all-zeros default — it is a valid 64-char hex string and
        # would silently "work" but offers zero security (publicly known key).
        if v == _ZERO_HEX_64:
            raise ValueError(
                "PRESCRIPTION_SIGNING_KEY_HEX is set to the insecure all-zeros default. "
                "Generate a real key and set it in your .env file."
            )
        return v

    # OTP (registration/phone verification — Phase 1)
    OTP_EXPIRY_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # MFA (login TOTP)
    MFA_ISSUER_NAME: str = "CryptCare"
    MFA_TOTP_VALID_WINDOW: int = 1

    # Rate limiting
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    RATE_LIMIT_OTP_MAX: int = 5
    RATE_LIMIT_OTP_WINDOW_SECONDS: int = 300
    RATE_LIMIT_DEFAULT_MAX: int = 100
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_EMERGENCY_ACCESS_MAX: int = 10
    RATE_LIMIT_EMERGENCY_ACCESS_WINDOW_SECONDS: int = 300

    # Clinical safety
    DRUG_MATCH_SIMILARITY_THRESHOLD: float = 0.55

    # Local AI
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.1"
    LOCAL_LLM_TIMEOUT_SECONDS: float = 3.0
    LOCAL_LLM_ENABLED: bool = True

    # Email / SMTP
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_ADDRESS: str = ""
    SMTP_FROM_NAME: str = "CryptCare"

    # App
    ENV: str = "development"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"


settings = Settings()
