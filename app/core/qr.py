"""
QR code generation for signed prescriptions (Phase 2 extension) and, in
future, Emergency QR (Phase 10).

IMPORTANT: a QR payload here is a REFERENCE + SIGNATURE, never the record's
actual content. A photographed/leaked QR image must not itself disclose PHI —
the holder still has to resolve the reference through the normal
authenticated + consent-gated API to see anything, same as if they'd typed
the prescription ID in by hand. The QR is a convenience for identifying and
proving-authentic a record, not a bypass around access control.
"""

import io

import qrcode


def build_prescription_qr_payload(prescription_id: str, digital_signature: str) -> str:
    """
    A compact reference string, not a data blob. Resolving it still requires
    calling GET /vault/prescriptions?patient_id=... (or a future dedicated
    lookup-by-id endpoint) through the normal auth + consent path.
    """
    return f"cryptcare:prescription:{prescription_id}:{digital_signature}"


def generate_qr_png(payload: str) -> bytes:
    """Renders `payload` as a PNG QR code and returns the raw image bytes."""
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def parse_prescription_qr_payload(payload: str) -> tuple[str, str]:
    """
    Inverse of build_prescription_qr_payload — used by a future Phase 8
    (Pharmacy) scan endpoint. Returns (prescription_id, digital_signature).
    Raises ValueError on a malformed payload rather than guessing.
    """
    parts = payload.split(":")
    if len(parts) != 4 or parts[0] != "cryptcare" or parts[1] != "prescription":
        raise ValueError("Not a recognized CryptCare prescription QR payload")
    _, _, prescription_id, signature = parts
    return prescription_id, signature


def build_emergency_qr_payload(token: str) -> str:
    """
    A compact reference string. Resolving it hits the public emergency access
    endpoint.
    """
    return f"cryptcare:emergency:{token}"


def parse_emergency_qr_payload(payload: str) -> str:
    """
    Inverse of build_emergency_qr_payload. Returns token.
    Raises ValueError on a malformed payload.
    """
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "cryptcare" or parts[1] != "emergency":
        raise ValueError("Not a recognized CryptCare emergency QR payload")
    return parts[2]
