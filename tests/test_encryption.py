import pytest
from app.core.encryption import encrypt, decrypt
from app.core.config import settings

def test_encryption_with_aad_success():
    plaintext = "Sensitive Diagnosis Data"
    aad = "cryptcare:v2|prescriptions|rec_123|diagnosis_encrypted|pat_456"
    
    blob = encrypt(plaintext, aad=aad)
    assert blob.startswith("v2:")
    
    decrypted = decrypt(blob, aad=aad)
    assert decrypted == plaintext


def test_encryption_wrong_aad_fails():
    plaintext = "Sensitive Diagnosis Data"
    aad_correct = "cryptcare:v2|prescriptions|rec_123|diagnosis_encrypted|pat_456"
    
    blob = encrypt(plaintext, aad=aad_correct)
    
    # 1. Swapped rows (different record_id)
    aad_swapped = "cryptcare:v2|prescriptions|rec_999|diagnosis_encrypted|pat_456"
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt(blob, aad=aad_swapped)
        
    # 2. Wrong patient_id
    aad_wrong_pat = "cryptcare:v2|prescriptions|rec_123|diagnosis_encrypted|pat_789"
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt(blob, aad=aad_wrong_pat)
        
    # 3. Wrong field name
    aad_wrong_field = "cryptcare:v2|prescriptions|rec_123|notes_encrypted|pat_456"
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        decrypt(blob, aad=aad_wrong_field)


def test_v2_prefix_stripping():
    plaintext = "Sensitive Data"
    aad = "cryptcare:v2|prescriptions|rec_123|diagnosis_encrypted|pat_456"
    
    blob = encrypt(plaintext, aad=aad)
    assert blob.startswith("v2:")
    
    # Simulate an attacker stripping 'v2:' from 'v2:v1:nonce:ciphertext'
    # Resulting string will be 'v1:nonce:ciphertext'
    stripped_blob = blob[3:]
    assert stripped_blob.startswith("v1:")
    
    # Attempt to decrypt stripped blob with legacy logic
    # First, with ENFORCE_AAD_V2 = False (to test cryptographic integrity)
    settings.ENFORCE_AAD_V2 = False
    with pytest.raises(ValueError, match="Failed to decrypt field"):
        # This fails cryptographically because it tries to decrypt without AAD, 
        # but the ciphertext tag includes the AAD mix-in.
        decrypt(stripped_blob, aad=None)
        
    # Now test with ENFORCE_AAD_V2 = True (it should fail at the app layer)
    settings.ENFORCE_AAD_V2 = True
    with pytest.raises(ValueError, match="Legacy decryption without AAD is disabled"):
        decrypt(stripped_blob, aad=None)
        
    # Reset for other tests
    settings.ENFORCE_AAD_V2 = False
