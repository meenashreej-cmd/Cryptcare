
import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, engine
from app.core.encryption import encrypt

def migrate_fraud_alerts():
    db = SessionLocal()
    try:
        is_sqlite = "sqlite" in str(engine.url)
        
        has_description = False
        if is_sqlite:
            result = db.execute(text("PRAGMA table_info(fraud_alerts)")).fetchall()
            if any(col[1] == "description" for col in result):
                has_description = True
        else:
            result = db.execute(text("SHOW COLUMNS FROM fraud_alerts LIKE 'description'")).fetchone()
            if result:
                has_description = True
            
            res_enc = db.execute(text("SHOW COLUMNS FROM fraud_alerts LIKE 'encrypted_context'")).fetchone()
            if not res_enc:
                db.execute(text("ALTER TABLE fraud_alerts ADD COLUMN encrypted_context VARCHAR(1024)"))
                db.commit()

        if not has_description:
            print("No description column found, nothing to migrate.")
            return

        rows = db.execute(text("SELECT alert_id, description FROM fraud_alerts WHERE description IS NOT NULL")).fetchall()
        print(f"Found {len(rows)} alerts to migrate.")

        for row in rows:
            alert_id, description = row
            if description:
                encrypted_val = encrypt(description)
                db.execute(
                    text("UPDATE fraud_alerts SET encrypted_context = :enc WHERE alert_id = :id"),
                    {"enc": encrypted_val, "id": alert_id}
                )
        db.commit()

        if not is_sqlite:
            db.execute(text("ALTER TABLE fraud_alerts DROP COLUMN description"))
            print("Dropped description column from MariaDB.")
        else:
            print("SQLite doesn't support DROP COLUMN cleanly in old versions, ignoring description column drop.")

        print("Migration complete.")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_fraud_alerts()

