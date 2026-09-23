
import os
import sys
import pytest
from pydantic import ValidationError
import importlib

def test_startup_fails_on_short_jwt_secret(monkeypatch):
    # Ensure app modules are not cached so we can test import side effects
    for module in list(sys.modules.keys()):
        if module.startswith("app."):
            del sys.modules[module]
            
    # Set short secret
    monkeypatch.setenv("JWT_SECRET_KEY", "short_secret")
    
    # Importing app.main should raise a ValidationError due to settings validation
    with pytest.raises(ValidationError) as exc:
        import app.main
        
    assert "JWT_SECRET_KEY" in str(exc.value)
    assert "String should have at least 32 characters" in str(exc.value)

