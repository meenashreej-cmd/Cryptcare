import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_trust_ledger_endpoint_public_access():
    """Verify trust-ledger endpoint is accessible without authentication (UI stream)"""
    response = client.get("/api/v1/audit/trust-ledger?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "chain_tip_hash" in data
    assert "total_entries" in data
    assert "is_tamper_free" in data
    assert data["is_tamper_free"] is True
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) > 0
    
    # Check entry schema structure
    first_entry = data["entries"][0]
    assert "id" in first_entry
    assert "tag" in first_entry
    assert "event" in first_entry
    assert "hash" in first_entry
    assert "timestamp" in first_entry
    assert "formatted_text" in first_entry


def test_trust_ledger_zero_phi():
    """Verify trust-ledger anonymization does not leak passwords, tokens, or raw secrets"""
    response = client.get("/api/v1/audit/trust-ledger?limit=50")
    assert response.status_code == 200
    data = response.json()
    
    forbidden_substrings = ["password", "bearer", "secret", "private_key", "totp_secret", "argon2"]
    for entry in data["entries"]:
        text = (entry["formatted_text"] + " " + entry["event"]).lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in text, f"Found sensitive leak '{forbidden}' in trust ledger entry: {entry}"
