"""
Phase 10 — Emergency QR Access.

A patient generates a durable QR "emergency card" they can print or keep on
their phone/wristband. Anyone who scans it — an EMT, an ER nurse, a
bystander — can view a small, safety-critical subset of the patient's
record WITHOUT logging in and WITHOUT prior consent. This is deliberately
the one endpoint in the whole API with zero authentication, because the
entire point is that it has to work when the patient is unconscious and no
CryptCare account is available to authenticate with.

That's a real, deliberate exception to this codebase's "no PHI without
consent" rule (see app/core/qr.py's docstring — this phase is the one place
that rule doesn't hold) — so it's compensated for on every front break-glass
and pharmacy access already established as the pattern for a no-prior-consent
exception:
  1. The card shows only safety-critical fields — blood group, allergies,
     current (ACTIVE) medications, DOB, and a designated emergency contact.
     Never diagnosis, notes, lab reports, or anything else in the vault.
  2. Every scan is logged with a distinct AccessActionEnum.EMERGENCY_QR_ACCESS
     action, never indistinguishable from a normal read.
  3. Every scan fires an immediate, mandatory patient notification.
  4. The token itself is a high-entropy secret (32 bytes via `secrets`, per
     the Phase 1 OTP lesson — never `random`), and only its SHA-256 hash is
     stored — the same pattern password hashing uses. A leaked database
     doesn't hand over live tokens.
  5. The patient fully controls it: revoke anytime, regenerate anytime
     (which immediately invalidates the old one — one active token per
     patient, not a growing pile of live QR codes).
  6. GET /emergency/access/{token} gets its own tight, per-IP (not
     per-path) rate limit — see app/middleware/rate_limit.py's
     _SENSITIVE_PREFIXES — since a different token per guess would
     otherwise dodge exact-path-keyed limiting entirely.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmergencyAccessToken(Base):
    __tablename__ = "emergency_access_tokens"

    token_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.patient_id"), nullable=False)
    # SHA-256 hex digest of the raw token — the raw value is shown to the
    # patient exactly once (encoded in the QR PNG at generation time) and
    # never persisted or logged in plaintext, same as a password.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
