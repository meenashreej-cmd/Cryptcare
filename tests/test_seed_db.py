
import os
import subprocess
import pytest
from app.models.user import User

def test_seed_db_does_not_have_hardcoded_password():
    with open("seed_db.py", "r", encoding="utf-8") as f:
        content = f.read()
    # It used to be PASSWORD = "Password123"
    assert "PASSWORD = \"Password123\"" not in content

def test_admin_user_has_must_change_password_flag(db_transactional, monkeypatch):
    import getpass
    monkeypatch.setattr(getpass, "getpass", lambda prompt: "Password123!")
    
    # This requires running seed_db, but instead we just test the model
    import seed_db as sdb
    
    original_engine = sdb.engine
    original_session_local = sdb.SessionLocal
    
    from app.db.session import engine
    from tests.conftest import TestingSessionLocal
    sdb.engine = engine
    sdb.SessionLocal = TestingSessionLocal
    sdb.PASSWORD = "Password123!"
    
    try:
        sdb.seed_db()
        admin = db_transactional.query(User).filter(User.email == "admin@example.com").first()
        assert admin is not None
        assert admin.must_change_password is True
    finally:
        sdb.engine = original_engine
        sdb.SessionLocal = original_session_local

