import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.middleware.rate_limit import RateLimitMiddleware

# Import all models so they register on Base.metadata before create_all().
from app.models import audit, consent, lab, notification, nursing, user, vault, insurance, blood_bank, emergency, fraud  # noqa: F401

app = FastAPI(
    title="CryptCare API",
    description="Patient-Sovereign Healthcare Ecosystem — Phases 1-4 (Identity, Vault, Laboratory, Consent) + Phase 4/2/3 extensions (break-glass, caregiver access, activity timeline, notifications, prescription QR, encrypted imaging)",
    version="0.2.0",
)

allowed_origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
if settings.ENV != "dev" and "*" in allowed_origins:
    print("FATAL: Wildcard CORS allowed origins are not permitted outside of development.")
    sys.exit(1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    # For the academic build, auto-create tables from models.
    # In production, use Alembic migrations instead (see alembic/ directory).
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}
