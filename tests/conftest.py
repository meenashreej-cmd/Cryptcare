import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys


from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.middleware import rate_limit

def pytest_addoption(parser):
    parser.addoption(
        "--mariadb", action="store_true", default=False, help="run tests against local MariaDB"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "mariadb: mark test to run only when mariadb is available")

# Database setup will be initialized dynamically based on pytest config
engine = None
TestingSessionLocal = None

@pytest.fixture(scope="session", autouse=True)
def setup_db(request):
    global engine, TestingSessionLocal
    use_mariadb = request.config.getoption("--mariadb")
    
    if use_mariadb:
        # User's local MariaDB from .env config (root:1234) for tests
        SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@127.0.0.1:3307/cryptcare_test"
        import pymysql
        try:
            conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='1234')
            conn.cursor().execute("CREATE DATABASE IF NOT EXISTS cryptcare_test;")
            conn.close()
        except Exception as e:
            pytest.exit(f"Failed to connect to local MariaDB or create database: {e}")
            
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, 
            pool_pre_ping=True,
            connect_args={"init_command": "SET SESSION innodb_lock_wait_timeout=5"}
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    else:
        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    
    # Patch the app's engine and SessionLocal so that startup events use the test DB
    import app.db.session as db_session
    original_engine = db_session.engine
    original_session_local = db_session.SessionLocal
    
    db_session.engine = engine
    db_session.SessionLocal = TestingSessionLocal
    
    yield
    
    # Restore
    db_session.engine = original_engine
    db_session.SessionLocal = original_session_local
    
    # Drop all after session only for memory db (keep mariadb state or drop it?)
    # Dropping all for MariaDB ensures clean slate for next run.
    Base.metadata.drop_all(bind=engine)
    if engine:
        engine.dispose()

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def db_transactional():
    """A non-transactional fixture for concurrency tests that actually commits to the DB."""
    session = TestingSessionLocal()
    yield session
    
    # Explicit cleanup
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()

@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Reset in-memory rate-limit state before every test so counter leakage
    across tests sharing the same (IP, path) key can't produce spurious 429s."""
    rate_limit.reset()
    yield


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def client_transactional(db_transactional):
    def override_get_db_transactional():
        try:
            yield db_transactional
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db_transactional
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
