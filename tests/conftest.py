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
        SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@127.0.0.1:3306/cryptcare_test"
        import pymysql
        try:
            conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='1234')
            conn.cursor().execute("CREATE DATABASE IF NOT EXISTS cryptcare_test;")
            conn.close()
        except Exception as e:
            pytest.exit(f"Failed to connect to local MariaDB or create database: {e}")
            
        engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
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
    yield
    # Drop all after session only for memory db (keep mariadb state or drop it?)
    # Dropping all for MariaDB ensures clean slate for next run.
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

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
