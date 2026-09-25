
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS broadcast_cooldowns"))
    conn.commit()
print("dropped table")

