from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings, loaded from environment variables / .env.
    Never hardcode secrets here — this class only defines shape + defaults.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "mysql+pymysql://cryptcare_user:changeme@localhost:3306/cryptcare"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY_V1: str
    # Populated during a key-rotation window: generate a new base64 32-byte
    # key, set it here, keep ENCRYPTION_KEY_V1 as-is (old rows still decrypt
    # against it), then flip ACTIVE_ENCRYPTION_KEY_VERSION to "v2" so new
    # writes use the new key. See tests/test_key_rotation.py.
    ENCRYPTION_KEY_V2: str | None = None
    ACTIVE_ENCRYPTION_KEY_VERSION: str = "v1"

    # OTP (registration/phone verification — Phase 1)
    OTP_EXPIRY_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # MFA (login TOTP — Phase 5)
    MFA_ISSUER_NAME: str = "CryptCare"
    MFA_TOTP_VALID_WINDOW: int = 1  # +/- 30s steps tolerated for clock drift

    # Rate limiting (Phase 5) — in-memory, per-process. See app/middleware/rate_limit.py.
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    RATE_LIMIT_OTP_MAX: int = 5
    RATE_LIMIT_OTP_WINDOW_SECONDS: int = 300
    RATE_LIMIT_DEFAULT_MAX: int = 100
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_EMERGENCY_ACCESS_MAX: int = 10
    RATE_LIMIT_EMERGENCY_ACCESS_WINDOW_SECONDS: int = 300

    # Clinical safety (Phase 7)
    DRUG_MATCH_SIMILARITY_THRESHOLD: float = 0.55

    # Local AI (Phase 7 explanations, Phase 6 architecture doc's "local-only,
    # never sends PHI off-device" principle) — Ollama running on the same
    # trust boundary as the app. Explanation generation is best-effort: if
    # this is unreachable, clinical_safety_service falls back to a
    # deterministic templated explanation rather than failing the request.
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.1"
    LOCAL_LLM_TIMEOUT_SECONDS: float = 3.0
    LOCAL_LLM_ENABLED: bool = True

    # Email / SMTP (OTP delivery — Phase 1)
    # Set SMTP_ENABLED=false to fall back to console logging (dev/CI default).
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""          # e.g. yourapp@gmail.com
    SMTP_PASSWORD: str = ""          # app-password, NOT account password
    SMTP_FROM_ADDRESS: str = ""      # defaults to SMTP_USERNAME if left blank
    SMTP_FROM_NAME: str = "CryptCare"

    # App
    ENV: str = "development"


settings = Settings()
