"""
Prescription integrity signing (simplified for the academic build).

Production note: use per-doctor RSA-4096 or ECC keypairs (private key held
in a secure enclave/HSM on the doctor's verified device or server-side vault)
so a signature cryptographically proves *which doctor* authored the content
and that it hasn't been altered since. This module uses HMAC-SHA256 keyed by
a per-doctor secret as a simpler stand-in that still demonstrates the same
tamper-evidence property for a final-year build.
"""

import hashlib
import hmac

from app.core.config import settings


def _doctor_signing_key(doctor_id: str) -> bytes:
    # Derive a per-doctor key from the master secret rather than storing
    # separate keys per doctor — simpler key management for the demo scope.
    return hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{doctor_id}".encode()).digest()


def sign_prescription(doctor_id: str, canonical_content: str) -> str:
    key = _doctor_signing_key(doctor_id)
    signature = hmac.new(key, canonical_content.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature


def verify_prescription_signature(doctor_id: str, canonical_content: str, signature: str) -> bool:
    expected = sign_prescription(doctor_id, canonical_content)
    return hmac.compare_digest(expected, signature)


def canonical_prescription_content(diagnosis: str, notes: str, items: list[dict]) -> str:
    items_str = "|".join(
        f"{i['medicine_name']}:{i.get('dosage')}:{i.get('frequency')}:{i.get('duration_days')}"
        for i in items
    )
    return f"{diagnosis}||{notes}||{items_str}"
