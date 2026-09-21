"""
Prescription integrity signing (Ed25519).

Uses Ed25519 signatures to cryptographically prove *which doctor* authored
the content and that it hasn't been altered since. Legacy HMAC verification 
is maintained for already-signed immutable records.
"""

import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import settings


def _doctor_signing_key(doctor_id: str) -> bytes:
    """Legacy HMAC key derivation for existing immutable records."""
    return hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{doctor_id}".encode()).digest()


def sign_prescription(doctor_id: str, canonical_content: str) -> str:
    key_hex = settings.PRESCRIPTION_SIGNING_KEY_HEX
    if not key_hex or len(key_hex) != 64:
        raise ValueError("Invalid Ed25519 private key configuration")
        
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
    signature_bytes = private_key.sign(canonical_content.encode("utf-8"))
    
    # Store alg=ed25519, kid=v1 with the signature
    return f"ed25519:v1:{signature_bytes.hex()}"


def verify_prescription_signature(doctor_id: str, canonical_content: str, signature: str) -> bool:
    if signature.startswith("ed25519:"):
        parts = signature.split(":")
        if len(parts) == 3:
            alg, kid, sig_hex = parts
            key_hex = settings.PRESCRIPTION_SIGNING_KEY_HEX
            if not key_hex or len(key_hex) != 64:
                return False
                
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
            public_key = private_key.public_key()
            try:
                public_key.verify(bytes.fromhex(sig_hex), canonical_content.encode("utf-8"))
                return True
            except Exception:
                return False
    else:
        # Fallback to legacy HMAC for existing immutable records
        expected = hmac.new(_doctor_signing_key(doctor_id), canonical_content.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
        
    return False


def canonical_prescription_content(diagnosis: str, notes: str, items: list[dict]) -> str:
    # Deterministic serialization using the existing format to maintain compatibility
    items_str = "|".join(
        f"{i['medicine_name']}:{i.get('dosage')}:{i.get('frequency')}:{i.get('duration_days')}"
        for i in items
    )
    return f"{diagnosis}||{notes}||{items_str}"
