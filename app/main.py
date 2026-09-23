import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.db.base import Base
from app.middleware.rate_limit import RateLimitMiddleware

# Import all models so they register on Base.metadata before create_all().
from app.models import audit, consent, lab, notification, nursing, user, vault, insurance, blood_bank, emergency, fraud  # noqa: F401

kwargs = {}
if settings.ENV != "dev":
    kwargs["docs_url"] = None
    kwargs["redoc_url"] = None
    kwargs["openapi_url"] = None

app = FastAPI(
    title="CryptCare API",
    description="Patient-Sovereign Healthcare Ecosystem — Phases 1-4 (Identity, Vault, Laboratory, Consent) + Phase 4/2/3 extensions (break-glass, caregiver access, activity timeline, notifications, prescription QR, encrypted imaging)",
    version="0.2.0",
    **kwargs
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
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    
    # Pre-seed broadcast cooldowns to prevent gap lock deadlocks on compare-and-set
    from app.db.session import SessionLocal
    from app.models.blood_bank import BroadcastCooldown, BloodComponentEnum
    from datetime import datetime, timedelta
    
    with SessionLocal() as session:
        existing = session.query(BroadcastCooldown).count()
        if existing == 0:
            cooldowns = []
            for bg in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
                for comp in BloodComponentEnum:
                    cooldowns.append(BroadcastCooldown(
                        blood_group=bg,
                        component=comp,
                        last_broadcast_at=datetime.utcnow() - timedelta(days=1)
                    ))
            session.add_all(cooldowns)
            session.commit()

    # Ensure all routes have an explicit authentication dependency (Deny-by-default)
    from app.core.auth_registry import PUBLIC_ALLOWLIST, REFRESH_COOKIE_AUTHENTICATED, is_auth_provider
    
    def has_auth_dependency(dependant, seen=None) -> bool:
        if seen is None:
            seen = set()
        if not dependant or id(dependant) in seen:
            return False
        seen.add(id(dependant))
        
        if not hasattr(dependant, "dependencies") or not dependant.dependencies:
            return False
            
        for dep in dependant.dependencies:
            if is_auth_provider(dep.call):
                return True
            if has_auth_dependency(dep, seen):
                return True
        return False

    missing_auth = []
    from fastapi.routing import APIRoute
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if path in PUBLIC_ALLOWLIST or path in REFRESH_COOKIE_AUTHENTICATED:
            continue
        if not has_auth_dependency(route.dependant):
            missing_auth.append(f"{list(route.methods)} {path} ({route.name})")
            
    if missing_auth:
        raise RuntimeError(f"Deny-by-default enforcement failed! The following routes are missing an explicit auth dependency: {missing_auth}")


@app.get("/health")
def health_check():
    return {"status": "ok"}
