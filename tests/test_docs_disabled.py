
import pytest
from fastapi.testclient import TestClient
import sys
import importlib

def test_docs_disabled_in_prod(monkeypatch):
    monkeypatch.setenv("ENV", "prod")
    # Reload config and main
    import app.core.config
    importlib.reload(app.core.config)
    
    import app.main
    importlib.reload(app.main)
    
    client = TestClient(app.main.app)
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404

def test_docs_enabled_in_dev(monkeypatch):
    monkeypatch.setenv("ENV", "dev")
    import app.core.config
    importlib.reload(app.core.config)
    
    import app.main
    importlib.reload(app.main)
    
    client = TestClient(app.main.app)
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200

