"""
migrate_sqlite_to_mysql.py
Transfers all data from local SQLite test.db to a cloud MySQL / TiDB Cloud database.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Import all models to ensure Base.metadata is complete
from app.db.base import Base
from app.models import (  # noqa: F401
    audit,
    consent,
    lab,
    notification,
    nursing,
    user,
    vault,
    insurance,
    blood_bank,
    emergency,
    fraud,
    appointment,
    auth,
)


def migrate(sqlite_path: str, mysql_url: str):
    print(f"Connecting to source SQLite: {sqlite_path}")
    if not os.path.isfile(sqlite_path):
        print(f"ERROR: SQLite file not found at {sqlite_path}")
        return False

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")

    # Prepare connect_args for TiDB / MySQL SSL if needed
    connect_args = {}
    if "tidbcloud.com" in mysql_url or "ssl" in mysql_url:
        import ssl

        ca_candidates = [
            str(BASE_DIR / "certs" / "isrgrootx1.pem"),
            str(BASE_DIR / "certs" / "tidb-ca.pem"),
        ]
        ca_path = None
        for candidate in ca_candidates:
            if os.path.isfile(candidate):
                ca_path = candidate
                break

        if ca_path:
            print(f"Using SSL CA certificate: {ca_path}")
            tls_context = ssl.create_default_context(cafile=ca_path)
        else:
            tls_context = ssl.create_default_context()
        tls_context.verify_mode = ssl.CERT_REQUIRED
        tls_context.check_hostname = True
        connect_args = {"ssl": tls_context}

    if mysql_url.startswith("mysql://"):
        mysql_url = mysql_url.replace("mysql://", "mysql+pymysql://", 1)

    print("Connecting to target MySQL database...")
    target_engine = create_engine(mysql_url, connect_args=connect_args)

    # 1. Create tables on target MySQL
    print("\nCreating schema/tables on target database...")
    Base.metadata.create_all(bind=target_engine)

    # 2. Reflect tables from both engines
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    # 3. Disable foreign keys on target during bulk load
    with target_engine.begin() as target_conn:
        target_conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

        print("\n--- Migrating Tables ---")
        for table_name in Base.metadata.tables:
            if table_name not in sqlite_meta.tables:
                print(f"  [SKIP] '{table_name}' (not present in SQLite)")
                continue

            src_table = sqlite_meta.tables[table_name]
            dst_table = target_meta.tables.get(table_name)
            if dst_table is None:
                print(f"  [WARN] '{table_name}' missing from target schema")
                continue

            with sqlite_engine.connect() as src_conn:
                rows = src_conn.execute(select(src_table)).fetchall()

            if not rows:
                print(f"  [OK] '{table_name}': 0 rows")
                continue

            # Clear destination table first to prevent duplicates
            target_conn.execute(dst_table.delete())

            # Convert Row objects to dicts
            row_dicts = [dict(row._mapping) for row in rows]
            target_conn.execute(dst_table.insert(), row_dicts)
            print(f"  [OK] '{table_name}': migrated {len(row_dicts)} rows")

        target_conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

    print("\n Migration completed successfully!")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_db = sys.argv[1]
    else:
        from app.core.config import settings

        target_db = settings.DATABASE_URL

    sqlite_file = os.path.join(BASE_DIR, "test.db")
    migrate(sqlite_file, target_db)
