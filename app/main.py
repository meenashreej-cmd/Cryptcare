from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.db.base import Base
from app.db.session import engine
from app.middleware.rate_limit import RateLimitMiddleware

# Import all models so they register on Base.metadata before create_all().
from app.models import audit, consent, lab, notification, nursing, user, vault, insurance  # noqa: F401

app = FastAPI(
    title="CryptCare API",
    description="Patient-Sovereign Healthcare Ecosystem — Phases 1-4 (Identity, Vault, Laboratory, Consent) + Phase 4/2/3 extensions (break-glass, caregiver access, activity timeline, notifications, prescription QR, encrypted imaging)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the Flutter app's origin(s) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
