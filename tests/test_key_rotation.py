"""
Phase 5 hardening — encryption key rotation.

Demonstrates the property the versioned-blob format in app/core/encryption.py
is designed for: data encrypted under an old key version keeps decrypting
correctly after the active key version is rotated forward, with no
re-encryption pass needed on old rows.
"""

import os

import pytest

from app.core.config import settings
from app.core.encryption import decrypt, encrypt, register_key_version


@pytest.fixture
def rotated_key_version():
    """Registers a v2 key and always restores ACTIVE_ENCRYPTION_KEY_VERSION afterward."""
    original_version = settings.ACTIVE_ENCRYPTION_KEY_VERSION
    register_key_version("v2", os.urandom(32))
    yield
    settings.ACTIVE_ENCRYPTION_KEY_VERSION = original_version


def test_old_ciphertext_still_decrypts_after_rotation(rotated_key_version):
    plaintext = "Patient allergy record: penicillin"

    # Encrypted while v1 is active.
    old_blob = encrypt(plaintext)
    assert old_blob.startswith("v1:")

    # Rotate forward.
    settings.ACTIVE_ENCRYPTION_KEY_VERSION = "v2"

    # The old v1 blob must still decrypt correctly — rotation must never
    # require a synchronous re-encryption pass over existing rows.
    assert decrypt(old_blob) == plaintext


def test_new_writes_use_the_newly_active_key_version(rotated_key_version):
    settings.ACTIVE_ENCRYPTION_KEY_VERSION = "v2"

    new_blob = encrypt("New record encrypted post-rotation")
    assert new_blob.startswith("v2:")
    assert decrypt(new_blob) == "New record encrypted post-rotation"


def test_rejects_unregistered_key_version():
    original_version = settings.ACTIVE_ENCRYPTION_KEY_VERSION
    try:
        settings.ACTIVE_ENCRYPTION_KEY_VERSION = "v99-does-not-exist"
        with pytest.raises(ValueError):
            encrypt("this should fail before touching any crypto primitive")
    finally:
        settings.ACTIVE_ENCRYPTION_KEY_VERSION = original_version


def test_register_key_version_rejects_wrong_length_key():
    with pytest.raises(ValueError):
        register_key_version("v_bad", b"too-short")


def test_decrypt_rejects_unsupported_version():
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt("v99:some_nonce:some_ciphertext")


def test_decrypt_rejects_corrupted_format():
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt("v1_invalid_format_no_colons")


def test_decrypt_rejects_corrupted_ciphertext():
    plaintext = "Sensitive data"
    blob = encrypt(plaintext)
    version, nonce_b64, ciphertext_b64 = blob.split(":")
    
    import base64
    from cryptography.exceptions import InvalidTag
    
    # Corrupt ciphertext by flipping a byte
    ciphertext = bytearray(base64.b64decode(ciphertext_b64))
    ciphertext[0] ^= 0xFF
    corrupted_b64 = base64.b64encode(ciphertext).decode("utf-8")
    corrupted_blob = f"{version}:{nonce_b64}:{corrupted_b64}"
    
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt(corrupted_blob)


def test_decrypt_rejects_modified_auth_tag():
    plaintext = "Sensitive data"
    blob = encrypt(plaintext)
    version, nonce_b64, ciphertext_b64 = blob.split(":")
    
    import base64
    from cryptography.exceptions import InvalidTag
    
    # AES-GCM appends a 16-byte auth tag to the end of the ciphertext.
    # Corrupting the last byte corrupts the auth tag.
    ciphertext = bytearray(base64.b64decode(ciphertext_b64))
    ciphertext[-1] ^= 0xFF
    corrupted_b64 = base64.b64encode(ciphertext).decode("utf-8")
    corrupted_blob = f"{version}:{nonce_b64}:{corrupted_b64}"
    
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt(corrupted_blob)
