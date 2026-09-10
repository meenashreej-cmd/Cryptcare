"""
Field-level AES-256-GCM encryption for PHI columns.

Ciphertext is stored as: "<key_version>:<base64(nonce)>:<base64(ciphertext)>"
so that key rotation never breaks decryption of historical records —
each blob carries the key version it was encrypted under.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

# In a real deployment this map is populated from a KMS/HSM/secret manager,
# keyed by version, so multiple key versions can coexist during rotation.
_KEY_REGISTRY = {
    "v1": base64.b64decode(settings.ENCRYPTION_KEY_V1),
}
if settings.ENCRYPTION_KEY_V2:
    # Old ciphertext blobs carry "v1:..." and keep decrypting against the v1
    # key below even after this is added — only ACTIVE_ENCRYPTION_KEY_VERSION
    # controls which key *new* encrypt() calls use.
    _KEY_REGISTRY["v2"] = base64.b64decode(settings.ENCRYPTION_KEY_V2)

_NONCE_SIZE = 12  # bytes, recommended for AES-GCM


def register_key_version(version: str, key_bytes: bytes) -> None:
    """
    Hot-register an additional key version into the in-process registry.

    In production this is what a KMS-refresh hook would call when a new key
    version is provisioned, ahead of flipping ACTIVE_ENCRYPTION_KEY_VERSION.
    Exposed as a function (rather than only reading ENCRYPTION_KEY_V2 once at
    import time) so rotation can be exercised/tested without a process
    restart — see tests/test_key_rotation.py.
    """
    if len(key_bytes) != 32:
        raise ValueError("AES-256-GCM key must be exactly 32 bytes")
    _KEY_REGISTRY[version] = key_bytes


def _get_active_key() -> tuple[str, bytes]:
    version = settings.ACTIVE_ENCRYPTION_KEY_VERSION
    if version not in _KEY_REGISTRY:
        raise ValueError(
            f"ACTIVE_ENCRYPTION_KEY_VERSION is set to {version!r} but no key is "
            f"registered for it — register it first (see register_key_version)."
        )
    return version, _KEY_REGISTRY[version]


def _get_key_by_version(version: str) -> bytes:
    if version not in _KEY_REGISTRY:
        raise ValueError(f"Unknown encryption key version: {version}")
    return _KEY_REGISTRY[version]


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string, returning an opaque versioned blob."""
    if plaintext is None:
        return None
    version, key = _get_active_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return f"{version}:{base64.b64encode(nonce).decode()}:{base64.b64encode(ciphertext).decode()}"


def decrypt(blob: str) -> str:
    """Decrypt a versioned blob produced by encrypt(). Raises on tamper/corruption."""
    if blob is None:
        return None
    try:
        version, nonce_b64, ciphertext_b64 = blob.split(":", 2)
        key = _get_key_by_version(version)
        aesgcm = AESGCM(key)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext.decode("utf-8")
    except Exception as exc:
        # Never leak raw crypto internals to the caller/API response.
        raise ValueError("Failed to decrypt field — data may be corrupted or tampered.") from exc
