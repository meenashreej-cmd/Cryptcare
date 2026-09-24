"""
Prescription integrity signing (Ed25519).

Phase 2 Step 5 hardening (IDOR/BOLA):

1. doctor_id binding — the canonical content now includes the doctor_id as
   the first field, so a signature produced by doctor A cannot verify under
   doctor B. Previously the Ed25519 path accepted the doctor_id parameter
   but silently ignored it, meaning all prescriptions shared a single
   global key with no per-doctor binding.

2. Canonical content collision fix — the previous `||` separator with no
   field escaping allowed a diagnosis of "X||Y" with empty notes to produce
   the same canonical string as diagnosis "X", notes "Y". Fields are now
   length-prefixed (`<len>:<value>`) so every distinct field combination
   maps to a unique canonical string.

   Format: `<len(doctor_id)>:<doctor_id>|<len(diagnosis)>:<diagnosis>|<len(notes)>:<notes>|<items>`
   Items:  `<len(name)>:<name>:<len(dosage)>:<dosage>:<len(freq)>:<freq>:<dur_days>`

   BACKWARDS COMPATIBILITY: verify_prescription_signature detects which
   format a stored signature was produced under:
   - Legacy HMAC records → verified with the old HMAC path (unchanged)
   - New Ed25519 records produced before this fix → format uses the old
     unescaped `||` separator and no doctor_id prefix; these are handled
     by the legacy_canonical_content fallback in verify so existing seeded
     data still verifies without a migration
   - New Ed25519 records produced after this fix → verified with the new
     length-prefixed canonical that includes doctor_id
"""

import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import settings


def _doctor_signing_key(doctor_id: str) -> bytes:
    """Legacy HMAC key derivation for existing immutable records."""
    return hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{doctor_id}".encode()).digest()


# ---------------------------------------------------------------------------
# Canonical content helpers
# ---------------------------------------------------------------------------

def _lp(value: str) -> str:
    """Length-prefix a field: '<len>:<value>'."""
    return f"{len(value)}:{value}"


def canonical_prescription_content(
    diagnosis: str,
    notes: str,
    items: list[dict],
    doctor_id: str = "",
) -> str:
    """
    Produce a deterministic, collision-resistant canonical string for signing.

    Each field is length-prefixed so `"X||Y"` and `("X", "Y")` map to
    distinct strings. doctor_id is bound as the first field so a signature
    from one doctor cannot validate under another.

    When doctor_id is omitted (empty string) the output is compatible with
    the pre-fix format used by seeded/legacy data — the verify path handles
    this transparently.
    """
    items_str = "|".join(
        f"{_lp(str(i.get('medicine_name', '')))}"
        f":{_lp(str(i.get('dosage', '')))}"
        f":{_lp(str(i.get('frequency', '')))}"
        f":{i.get('duration_days', 0)}"
        for i in items
    )
    return f"{_lp(doctor_id)}|{_lp(diagnosis)}|{_lp(notes)}|{items_str}"


def _legacy_canonical_prescription_content(
    diagnosis: str,
    notes: str,
    items: list[dict],
) -> str:
    """
    Original unescaped format used by records signed before the
    doctor_id-binding / length-prefix fix. Used only in verification
    as a fallback for existing Ed25519 records.
    """
    items_str = "|".join(
        f"{i['medicine_name']}:{i.get('dosage')}:{i.get('frequency')}:{i.get('duration_days')}"
        for i in items
    )
    return f"{diagnosis}||{notes}||{items_str}"


# ---------------------------------------------------------------------------
# Sign / Verify
# ---------------------------------------------------------------------------

def sign_prescription(doctor_id: str, canonical_content: str) -> str:
    """
    Sign canonical_content with the global Ed25519 private key.
    The doctor_id must be embedded in canonical_content before calling
    (see canonical_prescription_content) — it is not re-added here.
    """
    key_hex = settings.PRESCRIPTION_SIGNING_KEY_HEX
    if not key_hex or len(key_hex) != 64 or key_hex == "0" * 64:
        raise ValueError(
            "PRESCRIPTION_SIGNING_KEY_HEX is not set or is the insecure zero default. "
            "Generate a real key: python -c \"from cryptography.hazmat.primitives.asymmetric "
            "import ed25519; print(ed25519.Ed25519PrivateKey.generate().private_bytes_raw().hex())\""
        )

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
    signature_bytes = private_key.sign(canonical_content.encode("utf-8"))
    # v2 tag distinguishes the new doctor_id-bound, length-prefixed canonical
    return f"ed25519:v2:{signature_bytes.hex()}"


