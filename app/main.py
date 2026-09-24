import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.db.base import Base
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

    # ------------------------------------------------------------------ #
    # Phase 3 — Key management: reject placeholder / insecure key values  #
    # at boot so a misconfigured deployment fails loudly rather than       #
    # silently running with known-weak keys.                               #
    # ------------------------------------------------------------------ #
    import base64
    import sys

    _PLACEHOLDER_JWT_SECRETS = {
        "replace-with-a-long-random-secret",
        "your-secret-key",
        "changeme",
        "secret",
    }
    _PLACEHOLDER_ENC_KEYS = {
        "replace-with-base64-32-byte-key",
        "changeme",
        "",
    }

    if settings.ENV != "development":
        errors: list[str] = []

        if settings.JWT_SECRET_KEY in _PLACEHOLDER_JWT_SECRETS:
            errors.append("JWT_SECRET_KEY is set to a known placeholder value.")

        try:
            enc_key_bytes = base64.b64decode(settings.ENCRYPTION_KEY_V1)
            if len(enc_key_bytes) != 32:
                errors.append("ENCRYPTION_KEY_V1 must decode to exactly 32 bytes.")
            if settings.ENCRYPTION_KEY_V1 in _PLACEHOLDER_ENC_KEYS:
                errors.append("ENCRYPTION_KEY_V1 is set to a known placeholder value.")
        except Exception:
            errors.append("ENCRYPTION_KEY_V1 is not valid base64.")

        # PRESCRIPTION_SIGNING_KEY_HEX is already validated at settings-load
        # time by the Pydantic field_validator (rejects zero key and bad hex).
        # Duplicate the zero-key check here for defence-in-depth in non-dev
        # environments where Settings may have been constructed differently.
        if settings.PRESCRIPTION_SIGNING_KEY_HEX == "0" * 64:
            errors.append("PRESCRIPTION_SIGNING_KEY_HEX is the all-zeros default (insecure).")

        if errors:
            print("FATAL: Insecure key configuration detected — refusing to start in non-development mode:")
            for e in errors:
                print(f"  • {e}")
            sys.exit(1)

    # Pre-seed broadcast cooldowns
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

    # Deny-by-default enforcement
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
        raise RuntimeError(
            f"Deny-by-default enforcement failed! The following routes are missing "
            f"an explicit auth dependency: {missing_auth}"
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}
