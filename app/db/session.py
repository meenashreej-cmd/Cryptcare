import os
import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

database_url = settings.DATABASE_URL
connect_args = {}

if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

# Handle TiDB / Cloud MySQL SSL configuration on Render and production
ca_path = os.getenv("TIDB_CA_PATH")
if not ca_path:
    for candidate in ["/etc/secrets/tidb-ca.pem", "certs/isrgrootx1.pem", "certs/tidb-ca.pem"]:
        if os.path.isfile(candidate) and ("tidbcloud.com" in database_url or "ssl" in database_url):
            ca_path = candidate
            break

if ca_path:
    if not os.path.isfile(ca_path):
        raise RuntimeError(f"TiDB CA certificate not found at {ca_path}")
    tls_context = ssl.create_default_context(cafile=ca_path)
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    connect_args = {"ssl": tls_context}
elif "tidbcloud.com" in database_url or "ssl" in database_url:
    tls_context = ssl.create_default_context()
    tls_context.verify_mode = ssl.CERT_REQUIRED
    tls_context.check_hostname = True
    connect_args = {"ssl": tls_context}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