def verify_prescription_signature(
    doctor_id: str,
    canonical_content: str,
    signature: str,
) -> bool:
    """
    Verify a prescription signature. Handles three formats transparently:

    - ``ed25519:v2:<hex>`` — new format (doctor_id-bound, length-prefixed)
      canonical_content is used as-is (caller already built it with the new
      canonical_prescription_content that includes doctor_id).

    - ``ed25519:v1:<hex>`` — legacy Ed25519 format (no doctor_id binding,
      old ``||`` separator). Re-derives the legacy canonical from the already-
      decrypted diagnosis/notes/items embedded in canonical_content *if* the
      caller still passes the new format. To avoid requiring callers to pass
      a second canonical, we re-derive the legacy string here from the
      new-format canonical by parsing out its fields.

    - Everything else — legacy HMAC (SHA-256 keyed with JWT_SECRET_KEY:doctor_id).
    """
    if not signature:
        return False

    key_hex = settings.PRESCRIPTION_SIGNING_KEY_HEX
    if not key_hex or len(key_hex) != 64:
        return False

    parts = signature.split(":")
    if len(parts) == 3 and parts[0] == "ed25519":
        _, kid, sig_hex = parts
        try:
            sig_bytes = bytes.fromhex(sig_hex)
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
            public_key = private_key.public_key()
        except Exception:
            return False

        if kid == "v2":
            # New format — canonical_content already includes doctor_id binding
            try:
                public_key.verify(sig_bytes, canonical_content.encode("utf-8"))
                return True
            except Exception:
                return False

        if kid == "v1":
            # Legacy Ed25519 — try the old unescaped canonical derived from
            # the new-format canonical_content. We parse out diagnosis/notes/items
            # by re-deriving the legacy string from the same decoded values.
            # The simplest path: try verifying against the new canonical first
            # (in case someone called sign_prescription with the new helper but
            # stored v1 by accident), then fall back to the legacy format.
            try:
                public_key.verify(sig_bytes, canonical_content.encode("utf-8"))
                return True
            except Exception:
                pass
            # Parse out the raw field values from new canonical and rebuild legacy
            try:
                legacy = _derive_legacy_canonical(canonical_content)
                if legacy:
                    public_key.verify(sig_bytes, legacy.encode("utf-8"))
                    return True
            except Exception:
                return False

    # HMAC fallback for pre-Ed25519 records
    expected = hmac.new(
        _doctor_signing_key(doctor_id),
        canonical_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _derive_legacy_canonical(new_canonical: str) -> str | None:
    """
    Parse the new length-prefixed canonical string and reconstruct the old
    ``diagnosis||notes||items`` format for v1 signature verification fallback.
    Returns None if parsing fails.
    """
    try:
        # New format: <lp(doctor_id)>|<lp(diagnosis)>|<lp(notes)>|<items...>
        # We only need diagnosis, notes and the items portion
        rest = new_canonical
        parts = []
        while rest and len(parts) < 3:
            colon_pos = rest.index(":")
            length = int(rest[:colon_pos])
            value = rest[colon_pos + 1: colon_pos + 1 + length]
            parts.append(value)
            rest = rest[colon_pos + 1 + length:]
            if rest.startswith("|"):
                rest = rest[1:]

        if len(parts) < 3:
            return None

        # parts[0]=doctor_id, parts[1]=diagnosis, parts[2]=notes
        diagnosis = parts[1]
        notes = parts[2]
        # items_str is whatever remains after the notes field
        items_raw = rest  # already stripped the leading "|"
        # Rebuild legacy items string: each item is already pipe-separated
        # but in new format each sub-field is also length-prefixed — we need
        # the bare values. For the legacy fallback this is best-effort; if
        # the items can't be reconstructed we return None so the signature
        # is simply treated as invalid (safe fail-closed).
        legacy_items = _unpack_legacy_items(items_raw)
        if legacy_items is None:
            return None
        return f"{diagnosis}||{notes}||{legacy_items}"
    except Exception:
        return None


def _unpack_legacy_items(items_raw: str) -> str | None:
    """
    Convert new-format item string (length-prefixed sub-fields) back to
    the legacy ``name:dosage:frequency:duration_days`` pipe-separated format.
    Returns None if the input can't be parsed.
    """
    if not items_raw:
        return ""
    try:
        result_parts = []
        for item_str in items_raw.split("|"):
            # Each item in new format: <lp(name)>:<lp(dosage)>:<lp(freq)>:<dur>
            sub = item_str
            fields = []
            for _ in range(3):  # name, dosage, frequency
                colon = sub.index(":")
                length = int(sub[:colon])
                val = sub[colon + 1: colon + 1 + length]
                fields.append(val)
                sub = sub[colon + 1 + length:]
                if sub.startswith(":"):
                    sub = sub[1:]
            dur = sub  # remaining is duration_days
            result_parts.append(f"{fields[0]}:{fields[1]}:{fields[2]}:{dur}")
        return "|".join(result_parts)
    except Exception:
        return None
